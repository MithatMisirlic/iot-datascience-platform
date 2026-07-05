"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api.v1.router import api_router
from backend.app.db.init_db import create_tables
from backend.app.db.session import engine
from backend.app.schemas.exercise_data import SignalFloat


API_DESCRIPTION = (
    "REST API for managing experiments and exercises in a research study "
    "investigating the relationship between language and movement in "
    "Parkinson's patients."
)

OPENAPI_TAGS = [
    {"name": "Experiments", "description": "Manage experiments (the umbrella entity)."},
    {"name": "Exercises", "description": "Manage exercises within experiments."},
    {"name": "Recording", "description": "Control data recording for an exercise."},
    {
        "name": "Data",
        "description": "Retrieve and clear recorded and processed exercise data.",
    },
]


def startup() -> None:
    """Initialize database tables when the application starts."""

    create_tables()


def shutdown() -> None:
    """Release pooled database connections when the application stops."""

    engine.dispose()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Run application startup and shutdown hooks."""

    del application
    startup()
    try:
        yield
    finally:
        shutdown()


app = FastAPI(
    title="Experiment API",
    version="1.0.0",
    description=API_DESCRIPTION,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
    servers=[
        {
            "url": "http://localhost:3000",
            "description": "Local development server",
        }
    ],
)
app.openapi_version = "3.0.3"

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8501",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(StarletteHTTPException)
async def contract_http_error(
    request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    """Use the contract error schema for documented client errors."""

    del request
    key = "error" if exception.status_code in {400, 404, 409} else "detail"
    return JSONResponse(
        status_code=exception.status_code,
        content={key: str(exception.detail)},
        headers=exception.headers,
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """Return the contract's error shape for invalid requests."""

    del request, exception
    return JSONResponse(
        status_code=400,
        content={"error": "The request is invalid."},
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Return basic service identity and state."""

    return {"name": "Experiment API", "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Return the service health state."""

    return {"status": "healthy"}


def _convert_nullable_schemas(value: Any) -> None:
    """Convert JSON Schema null unions to OpenAPI 3.0 nullable fields."""

    if isinstance(value, dict):
        alternatives = value.get("anyOf")
        if isinstance(alternatives, list) and len(alternatives) == 2:
            null_options = [item for item in alternatives if item == {"type": "null"}]
            non_null_options = [
                item for item in alternatives if item != {"type": "null"}
            ]
            if len(null_options) == 1 and len(non_null_options) == 1:
                remaining = {key: item for key, item in value.items() if key != "anyOf"}
                value.clear()
                value.update(non_null_options[0])
                value.update(remaining)
                value["nullable"] = True
        for item in value.values():
            _convert_nullable_schemas(item)
    elif isinstance(value, list):
        for item in value:
            _convert_nullable_schemas(item)


def generate_openapi_schema() -> dict[str, Any]:
    """Generate OpenAPI while retaining all components named by the contract."""

    if app.openapi_schema is None:
        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
            servers=app.servers,
        )
        schema.setdefault("components", {}).setdefault("schemas", {})[
            "SignalFloat"
        ] = SignalFloat.model_json_schema()
        for path_item in schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict):
                    operation.get("responses", {}).pop("422", None)
        schema["components"]["schemas"].pop("HTTPValidationError", None)
        schema["components"]["schemas"].pop("ValidationError", None)
        _convert_nullable_schemas(schema)
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = generate_openapi_schema
