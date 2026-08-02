from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from core.exceptions import (
    ApplicationError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    OptimizationError,
    PersistenceError,
    ValidationError,
)

ERROR_STATUS_CODES = {
    ValidationError: status.HTTP_400_BAD_REQUEST,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    PersistenceError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    OptimizationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        _request: Request, exc: ApplicationError
    ) -> JSONResponse:
        status_code = ERROR_STATUS_CODES.get(
            type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})
