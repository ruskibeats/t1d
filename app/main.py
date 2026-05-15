"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

from app.agents.coordinator import AgentCoordinator
from app.config import get_settings
from app.core.database import init_db
from app.core.errors import (
    AuthenticationError,
    ErrorResponse,
    T1DException,
)
from app.core.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global app instance and coordinator
app = None
coordinator: AgentCoordinator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events."""
    # Startup
    settings = get_settings()

    logger.info("Starting T1D Companion application")

    # Initialize database
    await init_db()

    # Initialize agent coordinator
    global coordinator
    coordinator = AgentCoordinator()
    await coordinator.startup()

    logger.info("T1D Companion started successfully!")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"API docs: {settings.api_docs_url}")

    yield

    # Shutdown
    logger.info("Shutting down T1D Companion...")
    await coordinator.shutdown()
    logger.info("T1D Companion stopped.")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    global app

    if app is not None:
        return app

    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        description=settings.app_description,
        version=settings.version,
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None if settings.environment == "production" else "/redoc",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log incoming requests."""
        if request.url.path.startswith(("/docs", "/openapi.json", "/health", "/static")):
            return await call_next(request)

        logger.info(
            "Request received",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        response = await call_next(request)
        return response

    # Exception handlers
    @app.exception_handler(T1DException)
    async def t1d_exception_handler(request: Request, exc: T1DException):
        """Handle T1D-specific exceptions."""
        logger.error(
            exc.message,
            extra={
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.__class__.__name__,
                message=exc.message,
                detail=exc.details,
            ).model_dump(),
        )

    @app.exception_handler(AuthenticationError)
    async def auth_exception_handler(request: Request, exc: AuthenticationError):
        """Handle authentication exceptions."""
        logger.warning(
            "Authentication failed",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error="AuthenticationError",
                message=exc.message,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors."""
        logger.error(
            "Unhandled exception",
            extra={
                "exception": str(exc),
                "path": request.url.path,
                "method": request.method,
            },
        )

        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="InternalServerError",
                message="An unexpected error occurred. Please try again later.",
                detail={"exception_type": type(exc).__name__} if settings.environment == "development" else None,
            ).model_dump(),
        )

    # Custom docs endpoint with disclaimer
    @app.get("/docs", include_in_schema=False)
    async def custom_docs():
        """Custom docs page with safety disclaimer."""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{settings.app_title} - API Documentation",
            swagger_favicon_url="/favicon.ico",
        )

    # Root endpoint
    @app.get("/", tags=["Info"])
    async def root() -> dict:
        """Root endpoint with service information."""
        return {
            "service": settings.app_title,
            "version": settings.version,
            "description": settings.app_description,
            "status": "running",
            "environment": settings.environment,
            "disclaimer": (
                "This service provides educational insights based on personal health data. "
                "It does not provide medical advice, diagnosis, or treatment recommendations. "
                "Always consult your healthcare provider regarding diabetes management."
            ),
            "endpoints": {
                "docs": "/docs",
                "health": "/health",
                "auth": "/auth/login",
                "glucose": "/api/v1/glucose",
                "events": "/api/v1/events",
                "patterns": "/api/v1/patterns",
                "chat": "/api/v1/chat",
            },
        }

    # Health check endpoint
    @app.get("/health", tags=["Info"])
    async def health_check() -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": settings.app_title,
            "version": settings.version,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }

    # Include routers
    from app.api import (
        auth,
        chat,
        events,
        glucose,
        glucose_ext,
        patterns,
        users,
    )

    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(glucose.router, prefix="/api/v1", tags=["Glucose Data"])
    app.include_router(glucose_ext.router, prefix="/api/v1", tags=["Glucose Data"])
    app.include_router(events.router, prefix="/api/v1", tags=["Context Events"])
    app.include_router(patterns.router, prefix="/api/v1", tags=["Patterns"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Conversational AI"])

    logger.info("Application setup complete")

    return app


# Create app instance
app = create_app()
