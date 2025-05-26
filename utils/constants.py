import secrets

DATABASE_PATH = "app_database.db"
JWT_SECRET_KEY = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

NEXT_OTP_INTERVAL = 60
TOP_MAX_DIGIT = 6