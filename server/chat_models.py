"""
Chat Models för Alice Database
=============================
SQLAlchemy models för chat history, user sessions och system data.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
import json
import uuid

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator, VARCHAR

from database import Base

class JSONType(TypeDecorator):
    """Custom type för JSON storage i SQLite"""
    impl = VARCHAR
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

class ConversationType(str, Enum):
    """Typ av konversation"""
    CHAT = "chat"
    AGENT = "agent" 
    VOICE = "voice"
    SYSTEM = "system"

class MessageRole(str, Enum):
    """Roll för meddelanden"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"

class User(Base):
    """User model för chat sessioner"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    language = Column(String(10), default="sv")
    timezone = Column(String(50), default="Europe/Stockholm") 
    preferences = Column(JSONType, default=dict)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    is_active = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class Conversation(Base):
    """Konversationer/Chat sessioner"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String(200), nullable=True)  # Auto-generated från första meddelandet
    conversation_type = Column(String(20), default=ConversationType.CHAT.value)
    
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_message_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)
    
    # Metadata för konversationen
    context = Column(JSONType, default=dict)  # Agent context, voice settings etc
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id='{self.session_id}', user_id={self.user_id})>"

class Message(Base):
    """Meddelanden i konversationer"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    
    role = Column(String(20), nullable=False)  # user, assistant, system, agent
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Metadata för meddelandet
    model_used = Column(String(50), nullable=True)  # gpt-oss:20b, gpt-oss:7b etc
    response_time_ms = Column(Integer, nullable=True)
    token_count = Column(Integer, nullable=True)
    
    # Agent-specifika fält
    agent_plan_id = Column(String(36), nullable=True)
    agent_action = Column(JSONType, default=dict)
    
    # Voice-specifika fält
    audio_file_path = Column(String(500), nullable=True)
    transcription_confidence = Column(Float, nullable=True)
    
    # System metadata
    extra_metadata = Column(JSONType, default=dict)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role='{self.role}', content='{content_preview}')>"

class AgentExecution(Base):
    """Agent execution historia"""
    __tablename__ = "agent_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    
    plan_id = Column(String(36), nullable=False)
    goal = Column(Text, nullable=False)
    
    status = Column(String(20), nullable=False)  # pending, in_progress, completed, failed, cancelled
    
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    
    total_actions = Column(Integer, default=0)
    completed_actions = Column(Integer, default=0)
    failed_actions = Column(Integer, default=0)
    
    execution_plan = Column(JSONType, default=dict)  # Full execution plan & results
    
    def __repr__(self):
        return f"<AgentExecution(id={self.id}, plan_id='{self.plan_id}', status='{self.status}')>"

class SystemMetric(Base):
    """System metrics för analys"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Grouping fields
    source = Column(String(50), nullable=False)  # guardian, llm, agent, etc
    category = Column(String(50), nullable=False)  # performance, usage, error, etc
    
    # Extra metadata
    labels = Column(JSONType, default=dict)  # För grouping och filtering
    
    def __repr__(self):
        return f"<SystemMetric(name='{self.metric_name}', value={self.metric_value}, source='{self.source}')>"

class ChatSession(Base):
    """Active chat sessions för WebSocket tracking"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True) 
    session_token = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    
    connection_type = Column(String(20), default="websocket")  # websocket, http, voice
    client_info = Column(JSONType, default=dict)  # Browser, device info etc
    
    connected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_ping = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    disconnected_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"