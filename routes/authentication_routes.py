from fastapi import APIRouter, Depends

from api.dependencies import get_authentication_service
from api.openapi import VALIDATION_RESPONSE
from schema.schema import (
    DetailResponse,
    OTPChallengeResponse,
    OTPVerification,
    RegistrationResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from services import AuthenticationService

auth_router = APIRouter(tags=["Authentication"])


@auth_router.post(
    "/auth/register",
    response_model=RegistrationResponse,
    summary="Register a user",
    description=(
        "Create an active user account with a unique username and email address. "
        "The password is stored as a one-way bcrypt hash."
    ),
    responses={
        400: {"model": DetailResponse, "description": "Username or email already exists."},
        **VALIDATION_RESPONSE,
    },
)
def register_user(
    user_data: UserRegister,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.register(user_data)


@auth_router.post(
    "/auth/login",
    response_model=TokenResponse | OTPChallengeResponse,
    summary="Authenticate a user",
    description=(
        "Validate username and password. Returns a Bearer JWT immediately when "
        "OTP is disabled, otherwise returns a short-lived OTP session challenge."
    ),
    responses={
        401: {"model": DetailResponse, "description": "Invalid username or password."},
        **VALIDATION_RESPONSE,
    },
)
def login_user(
    login_data: UserLogin,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.login(login_data)


@auth_router.post(
    "/auth/verify-otp",
    response_model=TokenResponse,
    summary="Verify an OTP challenge",
    description=(
        "Complete an unexpired, unused OTP session and return a Bearer JWT. "
        "This endpoint is unavailable when OTP is disabled."
    ),
    responses={
        400: {"model": DetailResponse, "description": "OTP is disabled or the session is invalid."},
        401: {"model": DetailResponse, "description": "The OTP code is incorrect."},
        **VALIDATION_RESPONSE,
    },
)
def verify_user_otp(
    otp_data: OTPVerification,
    service: AuthenticationService = Depends(get_authentication_service),
):
    return service.verify_otp(otp_data)
