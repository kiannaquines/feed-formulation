from fastapi import APIRouter, Depends, status

from api.dependencies import (
    get_current_user,
    get_feed_formulation_service,
    get_feed_optimization_service,
)
from schema.schema import (
    DetailResponse,
    FeedFormulationRequest,
    FeedFormulationResponse,
    FeedFormulationUpdateResponse,
    FeedFormulationWithPayloadRequest,
)
from services import FeedFormulationService, FeedOptimizationService

feed_formulation_router = APIRouter(tags=["Feed Formulation"])


@feed_formulation_router.post("/feed/formulate")
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
)
def get_my_formulations(
    auth_user: dict = Depends(get_current_user),
    service: FeedFormulationService = Depends(get_feed_formulation_service),
):
    return service.list_for_user(auth_user["user_id"])
