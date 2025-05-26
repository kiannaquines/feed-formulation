from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import time
import socket
import psutil
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from utils.constants import *
from utils.otp_utils import *
from utils.authentication_utils import *
from utils.database_utils import *
from models.models import *

security = HTTPBearer()

async def get_current_user_from_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    payload = verify_jwt_token(credentials.credentials)
    user_id = payload.get("user_id")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ? AND is_active = TRUE", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return dict(user)

async def verify_api_key_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key and return associated user"""
    key_hash = hash_api_key(credentials.credentials)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, ak.id as api_key_id 
            FROM users u 
            JOIN api_keys ak ON u.id = ak.user_id 
            WHERE ak.key_hash = ? AND ak.is_active = TRUE AND u.is_active = TRUE
        ''', (key_hash,))
        
        result = cursor.fetchone()
        
        if result:
            cursor.execute(
                "UPDATE api_keys SET last_used_at = CURRENT_TIMESTAMP, usage_count = usage_count + 1 WHERE id = ?",
                (result['api_key_id'],)
            )
            conn.commit()
            return dict(result)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )

init_database()

app = FastAPI(
    title="Feed Formulation API with Authentication",
    description="API for feed formulation and management with user authentication and OTP security",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()
hostname = socket.gethostname()

@app.get("/")
def index_page(request: Request):
    return {
        "message": "Welcome to the Feed Formulation API with Authentication!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": hostname,
        "authentication": {
            "methods": ["JWT Token", "API Key"],
            "endpoints": {
                "register": "POST /auth/register",
                "login": "POST /auth/login",
                "verify_otp": "POST /auth/verify-otp",
                "create_api_key": "POST /auth/api-keys"
            }
        }
    }

@app.get("/health")
def health_check():
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)

    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory_usage = psutil.virtual_memory().percent

    if cpu_usage < 85 and memory_usage < 90:
        status = "healthy"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "details": {
            "uptime_seconds": uptime_seconds,
            "hostname": hostname,
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": memory_usage,
        }
    }

@app.post("/auth/register")
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

@app.post("/auth/login")
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

@app.post("/auth/verify-otp")
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

@app.get("/auth/profile")
def get_user_profile(current_user: dict = Depends(get_current_user_from_token)):
    """Get current user profile"""
    return {
        "user": {
            "id": current_user['id'],
            "username": current_user['username'],
            "email": current_user['email'],
            "is_active": current_user['is_active'],
            "created_at": current_user['created_at'],
            "last_login_at": current_user['last_login_at']
        }
    }

@app.post("/auth/api-keys", response_model=APIKeyResponse)
def create_user_api_key(key_request: APIKeyCreate, current_user: dict = Depends(get_current_user_from_token)):
    """Create a new API key for the authenticated user"""
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO api_keys (user_id, key_hash, key_name)
                VALUES (?, ?, ?)
            ''', (current_user['id'], key_hash, key_request.key_name))
            conn.commit()
            
            return APIKeyResponse(
                api_key=api_key,
                key_name=key_request.key_name,
                message="API key created successfully. Store it securely - it won't be shown again!"
            )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key name already exists for this user"
            )

@app.get("/auth/api-keys")
def list_user_api_keys(current_user: dict = Depends(get_current_user_from_token)):
    """List all API keys for the authenticated user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT key_name, is_active, created_at, last_used_at, usage_count 
            FROM api_keys 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        ''', (current_user['id'],))
        
        keys = cursor.fetchall()
        
        return {
            "api_keys": [dict(key) for key in keys]
        }

@app.delete("/auth/api-keys/{key_name}")
def deactivate_user_api_key(key_name: str, current_user: dict = Depends(get_current_user_from_token)):
    """Deactivate an API key for the authenticated user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE api_keys SET is_active = FALSE 
            WHERE key_name = ? AND user_id = ?
        ''', (key_name, current_user['id']))
        
        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        conn.commit()
        return {"message": f"API key '{key_name}' has been deactivated"}

