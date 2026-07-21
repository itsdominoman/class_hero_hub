from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .database import settings
from .messaging_notifications import (
    message_notification_direction,
    notification_recipient_allowed,
)
from .family_notifications import revalidate_family_notification
from .models_school import (
    Conversation,
    ConversationParticipant,
    DevicePushRegistration,
    FhhLink,
    Membership,
    Message,
    NotificationDelivery,
    NotificationOutbox,
    User,
)


logger = logging.getLogger(__name__)
UTC = timezone.utc


class ProviderError(Exception):
    def __init__(self, code: str, *, terminal: bool = False, invalid_token: bool = False):
        super().__init__(code)
        self.code = code
        self.terminal = terminal
        self.invalid_token = invalid_token


def school_message_collapse_key(conversation_id: str, message_direction: str) -> str:
    if message_direction not in {"family_to_staff", "staff_to_family", "staff_to_staff"}:
        raise ProviderError("invalid_notification_direction", terminal=True)
    return f"school-chat-{message_direction.replace('_', '-')}-{conversation_id}"


class PushProvider(Protocol):
    def send(
        self,
        *,
        token: str,
        locale: str,
        event_id: str,
        conversation_id: str,
        urgent: bool,
        message_direction: str,
    ) -> str: ...


class BridgeProvider(Protocol):
    def send(self, **kwargs) -> str: ...


class FirebasePushProvider:
    def __init__(self) -> None:
        self._app = None
        self._attempted = False

    def _firebase_app(self):
        if self._app is not None:
            return self._app
        if self._attempted:
            raise ProviderError("firebase_unavailable", terminal=True)
        self._attempted = True
        raw = settings.FIREBASE_SERVICE_ACCOUNT_JSON.strip()
        if not raw:
            raise ProviderError("firebase_credentials_missing", terminal=True)
        try:
            import firebase_admin
            from firebase_admin import credentials

            try:
                self._app = firebase_admin.get_app()
            except ValueError:
                self._app = firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
            return self._app
        except Exception as exc:
            logger.exception("Failed to initialize Firebase Admin for CHH notifications")
            raise ProviderError("firebase_initialization_failed", terminal=True) from exc

    def send(
        self,
        *,
        token: str,
        locale: str,
        event_id: str,
        conversation_id: str,
        urgent: bool,
        message_direction: str,
    ) -> str:
        try:
            from firebase_admin import messaging

            title = "رسالة مدرسية جديدة" if locale == "ar" else "New school message"
            body = "لديك رسالة مدرسية جديدة." if locale == "ar" else "You have a new school message."
            collapse_key = school_message_collapse_key(conversation_id, message_direction)
            return messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={
                        "route_type": "school_chat",
                        "notification_event_id": event_id,
                    },
                    android=messaging.AndroidConfig(
                        collapse_key=collapse_key,
                        priority="high" if urgent else "normal",
                        ttl=timedelta(days=1),
                        restricted_package_name=settings.CHH_ANDROID_PACKAGE,
                        notification=messaging.AndroidNotification(
                            channel_id="urgent_school_messages" if urgent else "school_messages",
                            tag=collapse_key,
                            visibility="private",
                            default_sound=True,
                            default_vibrate_timings=True,
                        ),
                    ),
                    token=token,
                ),
                app=self._firebase_app(),
            )
        except ProviderError:
            raise
        except Exception as exc:
            code = str(getattr(exc, "code", "") or exc.__class__.__name__).lower().replace(" ", "_")[:80]
            invalid = code in {
                "unregistered",
                "invalid-argument",
                "invalid_argument",
                "registration-token-not-registered",
                "invalid-registration-token",
            } or exc.__class__.__name__ in {"UnregisteredError", "InvalidArgumentError"}
            terminal = invalid or exc.__class__.__name__ in {
                "SenderIdMismatchError",
                "ThirdPartyAuthError",
            }
            raise ProviderError(code or "firebase_send_failed", terminal=terminal, invalid_token=invalid) from exc


