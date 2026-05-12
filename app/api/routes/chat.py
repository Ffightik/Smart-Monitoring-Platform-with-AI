from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.services.gpt_service import chat, reset_session, get_history

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    # Optionally pass fresh prediction + stats on first message
    stats: Optional[dict] = None
    prediction: Optional[dict] = None
    inject_context: bool = False


class ChatResponse(BaseModel):
    user_id: str
    reply: str


@router.post("", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        reply = chat(
            user_id=req.user_id,
            user_message=req.message,
            stats=req.stats,
            prediction=req.prediction,
            inject_context=req.inject_context,
        )
        return ChatResponse(user_id=req.user_id, reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/history")
async def history_endpoint(user_id: str):
    return {"user_id": user_id, "history": get_history(user_id)}


@router.delete("/{user_id}/session")
async def reset_endpoint(user_id: str):
    reset_session(user_id)
    return {"user_id": user_id, "status": "session cleared"}
