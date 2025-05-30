from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, JSON
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    otp_secret = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)

    otp_sessions = relationship("OTPSession", back_populates="user")


class OTPSession(Base):
    __tablename__ = "otp_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String, unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="otp_sessions")

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    price = Column(Float, nullable=False)
    crude_protein = Column(Float, nullable=False)
    crude_fat = Column(Float, nullable=False)
    crude_fiber = Column(Float, nullable=False)
    metabolized_energy = Column(Float, nullable=False)
    calcium = Column(Float, nullable=False)
    total_phosphorus = Column(Float, nullable=False)
    avail_phosphorus = Column(Float, nullable=False)
    lysine = Column(Float, nullable=False)
    methionine = Column(Float, nullable=False)
    m_c = Column(Float, nullable=False)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FeedFormulation(Base):
    __tablename__ = "formulations"

    id = Column(Integer, primary_key=True, index=True)
    formulation_name = Column(String, nullable=True)
    formulation_description = Column(String, nullable=True)
    user_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)

class NutrientRequirements(Base):
    __tablename__ = "nutrient_requirements"

    id = Column(Integer, primary_key=True, index=True)
    nutrient_requirement_name = Column(String, nullable=False)
    nutrient_requirement_description = Column(String, nullable=True)
    composition = Column(JSON, nullable=False)


