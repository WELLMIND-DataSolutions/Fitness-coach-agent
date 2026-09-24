"""Chat endpoint and conversation history."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.agent import LLMUnavailable, run_chat
from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user, limiter
from app.models import ChatMessage, User
from app.schemas import ChatRequest, ChatResponse, HistoryMessage

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit(lambda: get_settings().chat_rate_limit)
def chat(
    request: Request,
    body: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        reply = run_chat(db, user, body.message.strip())
    except LLMUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The AI service is not responding right now. Try again in a minute.",
        ) from None
    return ChatResponse(reply=reply)


@router.get("/history", response_model=list[HistoryMessage])
def history(limit: int = 50, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.user_id == user.id, ChatMessage.role.in_(("user", "assistant")), ChatMessage.content != "")
        .order_by(ChatMessage.id.desc())
        .limit(limit)
    ).all()
    return [
        HistoryMessage(role="user" if r.role == "user" else "coach", text=r.content, created_at=r.created_at)
        for r in reversed(rows)
    ]


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    db.execute(delete(ChatMessage).where(ChatMessage.user_id == user.id))
    db.commit()