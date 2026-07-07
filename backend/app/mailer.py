from __future__ import annotations

import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StaffInviteEmail:
    to_email: str
    school_name: str
    accept_url: str


def send_staff_invite(email: StaffInviteEmail) -> None:
    logger.info(
        "Staff invite email queued for %s to join %s at %s",
        email.to_email,
        email.school_name,
        email.accept_url,
    )