class SignedFhhBridgeProvider:
    def send(
        self,
        *,
        event_id: str,
        remote_link_id: int,
        conversation_id: str | None = None,
        urgent: bool,
        occurred_at: datetime,
        message_direction: str | None = None,
        route_type: str = "school_chat",
        category: str = "chat",
        source_ref: str | None = None,
        action: str | None = None,
        source_version: int = 1,
        template_variant: str | None = None,
    ) -> str:
        if not (
            settings.FHH_NOTIFICATION_BRIDGE_URL.strip()
            and settings.FHH_NOTIFICATION_SERVICE_TOKEN.strip()
            and settings.FHH_NOTIFICATION_HMAC_SECRET.strip()
        ):
            raise ProviderError("fhh_bridge_configuration_missing", terminal=True)
        body = {
            "event_id": event_id,
            "route_type": route_type,
            "remote_link_id": remote_link_id,
            "urgent": urgent,
            "occurred_at": occurred_at.astimezone(UTC).isoformat(),
        }
        if route_type == "school_chat":
            body["conversation_id"] = conversation_id
            body["message_direction"] = message_direction
        else:
            body["category"] = category
            body["source_version"] = source_version
            body["source_ref"] = source_ref
            body["action"] = action
            if template_variant:
                body["template_variant"] = template_variant
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        timestamp = str(int(datetime.now(UTC).timestamp()))
        nonce = event_id
        digest = hashlib.sha256(raw).hexdigest()
        signature = hmac.new(
            settings.FHH_NOTIFICATION_HMAC_SECRET.encode("utf-8"),
            f"{timestamp}\n{nonce}\n{digest}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        try:
            response = httpx.post(
                settings.FHH_NOTIFICATION_BRIDGE_URL,
                content=raw,
                headers={
                    "Authorization": f"Bearer {settings.FHH_NOTIFICATION_SERVICE_TOKEN}",
                    "Content-Type": "application/json",
                    "X-CHH-Notification-Timestamp": timestamp,
                    "X-CHH-Notification-Nonce": nonce,
                    "X-CHH-Notification-Signature": signature,
                },
                timeout=httpx.Timeout(settings.FHH_NOTIFICATION_TIMEOUT_SECONDS),
            )
        except (httpx.HTTPError, TimeoutError) as exc:
            raise ProviderError("fhh_bridge_unavailable") from exc
        if response.status_code in {408, 425, 429} or response.status_code >= 500:
            raise ProviderError(f"fhh_bridge_http_{response.status_code}")
        if response.status_code >= 400:
            raise ProviderError(f"fhh_bridge_http_{response.status_code}", terminal=True)
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("fhh_bridge_invalid_response") from exc
        if payload.get("status") not in {"accepted", "duplicate"}:
            raise ProviderError("fhh_bridge_rejected")
        return str(payload.get("status"))


@dataclass(frozen=True)
class DispatchContext:
    row: NotificationOutbox
    message: Message
    conversation: Conversation
    sender: ConversationParticipant


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _retry_at(attempt: int, now: datetime) -> datetime:
    delay = min(
        settings.MESSAGING_NOTIFICATION_RETRY_MAX_SECONDS,
        settings.MESSAGING_NOTIFICATION_RETRY_BASE_SECONDS * (2 ** max(attempt - 1, 0)),
    )
    return now + timedelta(seconds=delay)


def claim_dispatch_rows(
    db: Session,
    *,
    worker_id: str,
    limit: int,
    now: datetime | None = None,
) -> list[int]:
    now = _aware(now or datetime.now(UTC)).astimezone(UTC)
    rows = (
        db.query(NotificationOutbox)
        .filter(
            or_(
                and_(
                    NotificationOutbox.state.in_(("pending", "failed")),
                    NotificationOutbox.next_attempt_at <= now,
                    NotificationOutbox.eligible_at <= now,
                    or_(
                        NotificationOutbox.last_error_code.is_(None),
                        NotificationOutbox.last_error_code != "scheduler_error",
                    ),
                ),
                and_(
                    NotificationOutbox.state == "leased",
                    NotificationOutbox.lease_owner.like("notification-dispatch-%"),
                    NotificationOutbox.lease_expires_at < now,
                ),
            )
        )
        .order_by(NotificationOutbox.next_attempt_at, NotificationOutbox.id)
        .with_for_update(of=NotificationOutbox, skip_locked=True)
        .limit(limit)
        .all()
    )
    expires = now + timedelta(seconds=settings.MESSAGING_NOTIFICATION_SCHEDULER_LEASE_SECONDS)
    for row in rows:
        row.state = "leased"
        row.lease_owner = worker_id
        row.lease_expires_at = expires
    ids = [row.id for row in rows]
    db.commit()
    return ids


def _cancel_outbox(row: NotificationOutbox, code: str, now: datetime) -> None:
    row.state = "cancelled"
    row.last_error_code = code
    row.completed_at = now
    row.lease_owner = None
    row.lease_expires_at = None


def _contexts(db: Session, rows: list[NotificationOutbox]) -> dict[int, DispatchContext]:
    messages = {
        row.id: row
        for row in db.query(Message).filter(Message.id.in_({row.message_id for row in rows})).all()
    }
    conversations = {
        row.id: row
        for row in db.query(Conversation)
        .filter(Conversation.id.in_({message.conversation_id for message in messages.values()}))
        .all()
    }
    senders = {
        row.id: row
        for row in db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.id.in_(
                {message.sender_participant_id for message in messages.values()}
            )
        )
        .all()
    }
    return {
        row.id: DispatchContext(
            row,
            messages[row.message_id],
            conversations[messages[row.message_id].conversation_id],
            senders[messages[row.message_id].sender_participant_id],
        )
        for row in rows
        if (
            row.message_id in messages
            and messages[row.message_id].conversation_id in conversations
            and messages[row.message_id].sender_participant_id in senders
        )
    }


