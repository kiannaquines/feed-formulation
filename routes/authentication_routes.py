from fastapi import APIRouter, HTTPException, status
from core.config import *
from core.otp import *
from db.database import *
from models.models import *
from core.authentication import *

auth_router = APIRouter(tags=["Authentication"])

@auth_router.post("/auth/register")
def register_user(user_data: UserRegister):
    """Register a new user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", 
                      (user_data.username, user_data.email))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        password_hash = hash_password(user_data.password)
        otp_secret = generate_otp_secret()
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, otp_secret)
            VALUES (?, ?, ?, ?)
        ''', (user_data.username, user_data.email, password_hash, otp_secret))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return {
            "message": "User registered successfully",
            "user_id": user_id,
            "otp_secret": otp_secret,
            "note": "Save your OTP secret securely. You'll need it for login verification."
        }

@auth_router.post("/auth/login")
def login_user(login_data: UserLogin):
    """Login user and initiate OTP verification"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND is_active = TRUE", 
                      (login_data.username,))
        user = cursor.fetchone()
        
        if not user or not verify_password(login_data.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        cursor.execute('''
            INSERT INTO otp_sessions (user_id, session_token, expires_at)
            VALUES (?, ?, ?)
        ''', (user['id'], session_token, expires_at))
        conn.commit()
        
        current_otp = generate_otp(user['otp_secret'])
        
        return {
            "message": "Login successful. Please verify OTP to complete authentication.",
            "session_token": session_token,
            "current_otp": current_otp,
            "expires_in_minutes": 10,
            "note": "Use the OTP with your session token to get your JWT token"
        }

@auth_router.post("/auth/verify-otp")
def verify_user_otp(otp_data: OTPVerification):
    """Verify OTP and return JWT token"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT os.*, u.* FROM otp_sessions os
            JOIN users u ON os.user_id = u.id
            WHERE os.session_token = ? AND os.expires_at > ? AND os.is_verified = FALSE
        ''', (otp_data.session_token, datetime.utcnow()))
        
        session = cursor.fetchone()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired session token"
            )
        
        if not verify_otp(session['otp_secret'], otp_data.otp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP code"
            )
        
        cursor.execute("UPDATE otp_sessions SET is_verified = TRUE WHERE session_token = ?", 
                      (otp_data.session_token,))
        cursor.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", 
                      (session['user_id'],))
        conn.commit()
        
        jwt_token = create_jwt_token(session['user_id'], session['username'])
        
        return {
            "message": "OTP verified successfully",
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in_hours": JWT_EXPIRATION_HOURS,
            "user": {
                "id": session['user_id'],
                "username": session['username'],
                "email": session['email']
            }
        }
