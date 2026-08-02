import socket
import time

import psutil
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.config import OTP_IS_ENABLED


class SystemService:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.start_time = time.time()

    def health(self, db: Session) -> dict:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        memory_usage = psutil.virtual_memory().percent
        database_status = "healthy"
        database_latency_ms = None
        database_check_started = time.perf_counter()
        try:
            db.execute(text("SELECT 1"))
            database_latency_ms = round(
                (time.perf_counter() - database_check_started) * 1000,
                3,
            )
        except SQLAlchemyError:
            database_status = "unhealthy"
        health_status = (
            "healthy"
            if cpu_usage < 85
            and memory_usage < 90
            and database_status == "healthy"
            else "unhealthy"
        )
        return {
            "status": health_status,
            "details": {
                "otp_enabled": OTP_IS_ENABLED,
                "uptime_seconds": int(time.time() - self.start_time),
                "hostname": self.hostname,
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "database_status": database_status,
                "database_latency_ms": database_latency_ms,
            },
        }


system_service = SystemService()
