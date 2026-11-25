from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
import os

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.rate_limit import limiter

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API for the Smart Civic Issue Detection, Prioritization and "
        "Resolution Management System."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "message": "Too many requests. Please try again later.",
            "error_code": "RATE_LIMIT_EXCEEDED",
        },
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "error_code": "HTTP_ERROR"},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            # Only JSON-safe fields: exc.errors() can embed the raw
            # ValueError from custom validators, which can't be serialised.
            "details": [
                {"loc": list(e.get("loc", [])), "message": e.get("msg", ""), "type": e.get("type", "")}
                for e in exc.errors()
            ],
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected error occurred",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


@app.get("/api/health", tags=["system"])
def health_check():
    return {"success": True, "message": "ok", "environment": settings.APP_ENV}


os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIRECTORY), name="uploads")


from app.api import auth as auth_router  # noqa: E402
from app.api import citizens as citizens_router  # noqa: E402
from app.api import issues as issues_router  # noqa: E402
from app.api import ai as ai_router  # noqa: E402
from app.api import otp as otp_router  # noqa: E402
from app.api import admin_issues as admin_issues_router  # noqa: E402
from app.api import admin_staff as admin_staff_router  # noqa: E402
from app.api import staff as staff_router  # noqa: E402

app.include_router(auth_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(citizens_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(issues_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(otp_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_issues_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_staff_router.router, prefix=settings.API_V1_PREFIX)
app.include_router(staff_router.router, prefix=settings.API_V1_PREFIX)

# Phase 7+ will add: admin, staff, departments, users routers.
