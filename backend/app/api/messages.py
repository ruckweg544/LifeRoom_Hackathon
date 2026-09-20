from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import get_settings
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
    if message.analysis_status != "pending":
        return _stored_analysis(message)
    skip = ai.is_obvious_noise(message.content)
    content, created_at = message.content, message.created_at
    household_id = current_member.household_id
    # Compare-and-set across workers: commit the claim BEFORE any provider request.
    claimed = db.query(Message).filter(
        Message.id == message_id, Message.analysis_status == "pending",
    ).update({"analysis_status": "skipped" if skip else "processing"}, synchronize_session=False)
    if not claimed:
        db.rollback()
        db.refresh(message)
        return _stored_analysis(message)
    if skip:
        db.commit()
        return MessageAnalysisOut(message_id=message_id, is_task=False)
    try:
        ai.reserve_analysis(household_id)
    except HTTPException:
        db.rollback()  # Local throttling happened before a provider attempt; allow manual retry.
        raise
    members = db.query(Member).filter(Member.household_id == household_id).all()
    names = [(member.id, member.display_name.strip().casefold()) for member in members]
    db.commit()
    try:
        result = await ai.detect_task(content, created_at)
        suggestion = None
        if result.is_task:
            matches = [member_id for member_id, name in names
                       if result.assignee and name == result.assignee.strip().casefold()]
            suggestion = ChoreSuggestion(title=result.task_name.strip(),
                                         assigned_to_id=matches[0] if len(matches) == 1 else None,
                                         due_date=result.due_date,
                                         due_at=datetime.combine(result.due_date, result.due_time,
                                             ZoneInfo(get_settings().ai_timezone)) if result.due_time else None)
        output = MessageAnalysisOut(message_id=message_id, is_task=result.is_task, suggestion=suggestion)
    except HTTPException as exc:
        detail = dict(exc.detail) if isinstance(exc.detail, dict) else {"code": "AI_UNAVAILABLE"}
        detail["retryable"] = False
        message.analysis_status = "failed"
        message.analysis_data = {"status_code": exc.status_code, "detail": detail}
        db.commit()
        raise HTTPException(exc.status_code, detail=detail) from None
    message.analysis_status = "completed"
    message.analysis_data = output.model_dump(mode="json")
    db.commit()
    return output


def _stored_analysis(message: Message) -> MessageAnalysisOut:
    if message.analysis_status == "completed":
        return MessageAnalysisOut.model_validate(message.analysis_data)
    if message.analysis_status == "failed":
        raise HTTPException(message.analysis_data["status_code"], detail=message.analysis_data["detail"])
    if message.analysis_status == "processing":
        # A crashed worker may leave this state. Never reclaim it: the provider may have received the request.
        raise HTTPException(409, detail={"code": "AI_ALREADY_ATTEMPTED", "retryable": False})
    return MessageAnalysisOut(message_id=message.id, is_task=False)
