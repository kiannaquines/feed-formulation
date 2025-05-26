from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class OTPVerification(BaseModel):
    session_token: str
    otp_code: str

class APIKeyCreate(BaseModel):
    key_name: str

class APIKeyResponse(BaseModel):
    api_key: str
    key_name: str
    message: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: str