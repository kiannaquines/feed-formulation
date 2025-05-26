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

@app.get("/api/feed/formulate")
def feed_formulator(
    formulation_request: FeedFormulationRequest,
    auth_user: dict = Depends(verify_api_key_token)
):
    """Dynamic feed formulation endpoint (protected by API key or JWT token)"""
    
    from scipy.optimize import linprog

    if not formulation_request.ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ingredient must be provided"
        )

    ingredients = [ing.name for ing in formulation_request.ingredients]
    costs = np.array([ing.cost_per_kg for ing in formulation_request.ingredients])
    
    nutrient_matrix = np.array([
        [ing.protein_percent for ing in formulation_request.ingredients],
        [ing.energy_me for ing in formulation_request.ingredients],
        [ing.calcium_percent for ing in formulation_request.ingredients],
        [ing.phosphorus_percent for ing in formulation_request.ingredients]
    ])
    
    nutrient_req = np.array([
        formulation_request.nutrient_requirements.protein_percent,
        formulation_request.nutrient_requirements.energy_me,
        formulation_request.nutrient_requirements.calcium_percent,
        formulation_request.nutrient_requirements.phosphorus_percent
    ])
    
    ingredient_min = np.array([ing.min_percentage for ing in formulation_request.ingredients])
    ingredient_max = np.array([ing.max_percentage for ing in formulation_request.ingredients])
    
    if any(ingredient_min < 0) or any(ingredient_max > 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient percentages must be between 0 and 1"
        )
    
    if any(ingredient_min > ingredient_max):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum percentage cannot be greater than maximum percentage"
        )
    
    sum_constraint = np.ones((1, len(ingredients)))
    A_eq = np.vstack((sum_constraint, nutrient_matrix))
    b_eq = np.hstack(([1.0], nutrient_req))
    bounds = list(zip(ingredient_min, ingredient_max))

    try:
        result = linprog(
            costs, 
            A_eq=A_eq, 
            b_eq=b_eq, 
            bounds=bounds, 
            method=formulation_request.optimization_method
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )

    base_response = {
        "authenticated_user": auth_user['username'],
        "user_id": auth_user['id'],
        "formulation_inputs": {
            "total_ingredients": len(ingredients),
            "optimization_method": formulation_request.optimization_method,
            "ingredients": [
                {
                    "name": ing.name,
                    "cost_per_kg": ing.cost_per_kg,
                    "min_percentage": ing.min_percentage * 100,
                    "max_percentage": ing.max_percentage * 100
                }
                for ing in formulation_request.ingredients
            ],
            "nutrient_targets": {
                "protein_percent": formulation_request.nutrient_requirements.protein_percent,
                "energy_me": formulation_request.nutrient_requirements.energy_me,
                "calcium_percent": formulation_request.nutrient_requirements.calcium_percent,
                "phosphorus_percent": formulation_request.nutrient_requirements.phosphorus_percent
            }
        }
    }

    if result.success:
        ingredient_percentages = result.x * 100
        nutrient_values = nutrient_matrix @ result.x
        costs_breakdown = costs * result.x

        base_response.update({
            "status": "success",
            "message": "Optimal feed formulation found.",
            "optimization_details": {
                "solver_status": result.message,
                "iterations": getattr(result, 'nit', 'N/A'),
                "total_cost_per_kg": round(result.fun, 4)
            },
            "ingredient_composition": [
                {
                    "name": ingredients[i],
                    "percentage": round(ingredient_percentages[i], 4),
                    "cost_contribution": round(costs_breakdown[i], 4),
                    "included": ingredient_percentages[i] > 0.001
                }
                for i in range(len(ingredients))
            ],
            "nutrient_achievement": {
                "protein_percent": {
                    "achieved": round(nutrient_values[0], 4),
                    "required": round(formulation_request.nutrient_requirements.protein_percent, 4),
                    "difference": round(nutrient_values[0] - formulation_request.nutrient_requirements.protein_percent, 4)
                },
                "energy_me": {
                    "achieved": round(nutrient_values[1], 4),
                    "required": round(formulation_request.nutrient_requirements.energy_me, 4),
                    "difference": round(nutrient_values[1] - formulation_request.nutrient_requirements.energy_me, 4)
                },
                "calcium_percent": {
                    "achieved": round(nutrient_values[2], 4),
                    "required": round(formulation_request.nutrient_requirements.calcium_percent, 4),
                    "difference": round(nutrient_values[2] - formulation_request.nutrient_requirements.calcium_percent, 4)
                },
                "phosphorus_percent": {
                    "achieved": round(nutrient_values[3], 4),
                    "required": round(formulation_request.nutrient_requirements.phosphorus_percent, 4),
                    "difference": round(nutrient_values[3] - formulation_request.nutrient_requirements.phosphorus_percent, 4)
                }
            },
            "summary": {
                "total_ingredient_percentage": round(sum(result.x) * 100, 6),
                "active_ingredients_count": sum(1 for x in ingredient_percentages if x > 0.001),
                "cost_per_kg": round(result.fun, 4),
                "formulation_feasible": True
            }
        })
    else:
        base_response.update({
            "status": "failure",
            "message": "No optimal solution found.",
            "error_details": {
                "solver_status_code": result.status,
                "solver_message": result.message,
                "possible_causes": [
                    "Nutrient requirements may be impossible to meet with given ingredients",
                    "Ingredient constraints may be too restrictive",
                    "Cost optimization may have no feasible solution"
                ],
                "suggestions": [
                    "Review nutrient requirements and ensure they are achievable",
                    "Check ingredient min/max percentage constraints",
                    "Consider adding more ingredient options",
                    "Verify ingredient nutrient compositions are correct"
                ]
            },
            "formulation_feasible": False
        })

    return base_response

