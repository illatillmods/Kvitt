from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def ready(request: Request) -> JSONResponse:
    settings = get_settings()
    database_ready = bool(getattr(request.app.state, "database_ready", False))
    startup_error = getattr(request.app.state, "startup_error", None)
    response = ReadinessResponse(
        status="ok" if database_ready else "degraded",
        service=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
        database_ready=database_ready,
        startup_error=startup_error,
    )
    status_code = status.HTTP_200_OK if database_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response.model_dump())