@app.get("/feed/formulate")
def feed_formulator(auth_user: dict = Depends(verify_api_key_token)):
    """Feed formulation endpoint (protected by API key or JWT token)"""
    
    from scipy.optimize import linprog

    ingredients = [
        'Corn', 'Soybean Meal', 'Skimmilk', 'Rice bran D1', 'Fish Meal',
        'Coconut Oil', 'Limestone', 'Monodical Phosphate', 'Vitamin Premix',
        'Choline', 'Salt', 'L-lysine', 'DL-Methionine', 'Antioxidant', 'Azolla'
    ]

    c = np.array([75, 100, 250, 80, 150, 50, 6.3, 80, 185, 640,
                  28, 1279, 120, 200, 350])

    A_nutrients = np.array([
        [7.8, 43.1, 33.5, 12.4, 58.7, 0, 0, 0, 0, 0, 0, 74, 58, 0, 21.3],
        [3.3, 2.24, 2.51, 2.4, 2.8, 8.6, 0, 0, 0, 0, 0, 3.625, 3.6, 0, 1.0513],
        [0.07, 0.45, 1.25, 0.07, 4.68, 0, 38, 16, 0, 0, 0, 0, 0, 0, 0.45],
        [0.06, 0.19, 0.95, 0.23, 2.86, 0, 0, 18, 0, 0, 0, 0, 0, 0, 0.35]
    ])

    nutrient_req = np.array([22.3, 2.9, 0.87, 0.48])

    ingredient_min = np.array([
        0.45, 0.25, 0.02, 0.05, 0.01, 0, 0, 0, 0.0025,
        0.0025, 0.0025, 0.0025, 0, 0.0025, 0.010
    ])

    ingredient_max = np.array([
        0.70, 0.30, 1, 0.5, 0.5, 1, 1, 1, 0.0025,
        0.0025, 0.0025, 0.0025, 1, 0.0025, 0.010
    ])

    sum_constraint = np.ones((1, len(ingredients)))
    A_eq = np.vstack((sum_constraint, A_nutrients))
    b_eq = np.hstack(([1.0], nutrient_req))
    bounds = list(zip(ingredient_min, ingredient_max))

    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')

    base_response = {
        "authenticated_user": auth_user['username'],
        "user_id": auth_user['id']
    }

    if result.success:
        ingredient_percentages = result.x * 100
        nutrient_values = A_nutrients @ result.x
        costs = c * result.x

        base_response.update({
            "status": "success",
            "message": "Optimal feed formulation found.",
            "total_cost_per_kg": round(result.fun, 2),
            "ingredient_composition_percent": {
                ingredients[i]: round(ingredient_percentages[i], 4)
                for i in range(len(ingredients))
                if ingredient_percentages[i] > 0
            },
            "nutrient_achievement": {
                "Protein (% CP)": round(nutrient_values[0], 4),
                "Energy (ME)": round(nutrient_values[1], 4),
                "Calcium (% Ca)": round(nutrient_values[2], 4),
                "Phosphorus (% P)": round(nutrient_values[3], 4),
            },
            "nutrient_requirements": {
                "Protein (% CP)": round(nutrient_req[0], 4),
                "Energy (ME)": round(nutrient_req[1], 4),
                "Calcium (% Ca)": round(nutrient_req[2], 4),
                "Phosphorus (% P)": round(nutrient_req[3], 4),
            },
            "cost_breakdown_per_ingredient": {
                ingredients[i]: round(costs[i], 4)
                for i in range(len(ingredients))
                if costs[i] > 0
            },
            "total_ingredient_percentage": round(sum(result.x) * 100, 6)
        })
    else:
        base_response.update({
            "status": "failure",
            "message": "No optimal solution found.",
            "solver_status_code": result.status,
            "solver_message": result.message
        })

    return base_response

@app.get("/feed/formulate-jwt")
def feed_formulator_jwt(current_user: dict = Depends(get_current_user_from_token)):
    """Feed formulation endpoint (protected by JWT token only)"""
    return feed_formulator(auth_user=current_user)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)