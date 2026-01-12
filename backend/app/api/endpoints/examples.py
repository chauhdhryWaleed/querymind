from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import require_api_key
from app.services.examples_service import ExamplesResponse, get_examples

router = APIRouter(tags=["examples"], dependencies=[Depends(require_api_key)])


@router.get("/examples", response_model=ExamplesResponse)
async def list_examples() -> ExamplesResponse:
    return get_examples()
