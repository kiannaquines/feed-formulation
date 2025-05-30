from fastapi import APIRouter, Request
import socket
import time
import psutil
from core.config import OTP_IS_ENABLED
root_router = APIRouter(tags=["Root Routes"])

hostname = socket.gethostname()
start_time = time.time()

@root_router.get("/")
def index_page(request: Request):
    return {
        "message": "Welcome to the Feed Formulation API with Authentication!",
        "client_ip": request.client.host,
        "documentation": str(request.base_url) + "docs",
        "hostname": hostname,
    }

@root_router.get("/health")
def health_check():
    current_time = time.time()
    uptime_seconds = int(current_time - start_time)

    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory_usage = psutil.virtual_memory().percent

    if cpu_usage < 85 and memory_usage < 90:
        status = "healthy"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "details": {
            "otp_enabled": OTP_IS_ENABLED,
            "uptime_seconds": uptime_seconds,
            "hostname": hostname,
            "cpu_usage_percent": cpu_usage,
            "memory_usage_percent": memory_usage,
        }
    }