def _valid_chh_recipient(db: Session, context: DispatchContext) -> bool:
    row = context.row
    participant = (
        db.query(ConversationParticipant)
        .filter(
            ConversationParticipant.id == row.recipient_participant_id,
            ConversationParticipant.conversation_id == context.conversation.id,
            ConversationParticipant.user_id == row.recipient_user_id,
            ConversationParticipant.left_at.is_(None),
        )
        .first()
    )
    if (
        participant is None
        or participant.membership_id is None
        or not notification_recipient_allowed(
            context.conversation,
            context.sender,
            participant,
        )
    ):
        return False
    return (
        db.query(Membership.id)
        .join(User, User.id == Membership.user_id)
        .filter(
            Membership.id == participant.membership_id,
            Membership.user_id == row.recipient_user_id,
            Membership.school_id == row.school_id,
            Membership.role.in_(("teacher", "school_admin")),
            Membership.status == "active",
            Membership.revoked_at.is_(None),
            User.status == "active",
        )
        .first()
        is not None
    )


def _ensure_deliveries(db: Session, context: DispatchContext, now: datetime) -> list[NotificationDelivery]:
    row = context.row
    registrations = (
        db.query(DevicePushRegistration)
        .filter(
            DevicePushRegistration.user_id == row.recipient_user_id,
            DevicePushRegistration.state == "active",
            DevicePushRegistration.platform == "android",
            DevicePushRegistration.app_package == settings.CHH_ANDROID_PACKAGE,
        )
        .order_by(DevicePushRegistration.id)
        .all()
    )
    existing = {
        delivery.device_registration_id: delivery
        for delivery in db.query(NotificationDelivery)
        .filter(NotificationDelivery.outbox_id == row.id)
        .all()
    }
    for registration in registrations:
        if registration.id not in existing:
            delivery = NotificationDelivery(
                outbox_id=row.id,
                device_registration_id=registration.id,
                next_attempt_at=now,
            )
            db.add(delivery)
            existing[registration.id] = delivery
    db.flush()
    return list(existing.values())


def _mark_delivery_failure(
    delivery: NotificationDelivery,
    error: ProviderError,
    *,
    now: datetime,
) -> None:
    delivery.attempt_count += 1
    delivery.last_error_code = error.code
    delivery.lease_owner = None
    delivery.lease_expires_at = None
    if error.invalid_token:
        delivery.state = "cancelled"
        delivery.completed_at = now
    elif error.terminal or delivery.attempt_count >= settings.MESSAGING_NOTIFICATION_MAX_ATTEMPTS:
        delivery.state = "dead"
        delivery.completed_at = now
    else:
        delivery.state = "failed"
        delivery.next_attempt_at = _retry_at(delivery.attempt_count, now)


