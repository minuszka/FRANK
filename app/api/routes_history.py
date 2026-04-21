from fastapi import APIRouter, Depends, Query

from app.schemas.chat import HistoryDeleteResponse, HistoryResponse
from app.services.history_service import HistoryService
from app.dependencies import get_history_service

router = APIRouter(tags=["history"])


@router.get("/api/history", response_model=HistoryResponse)
async def get_history(
    session_id: str = Query(default="default"),
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryResponse:
    return HistoryResponse(session_id=session_id, messages=history_service.get(session_id))


@router.delete("/api/history", response_model=HistoryDeleteResponse)
async def delete_history(
    session_id: str = Query(default="default"),
    history_service: HistoryService = Depends(get_history_service),
) -> HistoryDeleteResponse:
    deleted = history_service.clear(session_id)
    return HistoryDeleteResponse(session_id=session_id, deleted=deleted)

