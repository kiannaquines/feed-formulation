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


def _get_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value == "replace-with-a-long-random-secret" or len(value) < 32:
        raise ValueError(
            f"{name} must be at least 32 characters; generate it with "
            "'openssl rand -hex 32'"
        )
    return value


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is required")
JWT_SECRET_KEY = _get_secret("JWT_SECRET_KEY")
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
