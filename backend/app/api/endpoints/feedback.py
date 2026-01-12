from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import current_user, current_workspace, require_csrf
from app.database.session import get_rw_session
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService

router = APIRouter(tags=["feedback"])


@router.post(
    "/query/{request_id}/feedback",
    response_model=FeedbackResponse,
    dependencies=[Depends(require_csrf)],
)
async def submit_feedback(
    request_id: str,
    payload: FeedbackRequest,
    session: Annotated[AsyncSession, Depends(get_rw_session)],
    workspace: Annotated[Workspace, Depends(current_workspace)],
    user: Annotated[User, Depends(current_user)],
) -> FeedbackResponse:
    return await FeedbackService(session).record(workspace.id, user.id, request_id, payload)