@app.post("/feed/formulate")
def feed_formulator(
    formulation_request: FeedFormulationRequest,
    auth_user: dict = Depends(verify_api_key_token)
):
    """Dynamic feed formulation endpoint (protected by API key)"""
    
    from scipy.optimize import linprog

    if not formulation_request.ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one ingredient must be provided"
        )

    ingredients = [ing.name for ing in formulation_request.ingredients]
    costs = np.array([ing.cost_per_kg for ing in formulation_request.ingredients])
    
    nutrient_matrix = np.array([
        [ing.protein_percent for ing in formulation_request.ingredients],
        [ing.energy_me for ing in formulation_request.ingredients],
        [ing.calcium_percent for ing in formulation_request.ingredients],
        [ing.phosphorus_percent for ing in formulation_request.ingredients]
    ])
    
    nutrient_req = np.array([
        formulation_request.nutrient_requirements.protein_percent,
        formulation_request.nutrient_requirements.energy_me,
        formulation_request.nutrient_requirements.calcium_percent,
        formulation_request.nutrient_requirements.phosphorus_percent
    ])
    
    ingredient_min = np.array([ing.min_percentage for ing in formulation_request.ingredients])
    ingredient_max = np.array([ing.max_percentage for ing in formulation_request.ingredients])
    
    if any(ingredient_min < 0) or any(ingredient_max > 1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ingredient percentages must be between 0 and 1"
        )
    
    if any(ingredient_min > ingredient_max):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum percentage cannot be greater than maximum percentage"
        )
    
    sum_constraint = np.ones((1, len(ingredients)))
    A_eq = np.vstack((sum_constraint, nutrient_matrix))
    b_eq = np.hstack(([1.0], nutrient_req))
    bounds = list(zip(ingredient_min, ingredient_max))

    try:
        result = linprog(
            costs, 
            A_eq=A_eq, 
            b_eq=b_eq, 
            bounds=bounds, 
            method=formulation_request.optimization_method
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Optimization failed: {str(e)}"
        )

    base_response = {
        "authenticated_user": auth_user['username'],
        "user_id": auth_user['id'],
        "formulation_inputs": {
            "total_ingredients": len(ingredients),
            "optimization_method": formulation_request.optimization_method,
            "ingredients": [
                {
                    "name": ing.name,
                    "cost_per_kg": ing.cost_per_kg,
                    "min_percentage": ing.min_percentage * 100,
                    "max_percentage": ing.max_percentage * 100
                }
                for ing in formulation_request.ingredients
            ],
            "nutrient_targets": {
                "protein_percent": formulation_request.nutrient_requirements.protein_percent,
                "energy_me": formulation_request.nutrient_requirements.energy_me,
                "calcium_percent": formulation_request.nutrient_requirements.calcium_percent,
                "phosphorus_percent": formulation_request.nutrient_requirements.phosphorus_percent
            }
        }
    }

    if result.success:
        ingredient_percentages = result.x * 100
        nutrient_values = nutrient_matrix @ result.x
        costs_breakdown = costs * result.x

        base_response.update({
            "status": "success",
            "message": "Optimal feed formulation found.",
            "optimization_details": {
                "solver_status": result.message,
                "iterations": getattr(result, 'nit', 'N/A'),
                "total_cost_per_kg": round(result.fun, 4)
            },
            "ingredient_composition": [
                {
                    "name": ingredients[i],
                    "percentage": round(ingredient_percentages[i], 4),
                    "cost_contribution": round(costs_breakdown[i], 4),
                    "included": ingredient_percentages[i] > 0.001
                }
                for i in range(len(ingredients))
            ],
            "nutrient_achievement": {
                "protein_percent": {
                    "achieved": round(nutrient_values[0], 4),
                    "required": round(formulation_request.nutrient_requirements.protein_percent, 4),
                    "difference": round(nutrient_values[0] - formulation_request.nutrient_requirements.protein_percent, 4)
                },
                "energy_me": {
                    "achieved": round(nutrient_values[1], 4),
                    "required": round(formulation_request.nutrient_requirements.energy_me, 4),
                    "difference": round(nutrient_values[1] - formulation_request.nutrient_requirements.energy_me, 4)
                },
                "calcium_percent": {
                    "achieved": round(nutrient_values[2], 4),
                    "required": round(formulation_request.nutrient_requirements.calcium_percent, 4),
                    "difference": round(nutrient_values[2] - formulation_request.nutrient_requirements.calcium_percent, 4)
                },
                "phosphorus_percent": {
                    "achieved": round(nutrient_values[3], 4),
                    "required": round(formulation_request.nutrient_requirements.phosphorus_percent, 4),
                    "difference": round(nutrient_values[3] - formulation_request.nutrient_requirements.phosphorus_percent, 4)
                }
            },
            "summary": {
                "total_ingredient_percentage": round(sum(result.x) * 100, 6),
                "active_ingredients_count": sum(1 for x in ingredient_percentages if x > 0.001),
                "cost_per_kg": round(result.fun, 4),
                "formulation_feasible": True
            }
        })
    else:
        base_response.update({
            "status": "failure",
            "message": "No optimal solution found.",
            "error_details": {
                "solver_status_code": result.status,
                "solver_message": result.message,
                "possible_causes": [
                    "Nutrient requirements may be impossible to meet with given ingredients",
                    "Ingredient constraints may be too restrictive",
                    "Cost optimization may have no feasible solution"
                ],
                "suggestions": [
                    "Review nutrient requirements and ensure they are achievable",
                    "Check ingredient min/max percentage constraints",
                    "Consider adding more ingredient options",
                    "Verify ingredient nutrient compositions are correct"
                ]
            },
            "formulation_feasible": False
        })

    return base_response

@app.get("/feed/formulate-jwt")
def feed_formulator_jwt(current_user: dict = Depends(get_current_user_from_token)):
    """Feed formulation endpoint (protected by JWT token only)"""
    return feed_formulator(auth_user=current_user)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)