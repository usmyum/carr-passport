"""The text of every email this module sends. Plain text on purpose — no
template engine until there's a design worth one."""

from urllib.parse import urlencode

from app.core.config import settings
from app.shared.email import Email


def _link(path: str, token: str) -> str:
    return f"{settings.frontend_url}{path}?{urlencode({'token': token})}"


def verification_email(to: str, token: str) -> Email:
    return Email(
        to=to,
        subject="Confirm your email for Car Passport",
        body=(
            "Welcome to Car Passport!\n\n"
            "Confirm your email address by opening this link:\n\n"
            f"{_link('/verify-email', token)}\n\n"
            f"The link expires in {settings.email_verification_expire_hours} hours. "
            "If you didn't sign up, you can ignore this email."
        ),
    )


def password_reset_email(to: str, token: str) -> Email:
    return Email(
        to=to,
        subject="Reset your Car Passport password",
        body=(
            "Someone asked to reset the password for this account.\n\n"
            "To choose a new password, open this link:\n\n"
            f"{_link('/reset-password', token)}\n\n"
            f"The link expires in {settings.password_reset_expire_minutes} minutes "
            "and works once. If this wasn't you, ignore this email — your "
            "password stays the same."
        ),
    )
