from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Car Passport"
    app_env: str = "local"

    database_url: str

    # Separate database so running the suite never touches dev data.
    test_database_url: str | None = None

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Object storage (MinIO locally, S3-compatible in production)
    s3_endpoint_url: str | None = None

    # Only needed locally, where the API reaches MinIO over the Docker
    # network (`minio:9000`) but a presigned URL has to be reachable from a
    # browser on the host (`localhost:9000`) instead. In production there's
    # one real public S3 endpoint, so this is left unset and falls back to
    # `s3_endpoint_url`.
    s3_public_endpoint_url: str | None = None

    s3_bucket: str = "car-passport"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"

    # Uploads
    max_upload_size_mb: int = 10

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
