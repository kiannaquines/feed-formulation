from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from api.dependencies import (
    get_admin_licensing_service,
    get_current_admin,
    get_current_user,
    get_licensing_service,
)
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.schema import (
    DeviceResponse,
    LicenseActivationRequest,
    LicenseReassignmentRequest,
    LicenseRenewalRequest,
    LicenseResponse,
    LicenseRevocationRequest,
    LicensingStatusResponse,
    PlanResponse,
    ReferralClaimRequest,
    ReferralSummaryResponse,
)
from services import AdminLicensingService, LicensingService


licensing_router = APIRouter(tags=["Licensing"])
admin_licensing_router = APIRouter(tags=["License Administration"])


@licensing_router.get(
    "/licensing/plans",
    response_model=list[PlanResponse],
    summary="List licensing plans",
    description="Return the annual per-device PHP prices and storage quotas.",
)
def get_plans(
    service: LicensingService = Depends(get_licensing_service),
):
    return service.plans()


@licensing_router.get(
    "/licensing/status",
    response_model=LicensingStatusResponse,
    summary="Get this device's license status",
    description=(
        "Return the effective trial or paid license and current account-wide quota "
        "usage for the authenticated device."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_license_status(
    auth_user: dict = Depends(get_current_user),
    service: LicensingService = Depends(get_licensing_service),
):
    return service.status(auth_user)


@licensing_router.get(
    "/licensing/devices",
    response_model=list[DeviceResponse],
    summary="List registered devices",
    description="Return every installation registered to the authenticated account.",
    responses=PROTECTED_RESPONSES,
)
def get_devices(
    auth_user: dict = Depends(get_current_user),
    service: LicensingService = Depends(get_licensing_service),
):
    return service.devices(auth_user["user_id"])


@licensing_router.get(
    "/referrals/me",
    response_model=ReferralSummaryResponse,
    summary="Get referral status",
    description=(
        "Return the account's referral code, referral totals, and earned 30-day "
        "license credits."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_referrals(
    auth_user: dict = Depends(get_current_user),
    service: LicensingService = Depends(get_licensing_service),
):
    return service.referral_summary(auth_user["user_id"])


@licensing_router.post(
    "/referrals/credits/{credit_id}/claim",
    response_model=LicenseResponse,
    summary="Claim a referral credit",
    description=(
        "Extend one chosen active paid device license by the credit's 30 bonus days."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def claim_referral_credit(
    credit_id: int,
    payload: ReferralClaimRequest,
    auth_user: dict = Depends(get_current_user),
    service: LicensingService = Depends(get_licensing_service),
):
    return service.claim_referral_credit(
        credit_id, payload.license_id, auth_user["user_id"]
    )


@admin_licensing_router.get(
    "/admin/licenses",
    response_model=list[LicenseResponse],
    summary="List device licenses",
    description="List trial and paid licenses using optional administrative filters.",
    responses=PROTECTED_RESPONSES,
)
def list_licenses(
    user_id: int | None = None,
    license_status: Literal["active", "revoked"] | None = Query(
        default=None, alias="status"
    ),
    plan_code: Literal["starter", "premium", "ultra"] | None = None,
    expires_before: datetime | None = None,
    _admin: dict = Depends(get_current_admin),
    service: AdminLicensingService = Depends(get_admin_licensing_service),
):
    return service.list_licenses(
        user_id, license_status, plan_code, expires_before
    )


@admin_licensing_router.post(
    "/admin/licenses/activate",
    response_model=LicenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activate a paid device license",
    description=(
        "Record an offline annual payment and activate one plan for one owned device."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def activate_license(
    payload: LicenseActivationRequest,
    admin: dict = Depends(get_current_admin),
    service: AdminLicensingService = Depends(get_admin_licensing_service),
):
    return service.activate(
        payload.user_id,
        payload.device_id,
        payload.plan_code,
        payload.payment_reference,
        admin["user_id"],
    )


@admin_licensing_router.post(
    "/admin/licenses/{license_id}/renew",
    response_model=LicenseResponse,
    summary="Renew a paid device license",
    description=(
        "Record a new offline payment and add 365 days, optionally changing tier "
        "at the renewal boundary."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def renew_license(
    license_id: int,
    payload: LicenseRenewalRequest,
    admin: dict = Depends(get_current_admin),
    service: AdminLicensingService = Depends(get_admin_licensing_service),
):
    return service.renew(
        license_id,
        payload.plan_code,
        payload.payment_reference,
        admin["user_id"],
    )


@admin_licensing_router.post(
    "/admin/licenses/{license_id}/revoke",
    response_model=LicenseResponse,
    summary="Revoke a paid device license",
    description="Revoke a paid license and record the administrator's reason.",
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def revoke_license(
    license_id: int,
    payload: LicenseRevocationRequest,
    admin: dict = Depends(get_current_admin),
    service: AdminLicensingService = Depends(get_admin_licensing_service),
):
    return service.revoke(license_id, payload.reason, admin["user_id"])


@admin_licensing_router.post(
    "/admin/licenses/{license_id}/reassign",
    response_model=LicenseResponse,
    summary="Reassign a paid device license",
    description=(
        "Move a paid license to another device owned by the same account and audit "
        "the reason. Trial licenses cannot be moved."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def reassign_license(
    license_id: int,
    payload: LicenseReassignmentRequest,
    admin: dict = Depends(get_current_admin),
    service: AdminLicensingService = Depends(get_admin_licensing_service),
):
    return service.reassign(
        license_id, payload.device_id, payload.reason, admin["user_id"]
    )
