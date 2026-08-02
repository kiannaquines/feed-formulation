from typing import Literal

from fastapi import APIRouter, Depends, status

from api.dependencies import (
    get_admin_pricing_service,
    get_current_admin,
    get_pricing_service,
)
from api.openapi import PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.schema import (
    PlanResponse,
    PricingPlanVersionCreate,
    PricingPlanVersionResponse,
)
from services import AdminPricingService, PricingService


pricing_router = APIRouter(tags=["Pricing"])
admin_pricing_router = APIRouter(tags=["Pricing Administration"])


@pricing_router.get(
    "/pricing/plans",
    response_model=list[PlanResponse],
    summary="List monthly pricing plans",
    description=(
        "Return the current public monthly price and quotas for Starter, Premium, "
        "and Ultra. Authentication is not required."
    ),
)
def get_pricing_plans(
    service: PricingService = Depends(get_pricing_service),
):
    return service.list_current()


@admin_pricing_router.get(
    "/admin/pricing/plans",
    response_model=list[PricingPlanVersionResponse],
    summary="List current pricing versions",
    description="Return the current immutable version of every fixed pricing plan.",
    responses=PROTECTED_RESPONSES,
)
def get_current_pricing_versions(
    _admin: dict = Depends(get_current_admin),
    service: AdminPricingService = Depends(get_admin_pricing_service),
):
    return service.list_current_versions()


@admin_pricing_router.get(
    "/admin/pricing/plans/{plan_code}/versions",
    response_model=list[PricingPlanVersionResponse],
    summary="List pricing version history",
    description="Return immutable pricing versions newest first.",
    responses=PROTECTED_RESPONSES,
)
def get_pricing_version_history(
    plan_code: Literal["starter", "premium", "ultra"],
    _admin: dict = Depends(get_current_admin),
    service: AdminPricingService = Depends(get_admin_pricing_service),
):
    return service.list_versions(plan_code)


@admin_pricing_router.post(
    "/admin/pricing/plans/{plan_code}/versions",
    response_model=PricingPlanVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Publish a pricing version",
    description=(
        "Publish a new monthly price and quota snapshot. Existing license terms "
        "continue using their saved pricing version."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def publish_pricing_version(
    plan_code: Literal["starter", "premium", "ultra"],
    payload: PricingPlanVersionCreate,
    admin: dict = Depends(get_current_admin),
    service: AdminPricingService = Depends(get_admin_pricing_service),
):
    return service.publish(plan_code, payload, admin["user_id"])
