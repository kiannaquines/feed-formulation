from fastapi import APIRouter, Request

from services.system_service import system_service

root_router = APIRouter(tags=["Root Routes"])


@root_router.get("/")
def index_page(request: Request):
    return {
        "message": "Welcome to the Feed Formulation API with Authentication!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": system_service.hostname,
    }


@root_router.get("/health")
def health_check():
    return system_service.health()
