from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from .database import settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaffInviteEmail:
    to_email: str
    school_name: str
    accept_url: str


def _build_message(email: StaffInviteEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"You're invited to join {email.school_name} on Class Hero Hub"
    from_name = settings.SMTP_FROM_NAME
    from_email = settings.SMTP_FROM_EMAIL
    message["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    message["To"] = email.to_email
    message.set_content(
        "You've been invited to join "
        f"{email.school_name} on Class Hero Hub.\n\n"
        f"Accept your invite: {email.accept_url}\n"
    )
    return message


def send_staff_invite(email: StaffInviteEmail) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning(
            "SMTP not configured; staff invite email for %s to join %s not sent (accept_url=%s)",
            email.to_email,
            email.school_name,
            email.accept_url,
        )
        return

    message = _build_message(email)

    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS and settings.SMTP_PORT != 465:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)

    logger.info(
        "Staff invite email sent to %s to join %s",
        email.to_email,
        email.school_name,
    )
