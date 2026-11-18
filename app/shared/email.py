"""Outgoing email, behind one small interface — same idea as `storage.py`.

Services depend on `EmailSender`, never on SMTP directly, so tests can swap
in an in-memory outbox and production can point at any SMTP provider
without a code change.
"""

import asyncio
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache

from app.core.config import settings


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class EmailSender(ABC):

    @abstractmethod
    async def send(self, email: Email) -> None:
        """Deliver one plain-text email. Raises on failure."""


class SmtpEmailSender(EmailSender):

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        use_tls: bool,
        sender: str,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.sender = sender

    async def send(self, email: Email) -> None:
        # smtplib is blocking — run it off the event loop, like boto3 in
        # storage.py.
        await asyncio.to_thread(self._send_sync, email)

    def _send_sync(self, email: Email) -> None:

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)

        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if self.use_tls:
                smtp.starttls()

            if self.username:
                smtp.login(self.username, self.password)

            smtp.send_message(message)


@lru_cache
def get_email_sender() -> EmailSender:
    return SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        sender=settings.email_from,
    )
