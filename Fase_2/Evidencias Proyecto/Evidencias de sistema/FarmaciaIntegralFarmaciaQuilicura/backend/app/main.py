from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.catalog.repository import PostgresCatalogRepository
from app.catalog.routes import router as catalog_router
from app.auth.routes import COOKIE_NAME, COOKIE_PATH, router
from app.auth.sessions import SessionRepository
from app.auth.state import AuthState
from app.auth.users import PostgresUserRepository
from app.branches.repository import PostgresBranchRepository
from app.branches.routes import router as branches_router
from app.config import Settings
from app.db import create_database_engine, create_session_factory
from app.users.routes import router as users_router


def create_app(settings: Settings | None = None, session_factory=None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = None if session_factory is not None else create_database_engine()

        try:
            factory = (
                session_factory
                if session_factory is not None
                else create_session_factory(engine)
            )

            app.state.users = PostgresUserRepository(factory)
            app.state.branches = PostgresBranchRepository(factory)
            app.state.catalog = PostgresCatalogRepository(factory)
            app.state.sessions = SessionRepository(factory)
            app.state.auth = AuthState()

            yield
        finally:
            if engine is not None:
                engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"],
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
        if request.url.path.startswith("/api/users"):
            detail = (
                "Revisa los datos, los roles y la sucursal. "
                "La contraseña inicial requiere al menos 12 caracteres."
            )
        elif request.url.path.startswith("/api/branches"):
            detail = (
                "Revisa el código, el nombre y la dirección de la sucursal."
            )
        elif request.url.path.startswith("/api/categories"):
            detail = "Ingresa un nombre de categoría de entre 1 y 150 caracteres."
        elif request.url.path.startswith("/api/products"):
            detail = "Revisa los datos del producto."
        elif request.url.path.startswith("/api/products"):
            detail = "Revisa nombre, SKU, categoría, precio y códigos de barras."
        else:
            detail = "Revisa el correo y la contraseña ingresados."

        return JSONResponse(
            status_code=422,
            content={"detail": detail},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

        if exc.status_code == 401:
            response.delete_cookie(COOKIE_NAME, path="/api/auth")
            response.delete_cookie(
                COOKIE_NAME,
                path=COOKIE_PATH,
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
    app.include_router(users_router)
    app.include_router(branches_router)
    app.include_router(catalog_router)
    return app