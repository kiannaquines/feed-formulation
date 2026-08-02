from fastapi import APIRouter, Depends

from api.dependencies import get_authentication_service
from schema.schema import OTPVerification, UserLogin, UserRegister
from services import AuthenticationService

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post("/auth/register")
def register_user(
    user_data: UserRegister,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.register(user_data)


@auth_router.post("/auth/login")
def login_user(
    login_data: UserLogin,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.login(login_data)


@auth_router.post("/auth/verify-otp")
def verify_user_otp(
    otp_data: OTPVerification,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.verify_otp(otp_data)
