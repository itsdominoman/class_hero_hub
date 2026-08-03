from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from ..mailer import PilotEnquiryEmail, send_pilot_enquiry
from ..security import BoundedInMemoryRateLimiter, get_client_ip_from_scope


logger = logging.getLogger(__name__)
router = APIRouter()

PILOT_ENQUIRY_RATE_LIMITER = BoundedInMemoryRateLimiter(600, 5)


class PilotEnquiryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    school: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=120)
    region: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    message: str = Field(min_length=10, max_length=2000)

    @field_validator("name", "school", "role", "region", "email", mode="before")
    @classmethod
    def clean_single_line_fields(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if "\r" in cleaned or "\n" in cleaned or "\x00" in cleaned:
            raise ValueError("must be a single line")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("must be a valid email address")
        return value

    @field_validator("message", mode="before")
    @classmethod
    def clean_message(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        cleaned = value.strip()
        if "\x00" in cleaned:
            raise ValueError("contains an invalid character")
        return cleaned


@router.post("/pilot-enquiries")
def submit_pilot_enquiry(payload: PilotEnquiryRequest, request: Request):
    client_ip = get_client_ip_from_scope(request.scope) or "unknown"
    if not PILOT_ENQUIRY_RATE_LIMITER.allow(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many pilot enquiries. Please try again later.",
        )

    try:
        send_pilot_enquiry(
            PilotEnquiryEmail(
                name=payload.name,
                school=payload.school,
                role=payload.role,
                region=payload.region,
                reply_to=payload.email,
                message=payload.message,
            )
        )
    except Exception:
        logger.exception("Pilot enquiry email delivery failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pilot enquiry email delivery is temporarily unavailable.",
        )

    return {"status": "sent"}
