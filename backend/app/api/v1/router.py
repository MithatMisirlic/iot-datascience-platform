"""Version 1 API router registration."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints import data, exercises, experiments, recording


api_router = APIRouter()
api_router.include_router(experiments.router)
api_router.include_router(exercises.router)
api_router.include_router(recording.router)
api_router.include_router(data.router)
