"""
Database API Router - Endpoints för database queries och management
================================================================
Ger HTTP access till conversation history, user data och database stats.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db_session, get_database_stats, check_database_health
from chat_service import chat_service
from chat_models import User, Conversation, Message
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/db", tags=["database"])

# Pydantic models för API responses
class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    language: str = "sv"
    timezone: str = "Europe/Stockholm"
    is_active: bool = True
    created_at: datetime
    last_active: datetime

class ConversationResponse(BaseModel):
    id: int
    session_id: str
    title: Optional[str] = None
    conversation_type: str = "chat"
    started_at: datetime
    last_message_at: datetime
    is_active: bool = True
    message_count: int = 0
    
class MessageResponse(BaseModel):
    id: int
    message_id: str
    role: str
    content: str
    created_at: datetime
    model_used: Optional[str] = None
    response_time_ms: Optional[int] = None

class DatabaseStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_conversations: int
    active_conversations: int
    conversations_24h: int
    total_messages: int
    messages_24h: int
    agent_executions: int
    active_chat_sessions: int

@router.get("/health")
async def database_health():
    """Check database health and connectivity"""
    is_healthy = check_database_health()
    
    if is_healthy:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "operational"
        }
    else:
        raise HTTPException(status_code=503, detail="Database unavailable")

@router.get("/stats", response_model=DatabaseStatsResponse)
async def database_stats():
    """Get database statistics"""
    stats = get_database_stats()
    
    if not stats:
        raise HTTPException(status_code=503, detail="Unable to retrieve database stats")
    
    return DatabaseStatsResponse(**stats)

@router.get("/users/{username}", response_model=UserResponse)
async def get_user(username: str, db: Session = Depends(get_db_session)):
    """Get user by username"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        language=user.language,
        timezone=user.timezone,
        is_active=user.is_active,
        created_at=user.created_at,
        last_active=user.last_active
    )

@router.get("/users/{username}/conversations", response_model=List[ConversationResponse])
async def get_user_conversations(
    username: str, 
    limit: int = 20,
    db: Session = Depends(get_db_session)
):
    """Get recent conversations for user"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    conversations = chat_service.get_recent_conversations(user.id, limit)
    
    return [
        ConversationResponse(
            id=conv.id,
            session_id=conv.session_id,
            title=conv.title,
            conversation_type=conv.conversation_type,
            started_at=conv.started_at,
            last_message_at=conv.last_message_at,
            is_active=conv.is_active,
            message_count=conv.message_count
        )
        for conv in conversations
    ]

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """Get messages for a conversation"""
    # Verify conversation exists
    conversation = db.query(Conversation).get(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = chat_service.get_conversation_history(conversation_id, limit)
    
    return [
        MessageResponse(
            id=msg.id,
            message_id=msg.message_id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
            model_used=msg.model_used,
            response_time_ms=int(msg.response_time_ms) if msg.response_time_ms else None
        )
        for msg in messages
    ]

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: int, db: Session = Depends(get_db_session)):
    """Get conversation details"""
    conversation = db.query(Conversation).get(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationResponse(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        conversation_type=conversation.conversation_type,
        started_at=conversation.started_at,
        last_message_at=conversation.last_message_at,
        is_active=conversation.is_active,
        message_count=conversation.message_count
    )

@router.post("/maintenance/cleanup")
async def run_maintenance():
    """Run database maintenance tasks"""
    try:
        from database import run_database_maintenance
        run_database_maintenance()
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "message": "Database maintenance completed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Maintenance failed: {str(e)}")

@router.get("/recent-activity")
async def recent_activity(hours: int = 24, db: Session = Depends(get_db_session)):
    """Get recent system activity"""
    since = datetime.now() - timedelta(hours=hours)
    
    recent_conversations = db.query(Conversation).filter(
        Conversation.started_at > since
    ).count()
    
    recent_messages = db.query(Message).filter(
        Message.created_at > since
    ).count()
    
    return {
        "period_hours": hours,
        "since": since.isoformat(),
        "conversations": recent_conversations,
        "messages": recent_messages,
        "activity_level": "high" if recent_messages > 50 else "normal" if recent_messages > 10 else "low"
    }