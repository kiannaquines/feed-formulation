import socket
import time

import psutil

from core.config import OTP_IS_ENABLED


class SystemService:
    def __init__(self):
        self.hostname = socket.gethostname()
        self.start_time = time.time()

    def health(self) -> dict:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        memory_usage = psutil.virtual_memory().percent
        health_status = (
            "healthy" if cpu_usage < 85 and memory_usage < 90 else "unhealthy"
        )
        return {
            "status": health_status,
            "details": {
                "otp_enabled": OTP_IS_ENABLED,
                "uptime_seconds": int(time.time() - self.start_time),
                "hostname": self.hostname,
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
            },
        }


system_service = SystemService()