def _finalize_outbox(db: Session, row: NotificationOutbox, now: datetime) -> None:
    deliveries = (
        db.query(NotificationDelivery)
        .filter(NotificationDelivery.outbox_id == row.id)
        .order_by(NotificationDelivery.id)
        .all()
    )
    states = {delivery.state for delivery in deliveries}
    row.lease_owner = None
    row.lease_expires_at = None
    if "failed" in states or "pending" in states or "leased" in states:
        row.attempt_count += 1
        if row.attempt_count >= settings.MESSAGING_NOTIFICATION_MAX_ATTEMPTS:
            row.state = "dead"
            row.completed_at = now
            row.last_error_code = "provider_attempts_exhausted"
        else:
            row.state = "failed"
            retry_times = [delivery.next_attempt_at for delivery in deliveries if delivery.state == "failed"]
            row.next_attempt_at = min(retry_times) if retry_times else _retry_at(row.attempt_count, now)
            row.last_error_code = next(
                (delivery.last_error_code for delivery in deliveries if delivery.state == "failed"),
                "provider_retry",
            )
        return
    if "provider_accepted" in states:
        row.state = "provider_accepted"
        row.provider_accepted_at = now
        row.completed_at = now
        row.last_error_code = None
        row.provider_message_ref = next(
            (delivery.provider_message_ref for delivery in deliveries if delivery.provider_message_ref),
            None,
        )
        return
    row.state = "dead" if "dead" in states else "cancelled"
    row.completed_at = now
    row.last_error_code = next(
        (delivery.last_error_code for delivery in deliveries if delivery.last_error_code),
        "no_active_devices",
    )


