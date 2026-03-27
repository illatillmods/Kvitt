import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.errors import ReceiptProcessingError
from app.db.session import Base, get_engine
from app.schemas.error import ApiErrorDetail, ApiErrorResponse

settings = get_settings()
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def initialize_database() -> None:
    engine = get_engine()

    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.database_ready = False
    app.state.startup_error = None

    try:
        initialize_database()
        app.state.database_ready = True
    except Exception as exc:
        app.state.startup_error = str(exc)
        logger.exception("Database startup failed")
        if settings.require_db_ready:
            raise

    yield


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        start = perf_counter()

        response = await call_next(request)

        duration_ms = int((perf_counter() - start) * 1000)
        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING

        logger.log(
            log_level,
            "request_completed request_id=%s method=%s path=%s status_code=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(ReceiptProcessingError)
    async def receipt_processing_error_handler(
        request: Request,
        exc: ReceiptProcessingError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "receipt_processing_failed request_id=%s stage=%s code=%s path=%s message=%s",
            request_id,
            exc.stage,
            exc.code,
            request.url.path,
            exc.message,
        )
        payload = ApiErrorResponse(
            error=ApiErrorDetail(
                code=exc.code,
                message=exc.message,
                stage=exc.stage,
                retryable=exc.retryable,
                suggestions=exc.suggestions,
                request_id=request_id,
            )
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_request_error request_id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        payload = ApiErrorResponse(
            error=ApiErrorDetail(
                code="internal_error",
                message="Ett oväntat serverfel inträffade.",
                stage="server",
                retryable=True,
                suggestions=["Försök igen om en stund.", "Om felet kvarstår, använd manuell registrering."],
                request_id=request_id,
            )
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app

app = create_app()
