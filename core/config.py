import hashlib
import os

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _get_positive_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc

    if parsed_value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed_value


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app_database.db")
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    hashlib.sha256(b"feed_formulation_secret_key_1234567890").hexdigest(),
)
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = _get_positive_int("JWT_EXPIRATION_HOURS", 24)
NEXT_OTP_INTERVAL = _get_positive_int("NEXT_OTP_INTERVAL", 60)
TOP_MAX_DIGIT = _get_positive_int("TOP_MAX_DIGIT", 6)
OTP_IS_ENABLED = _get_bool("OTP_IS_ENABLED", False)
OTP_SESSION_EXPIRATION_MINUTES = _get_positive_int(
    "OTP_SESSION_EXPIRATION_MINUTES", 10
)
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
CORS_ALLOW_ORIGINS = _get_list("CORS_ALLOW_ORIGINS", ["*"])
CORS_ALLOW_CREDENTIALS = _get_bool("CORS_ALLOW_CREDENTIALS", True)
CORS_ALLOW_METHODS = _get_list("CORS_ALLOW_METHODS", ["*"])
CORS_ALLOW_HEADERS = _get_list("CORS_ALLOW_HEADERS", ["*"])
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = _get_positive_int("SERVER_PORT", 8000)
