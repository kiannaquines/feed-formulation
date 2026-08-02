from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.models import OTPSession, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        statement = select(User).where(
            or_(
                User.username.in_((username, email)),
                User.email.in_((username, email)),
            )
        )
        return self.db.scalar(statement)

    def get_active_by_username_or_email(self, identifier: str) -> User | None:
        statement = select(User).where(
            or_(User.username == identifier, User.email == identifier),
            User.is_active.is_(True),
        )
        return self.db.scalar(statement)

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class OTPSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_valid_unverified(
        self, session_token: str, current_time: datetime
    ) -> OTPSession | None:
        statement = (
            select(OTPSession)
            .join(User)
            .where(
                OTPSession.session_token == session_token,
                OTPSession.expires_at > current_time,
                OTPSession.is_verified.is_(False),
            )
        )
        return self.db.scalar(statement)

    def add(self, otp_session: OTPSession) -> OTPSession:
        self.db.add(otp_session)
        self.db.flush()
        return otp_session
