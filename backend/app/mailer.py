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


@dataclass(frozen=True)
class MagicLoginEmail:
    to_email: str
    login_url: str


@dataclass(frozen=True)
class PilotEnquiryEmail:
    name: str
    school: str
    role: str
    region: str
    reply_to: str
    message: str


@dataclass(frozen=True)
class FhhGuardianInviteEmail:
    to_email: str
    school_name: str
    invite_url: str


def _address_from_settings() -> str:
    from_name = settings.SMTP_FROM_NAME
    from_email = settings.SMTP_FROM_EMAIL
    return f"{from_name} <{from_email}>" if from_name else from_email


def _build_staff_invite_message(email: StaffInviteEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"You're invited to join {email.school_name} on Class Hero Hub"
    message["From"] = _address_from_settings()
    message["To"] = email.to_email
    message.set_content(
        "You've been invited to join "
        f"{email.school_name} on Class Hero Hub.\n\n"
        f"Accept your invite: {email.accept_url}\n"
    )
    return message


def _build_magic_login_message(email: MagicLoginEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = "Your Class Hero Hub sign-in link"
    message["From"] = _address_from_settings()
    message["To"] = email.to_email
    message.set_content(
        "Use this one-time link to sign in to Class Hero Hub.\n\n"
        f"Sign in: {email.login_url}\n\n"
        "This link expires soon and can only be used once.\n"
    )
    return message


def _build_pilot_enquiry_message(enquiry: PilotEnquiryEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"Class Hero Hub pilot enquiry — {enquiry.school}"
    message["From"] = _address_from_settings()
    message["To"] = "support@classherohub.com"
    message["Reply-To"] = enquiry.reply_to
    message.set_content(
        "A new Class Hero Hub pilot enquiry was submitted.\n\n"
        f"Name: {enquiry.name}\n"
        f"School: {enquiry.school}\n"
        f"Role: {enquiry.role}\n"
        f"Country or region: {enquiry.region}\n"
        f"Email: {enquiry.reply_to}\n\n"
        "What they would like to improve:\n"
        f"{enquiry.message}\n"
    )
    return message


def _build_fhh_guardian_invite_message(email: FhhGuardianInviteEmail) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = f"{email.school_name} has invited you to Family Hero Hub"
    message["From"] = _address_from_settings()
    message["To"] = email.to_email
    message.set_content(
        f"{email.school_name} uses Class Hero Hub to share school updates with families.\n\n"
        "Open your invitation and sign in to Family Hero Hub with this email address:\n"
        f"{email.invite_url}\n\n"
        "For your privacy, this email does not include a child's name. If you were not "
        "expecting this invitation, please contact the school.\n"
    )
    return message


def _send_message(message: EmailMessage) -> None:
    smtp_cls = smtplib.SMTP_SSL if settings.SMTP_PORT == 465 else smtplib.SMTP
    with smtp_cls(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        if settings.SMTP_USE_TLS and settings.SMTP_PORT != 465:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def send_staff_invite(email: StaffInviteEmail) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured for staff invitations")

    _send_message(_build_staff_invite_message(email))

    logger.info(
        "Staff invite email sent to %s to join %s",
        email.to_email,
        email.school_name,
    )


def send_magic_login(email: MagicLoginEmail) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured for sign-in links")

    _send_message(_build_magic_login_message(email))
    logger.info("Magic login email sent to %s", email.to_email)


def send_pilot_enquiry(enquiry: PilotEnquiryEmail) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured for pilot enquiries")

    _send_message(_build_pilot_enquiry_message(enquiry))
    logger.info("Pilot enquiry email accepted by the configured mail server")


def send_fhh_guardian_invite(email: FhhGuardianInviteEmail) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP is not configured for family invitations")

    _send_message(_build_fhh_guardian_invite_message(email))
    logger.info("Family Hero Hub invitation email accepted by the configured mail server")