def dispatch_claimed_rows(
    db: Session,
    *,
    row_ids: list[int],
    worker_id: str,
    push_provider: PushProvider,
    bridge_provider: BridgeProvider,
    now: datetime | None = None,
) -> int:
    now = _aware(now or datetime.now(UTC)).astimezone(UTC)
    rows = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.id.in_(row_ids),
            NotificationOutbox.state == "leased",
            NotificationOutbox.lease_owner == worker_id,
        )
        .order_by(NotificationOutbox.id)
        .all()
    )
    chat_rows = [row for row in rows if row.event_category == "chat"]
    contexts = _contexts(db, chat_rows)
    push_groups: dict[tuple[int, int, str], list[tuple[DispatchContext, NotificationDelivery, DevicePushRegistration]]] = {}
    bridge_contexts: list[DispatchContext] = []
    family_bridge_rows: list[NotificationOutbox] = []
    for row in rows:
        if row.event_category != "chat":
            if not revalidate_family_notification(db, row):
                _cancel_outbox(row, "recipient_ineligible", now)
            else:
                family_bridge_rows.append(row)
            continue
        context = contexts.get(row.id)
        if (
            context is None
            or context.message.state != "active"
            or context.conversation.status != "active"
        ):
            _cancel_outbox(row, "notification_target_missing", now)
            continue
        message_direction = message_notification_direction(
            context.conversation,
            context.sender,
        )
        if message_direction is None:
            _cancel_outbox(row, "invalid_notification_direction", now)
            continue
        if row.recipient_kind == "chh_user":
            if not _valid_chh_recipient(db, context):
                _cancel_outbox(row, "recipient_ineligible", now)
                continue
            deliveries = _ensure_deliveries(db, context, now)
            if not deliveries:
                _cancel_outbox(row, "no_active_devices", now)
                continue
            registrations = {
                registration.id: registration
                for registration in db.query(DevicePushRegistration)
                .filter(DevicePushRegistration.id.in_([delivery.device_registration_id for delivery in deliveries]))
                .all()
            }
            for delivery in deliveries:
                registration = registrations.get(delivery.device_registration_id)
                if registration is None or registration.state != "active":
                    if delivery.state not in {"provider_accepted", "dead", "cancelled"}:
                        delivery.state = "cancelled"
                        delivery.last_error_code = "device_inactive"
                        delivery.completed_at = now
                    continue
                if delivery.state in {"pending", "failed"} and delivery.next_attempt_at <= now:
                    push_groups.setdefault(
                        (registration.id, context.conversation.id, message_direction), []
                    ).append((context, delivery, registration))
        else:
            if message_direction != "staff_to_family":
                _cancel_outbox(row, "invalid_notification_direction", now)
                continue
            link = (
                db.query(FhhLink)
                .filter(
                    FhhLink.id == row.recipient_fhh_link_id,
                    FhhLink.school_id == row.school_id,
                    FhhLink.status == "active",
                    FhhLink.revoked_at.is_(None),
                )
                .first()
            )
            if link is None:
                _cancel_outbox(row, "recipient_ineligible", now)
            else:
                bridge_contexts.append(context)
    db.flush()

    for grouped in push_groups.values():
        grouped.sort(key=lambda item: (item[0].message.sequence, item[0].row.id))
        latest_context, _latest_delivery, registration = grouped[-1]
        try:
            provider_ref = push_provider.send(
                token=registration.fcm_token,
                locale=registration.locale,
                event_id=str(latest_context.row.event_id),
                conversation_id=str(latest_context.conversation.public_id),
                urgent=bool(latest_context.message.urgent),
                message_direction=message_notification_direction(
                    latest_context.conversation,
                    latest_context.sender,
                ) or "invalid",
            )
            for context, delivery, _registration in grouped:
                delivery.state = "provider_accepted"
                delivery.provider_message_ref = provider_ref
                delivery.dispatched_at = now
                delivery.provider_accepted_at = now
                delivery.completed_at = now
                delivery.last_error_code = None
                context.row.dispatched_at = now
        except ProviderError as error:
            if error.invalid_token:
                registration.state = "invalid"
                registration.disabled_reason = error.code
                registration.revoked_at = now
            for _context, delivery, _registration in grouped:
                _mark_delivery_failure(delivery, error, now=now)

    for context in bridge_contexts:
        row = context.row
        link = db.query(FhhLink).filter(FhhLink.id == row.recipient_fhh_link_id).one()
        try:
            provider_ref = bridge_provider.send(
                event_id=str(row.event_id),
                remote_link_id=link.id,
                conversation_id=str(context.conversation.public_id),
                urgent=bool(context.message.urgent),
                occurred_at=_aware(context.message.created_at),
                message_direction="staff_to_family",
            )
            row.state = "provider_accepted"
            row.provider_message_ref = provider_ref[:200]
            row.dispatched_at = now
            row.provider_accepted_at = now
            row.completed_at = now
            row.last_error_code = None
            row.lease_owner = None
            row.lease_expires_at = None
        except ProviderError as error:
            row.attempt_count += 1
            row.last_error_code = error.code
            row.lease_owner = None
            row.lease_expires_at = None
            if error.terminal or row.attempt_count >= settings.MESSAGING_NOTIFICATION_MAX_ATTEMPTS:
                row.state = "dead"
                row.completed_at = now
            else:
                row.state = "failed"
                row.next_attempt_at = _retry_at(row.attempt_count, now)

    for row in family_bridge_rows:
        link = db.query(FhhLink).filter(FhhLink.id == row.recipient_fhh_link_id).one()
        try:
            provider_ref = bridge_provider.send(
                event_id=str(row.event_id),
                remote_link_id=link.id,
                route_type=row.route_type,
                category=row.event_category,
                source_ref=row.route_ref,
                action=row.source_action,
                source_version=row.source_version,
                template_variant=(row.template_args or {}).get("variant"),
                urgent=bool(row.urgent),
                occurred_at=_aware(row.created_at),
            )
            row.state = "provider_accepted"
            row.provider_message_ref = provider_ref[:200]
            row.dispatched_at = now
            row.provider_accepted_at = now
            row.completed_at = now
            row.last_error_code = None
            row.lease_owner = None
            row.lease_expires_at = None
        except ProviderError as error:
            row.attempt_count += 1
            row.last_error_code = error.code
            row.lease_owner = None
            row.lease_expires_at = None
            if error.terminal or row.attempt_count >= settings.MESSAGING_NOTIFICATION_MAX_ATTEMPTS:
                row.state = "dead"
                row.completed_at = now
            else:
                row.state = "failed"
                row.next_attempt_at = _retry_at(row.attempt_count, now)

    for row in rows:
        if row.recipient_kind == "chh_user" and row.state == "leased":
            _finalize_outbox(db, row, now)
    db.commit()
    return len(rows)


def process_notification_dispatch_batch(
    session_factory: Callable[[], Session],
    *,
    worker_id: str,
    limit: int | None = None,
    now: datetime | None = None,
    push_provider: PushProvider | None = None,
    bridge_provider: BridgeProvider | None = None,
) -> int:
    claim_db = session_factory()
    try:
        row_ids = claim_dispatch_rows(
            claim_db,
            worker_id=worker_id,
            limit=limit or settings.MESSAGING_NOTIFICATION_SCHEDULER_BATCH_SIZE,
            now=now,
        )
    finally:
        claim_db.close()
    if not row_ids:
        return 0
    work_db = session_factory()
    try:
        return dispatch_claimed_rows(
            work_db,
            row_ids=row_ids,
            worker_id=worker_id,
            push_provider=push_provider or FirebasePushProvider(),
            bridge_provider=bridge_provider or SignedFhhBridgeProvider(),
            now=now,
        )
    except Exception:
        work_db.rollback()
        logger.exception("Messaging notification dispatch batch failed")
        raise
    finally:
        work_db.close()
