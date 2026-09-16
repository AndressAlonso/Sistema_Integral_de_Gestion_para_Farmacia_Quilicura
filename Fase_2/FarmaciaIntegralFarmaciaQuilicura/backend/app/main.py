from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.auth.routes import COOKIE_NAME, router
from app.auth.state import AuthState
from app.auth.users import LocalUserRepository
from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.users = LocalUserRepository(settings.users_file)
        app.state.auth = AuthState()
        yield

    app = FastAPI(title="SIGFQ — E1-H1", lifespan=lifespan)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["Retry-After"],
    )

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # No devolver el cuerpo de entrada: contiene la contraseña.
        return JSONResponse(
            status_code=422,
            content={"detail": "Revisa el correo y la contraseña ingresados."},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )
        if exc.status_code == 401:
            response.delete_cookie(
                COOKIE_NAME,
                path="/api/auth",
                httponly=True,
                secure=settings.cookie_secure,
                samesite="strict",
            )
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "No pudimos procesar la solicitud."},
            headers={"Cache-Control": "no-store"},
        )

    app.include_router(router)
    return app
