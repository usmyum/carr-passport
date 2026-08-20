"""File storage abstraction.

Receipts, documents and vehicle photos never go into Postgres — they go
through here. Locally that means MinIO; in production the same S3 API points
at real object storage, so nothing above this layer changes.

boto3 is synchronous, so every call is pushed to a worker thread to keep the
event loop free.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from pathlib import PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.shared.exceptions import StorageException


def build_object_key(
        folder: str,
        filename: str,
) -> str:
    """Namespace uploads and defuse the original filename.

    User-supplied names are never trusted as keys: the extension is kept for
    content sniffing, everything else becomes a UUID.
    """

    suffix = PurePosixPath(filename or "").suffix.lower()

    if len(suffix) > 10:
        suffix = ""

    return f"{folder.strip('/')}/{uuid.uuid4().hex}{suffix}"


class Storage(ABC):

    @abstractmethod
    async def upload(
            self,
            key: str,
            content: bytes,
            content_type: str,
    ) -> str:
        """Store bytes and return the object key."""

    @abstractmethod
    async def delete(
            self,
            key: str,
    ) -> None: ...

    @abstractmethod
    async def get_url(
            self,
            key: str,
            expires_in: int = 3600,
    ) -> str:
        """A temporary URL a browser or app can fetch the object with."""


class S3Storage(Storage):

    def __init__(
            self,
            bucket: str,
            endpoint_url: str | None,
            access_key: str,
            secret_key: str,
            region: str,
    ):
        self.bucket = bucket

        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3},
            ),
        )

    async def upload(
            self,
            key: str,
            content: bytes,
            content_type: str,
    ) -> str:

        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageException(
                "Could not upload the file"
            ) from exc

        return key

    async def delete(
            self,
            key: str,
    ) -> None:

        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket,
                Key=key,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageException(
                "Could not delete the file"
            ) from exc

    async def get_url(
            self,
            key: str,
            expires_in: int = 3600,
    ) -> str:

        try:
            return await asyncio.to_thread(
                self.client.generate_presigned_url,
                "get_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                },
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageException(
                "Could not build a download link"
            ) from exc

    def ensure_bucket(self) -> None:
        """Create the bucket if it is missing. Local-dev convenience."""

        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)


_storage: Storage | None = None


def get_storage() -> Storage:
    """FastAPI dependency. One client is reused for the process lifetime."""

    global _storage

    if _storage is None:
        _storage = S3Storage(
            bucket=settings.s3_bucket,
            endpoint_url=settings.s3_endpoint_url,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            region=settings.s3_region,
        )

    return _storage
