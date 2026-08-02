from fastapi import APIRouter, Request

from schema.schema import HealthResponse, RootResponse
from services.system_service import system_service

root_router = APIRouter(tags=["System"])


@root_router.get(
    "/",
    response_model=RootResponse,
    summary="Discover the API",
    description="Return the service identity, host, client address, and documentation URL.",
)
def index_page(request: Request):
    return {
        "message": "Welcome to the Feed Formulation API with Authentication!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": system_service.hostname,
    }


@root_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description=(
        "Report process uptime, hostname, OTP configuration, CPU usage, and memory "
        "usage. The service is unhealthy at 85% CPU or 90% memory utilization."
    ),
)
def health_check():
    return system_service.health()
