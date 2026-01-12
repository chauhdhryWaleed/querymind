from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    connections,
    examples,
    favorites,
    feedback,
    health,
    history,
    llm_keys,
    me,
    query,
    stats,
    workspaces,
)

api_router = APIRouter()

api_router.include_router(health.router)

api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(workspaces.router)

api_router.include_router(connections.router)
api_router.include_router(llm_keys.router)

api_router.include_router(query.router)
api_router.include_router(history.router)
api_router.include_router(favorites.router)
api_router.include_router(feedback.router)
api_router.include_router(stats.router)
api_router.include_router(examples.router)
