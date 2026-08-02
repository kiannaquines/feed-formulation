from fastapi import APIRouter, Depends, status

from api.dependencies import (
    get_current_user,
    get_feed_formulation_service,
    get_feed_optimization_service,
)
from api.openapi import OWNED_RESOURCE_RESPONSES, PROTECTED_RESPONSES, VALIDATION_RESPONSE
from schema.schema import (
    DetailResponse,
    FeedFormulationRequest,
    FeedFormulationResponse,
    FeedFormulationUpdateResponse,
    FeedFormulationWithPayloadRequest,
    OptimizationFailureResponse,
    OptimizationSuccessResponse,
)
from services import FeedFormulationService, FeedOptimizationService

feed_formulation_router = APIRouter(tags=["Feed Formulation"])


@feed_formulation_router.post(
    "/feed/formulate",
    response_model=OptimizationSuccessResponse | OptimizationFailureResponse,
    summary="Calculate a least-cost feed formulation",
    description=(
        "Minimize ingredient cost with SciPy `linprog`. The mixture must total 100%, "
        "match all four nutrient targets exactly, and remain within every ingredient's "
        "minimum and maximum inclusion bounds. Input bounds use decimals from 0 to 1."
    ),
    responses={
        **PROTECTED_RESPONSES,
        400: {
            "model": DetailResponse,
            "description": "Ingredients or percentage constraints are invalid.",
        },
        500: {
            "model": DetailResponse,
            "description": "The configured optimization method could not be executed.",
        },
        **VALIDATION_RESPONSE,
    },
)
def feed_formulator(
    formulation_request: FeedFormulationRequest,
    _auth_user: dict = Depends(get_current_user),
    service: FeedOptimizationService = Depends(get_feed_optimization_service),
):
    return service.formulate(formulation_request)


@feed_formulation_router.post(
    "/feed/formulation/save",
    response_model=DetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a formulation result",
    description=(
        "Store a named formulation payload for the authenticated user. The server "
        "derives ownership from the Bearer token."
    ),
    responses={**PROTECTED_RESPONSES, **VALIDATION_RESPONSE},
)
def save_formulation(
    formulation: FeedFormulationWithPayloadRequest,
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.save(formulation, auth_user["user_id"])


@feed_formulation_router.get(
    "/feed/formulation/all",
    response_model=list[FeedFormulationResponse],
    status_code=status.HTTP_200_OK,
    summary="List saved formulations",
    description="Return every formulation owned by the authenticated user.",
    responses=PROTECTED_RESPONSES,
)
def get_all_formulation(
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.list_for_user(auth_user["user_id"])


@feed_formulation_router.delete(
    "/feed/formulation/remove/{formulation_id}",
    response_model=DetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a saved formulation",
    description="Delete a formulation owned by the authenticated user.",
    responses=OWNED_RESOURCE_RESPONSES,
)
def remove_formulation(
    formulation_id: int,
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.delete(formulation_id, auth_user["user_id"])


@feed_formulation_router.put(
    "/feed/formulation/update/{formulation_id}",
    response_model=FeedFormulationUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a saved formulation",
    description=(
        "Replace the name, description, and stored payload of a formulation owned "
        "by the authenticated user."
    ),
    responses=OWNED_RESOURCE_RESPONSES,
)
def update_formulation(
    formulation_id: int,
    payload: FeedFormulationWithPayloadRequest,
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.update(formulation_id, payload, auth_user["user_id"])


@feed_formulation_router.get(
    "/my/feed/formulation/",
    response_model=list[FeedFormulationResponse],
    status_code=status.HTTP_200_OK,
    summary="List my saved formulations",
    description=(
        "Compatibility endpoint returning the same authenticated-user formulation "
        "collection as `/feed/formulation/all`."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_my_formulations(
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.list_for_user(auth_user["user_id"])
