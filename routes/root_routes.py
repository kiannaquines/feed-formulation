from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db.database import get_db
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
        "message": "Welcome to the FeedPrime API!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": system_service.hostname,
    }


@root_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check service health",
    description=(
        "Report process uptime, hostname, OTP configuration, CPU usage, memory "
        "usage, and database connectivity. The service is unhealthy at 85% CPU, "
        "90% memory utilization, or when the database check fails."
    ),
)
def health_check(db: Session = Depends(get_db)):
    return system_service.health(db)
