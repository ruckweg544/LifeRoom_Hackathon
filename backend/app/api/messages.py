from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_member
from app.database.session import get_db
from app.models.member import Member
from app.models.message import Message
from app.schemas.message import MessageOut, CreateMessageRequest, MessageAnalysisOut, ChoreSuggestion
from app.services import ai
from app.websocket.connection_manager import manager

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.post("", response_model=MessageOut, status_code=201)
async def create_message(payload: CreateMessageRequest,
                         current_member: Member = Depends(get_current_member),
                         db: Session = Depends(get_db)):
    message = Message(household_id=current_member.household_id,
                      member_id=current_member.id, sender_name=current_member.display_name,
                      content=payload.content)
    db.add(message)
    db.commit()
    db.refresh(message)
    await manager.broadcast(current_member.household_id, {"type": "message.created"})
    return MessageOut.model_validate(message)


@router.get("", response_model=list[MessageOut])
def list_messages(
    limit: int = 50,
    current_member: Member = Depends(get_current_member),
    db: Session = Depends(get_db),
):
    """Chat history for the caller's household only (real-time delivery happens over WebSocket)."""
    limit = max(1, min(limit, 200))
    messages = (
        db.query(Message)
        .filter(Message.household_id == current_member.household_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return [MessageOut.model_validate(m) for m in reversed(messages)]


@router.post("/{message_id}/analyze", response_model=MessageAnalysisOut)
async def analyze_message(message_id: str,
                          current_member: Member = Depends(get_current_member),
                          db: Session = Depends(get_db)):
    message = db.query(Message).filter(
        Message.id == message_id, Message.household_id == current_member.household_id,
    ).first()
    if message is None:
        raise HTTPException(404, "Message not found")
    members = db.query(Member).filter(Member.household_id == current_member.household_id).all()
    names = [(member.id, member.display_name.strip().casefold()) for member in members]
    content, created_at = message.content, message.created_at
    ai.reserve_analysis(current_member.household_id)
    db.rollback()  # Release the read transaction before waiting on the provider.
    result = await ai.detect_task(content, created_at)
    suggestion = None
    if result.is_task:
        matches = [member_id for member_id, name in names
                   if result.assignee and name == result.assignee.strip().casefold()]
        suggestion = ChoreSuggestion(title=result.task_name.strip(),
                                     assigned_to_id=matches[0] if len(matches) == 1 else None,
                                     due_date=result.due_date)
    return MessageAnalysisOut(message_id=message_id, is_task=result.is_task, suggestion=suggestion)
