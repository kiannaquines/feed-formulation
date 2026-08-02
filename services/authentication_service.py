import secrets
from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.authentication import (
    create_jwt_token,
    decode_jwt_token,
    generate_otp_secret,
    hash_password,
    verify_password,
)
from core.config import (
    JWT_EXPIRATION_HOURS,
    OTP_IS_ENABLED,
    OTP_SESSION_EXPIRATION_MINUTES,
)
from core.exceptions import AuthenticationError, PersistenceError, ValidationError
from core.otp import generate_otp, verify_otp
from models.models import OTPSession, User
from repositories import OTPSessionRepository, UserRepository
from schema.schema import OTPVerification, UserLogin, UserRegister


class AuthenticationService:
    def __init__(
        self,
        db: Session,
        users: UserRepository,
        otp_sessions: OTPSessionRepository,
    ):
        self.db = db
        self.users = users
        self.otp_sessions = otp_sessions

    def register(self, data: UserRegister) -> dict:
        if self._read(
            lambda: self.users.get_by_username_or_email(data.username, data.email)
        ):
            raise ValidationError("Username or email already registered")

        user = User(
            username=data.username,
            email=data.email,
            password_hash=hash_password(data.password),
            otp_secret=generate_otp_secret(),
        )
        self._commit(lambda: self.users.add(user))
        return {
            "message": "User registered successfully",
            "note": "Save your OTP secret securely. You'll need it for login verification.",
        }

    def authenticate(self, token: str) -> dict:
        payload = decode_jwt_token(token)
        user_id = payload.get("user_id")
        if not isinstance(user_id, int):
            raise AuthenticationError("Invalid token")
        user = self._read(lambda: self.users.get_by_id(user_id))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        return {"user_id": user.id, "username": user.username}

    def login(self, data: UserLogin) -> dict:
        user = self._read(lambda: self.users.get_active_by_username(data.username))
        if not user or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid username or password")

        if not OTP_IS_ENABLED:
            return self._token_response(user, "Login successful (OTP disabled)")

        otp_session = OTPSession(
            user_id=user.id,
            session_token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow()
            + timedelta(minutes=OTP_SESSION_EXPIRATION_MINUTES),
            is_verified=False,
        )
        self._commit(lambda: self.otp_sessions.add(otp_session))
        return {
            "message": "Login successful. Please verify OTP to complete authentication.",
            "session_token": otp_session.session_token,
            "current_otp": generate_otp(user.otp_secret),
            "expires_in_minutes": OTP_SESSION_EXPIRATION_MINUTES,
            "note": "Use the OTP with your session token to get your JWT token",
        }

    def verify_otp(self, data: OTPVerification) -> dict:
        if not OTP_IS_ENABLED:
            raise ValidationError("OTP verification is currently disabled.")

        otp_session = self._read(
            lambda: self.otp_sessions.get_valid_unverified(
                data.session_token, datetime.utcnow()
            )
        )
        if not otp_session:
            raise ValidationError("Invalid or expired session token")

        user = self._read(lambda: self.users.get_by_id(otp_session.user_id))
        if not user or not verify_otp(user.otp_secret, data.otp_code):
            raise AuthenticationError("Invalid OTP code")

        otp_session.is_verified = True
        user.last_login_at = datetime.utcnow()
        self._commit()
        return self._token_response(user, "OTP verified successfully")

    def _token_response(self, user: User, message: str) -> dict:
        return {
            "message": message,
            "access_token": create_jwt_token(user.id, user.username),
            "token_type": "bearer",
            "expires_in_hours": JWT_EXPIRATION_HOURS,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }

    def _commit(self, operation=None) -> None:
        try:
            if operation:
                operation()
            self.db.commit()
        except SQLAlchemyError as exc:
            self.db.rollback()
            raise PersistenceError("Database operation failed") from exc

    @staticmethod
    def _read(operation):
        try:
            return operation()
        except SQLAlchemyError as exc:
            raise PersistenceError("Database operation failed") from exc
