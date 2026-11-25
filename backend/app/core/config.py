from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    STORAGE_BACKEND: str = "local"

    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = "civicpulse-uploads-youruniqueid"
    AWS_PRESIGNED_URL_EXPIRE: int = 3600
    APP_NAME: str = "Smart Civic Issue Management System"
    APP_ENV: str = "development"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = True

    DATABASE_URL: str = "mysql+pymysql://civic_user:civic_pass@localhost:3306/civic_issues_db"

    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_EXPIRE_MINUTES: int = 60 * 24 * 7

    UPLOAD_DIRECTORY: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/quicktime"]

    AI_MODEL_PATH: str = "./ai/models/yolo_civic.pt"
    AI_PROVIDER: str = "mock"
    AI_MIN_CONFIDENCE: float = 0.35

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    DUPLICATE_RADIUS_METERS: float = 75.0
    DUPLICATE_TIME_WINDOW_HOURS: int = 168

    RATE_LIMIT_PER_MINUTE: int = 60

    # --- OTP (email + mobile verification) ---
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60

    # "console" logs the OTP to the server console (development only, no
    # credentials needed). "smtp" / "twilio" send for real.
    EMAIL_PROVIDER: str = "console"
    SMS_PROVIDER: str = "console"

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    


    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
