"""
Chat Service - Database integration för chat API
===============================================
Hanterar chat history, conversations och user sessions.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from uuid import uuid4
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

from database import SessionLocal
from chat_models import User, Conversation, Message, ChatSession, ConversationType, MessageRole

logger = logging.getLogger("alice.chat_service")

class ChatService:
    """Service för chat hantering med optimized database persistence"""
    
    def __init__(self):
        self._db = None
        # Thread pool för async database operations
        self.db_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="db-")
        # Write batching för high-volume logging
        self.pending_writes = []
        self.batch_size = 10
        self.last_flush = datetime.now()
    
    @contextmanager
    def _get_db_session(self):
        """Context manager för database sessions med automatic cleanup"""
        db = SessionLocal()
        try:
            yield db
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            db.close()
    
    def _get_db(self):
        """Get database session (legacy method for compatibility)"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def _close_db(self):
        """Close database session (legacy method for compatibility)"""
        if self._db is not None:
            self._db.close()
            self._db = None
    
    async def _async_db_operation(self, operation, *args, **kwargs):
        """Run database operation in thread pool för non-blocking I/O"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.db_executor, operation, *args, **kwargs)
    
    def get_or_create_user(self, username: str = "alice_user", display_name: str = None) -> User:
        """Hämta eller skapa user med optimized database access"""
        with self._get_db_session() as db:
            # Optimized query med index
            user = db.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    username=username,
                    display_name=display_name or username,
                    language="sv",
                    timezone="Europe/Stockholm",
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created new user: {username}")
            
            return user
    
    async def flush_pending_writes(self):
        """Flush pending writes i batch för performance"""
        if not self.pending_writes:
            return
        
        def _batch_write():
            with self._get_db_session() as db:
                for write_op in self.pending_writes:
                    db.add(write_op)
                db.commit()
                return len(self.pending_writes)
        
        count = await self._async_db_operation(_batch_write)
        logger.debug(f"Flushed {count} pending writes")
        self.pending_writes.clear()
        self.last_flush = datetime.now()
    
    def create_conversation(
        self, 
        user_id: int, 
        conversation_type: ConversationType = ConversationType.CHAT,
        title: str = None,
        context: Dict[str, Any] = None
    ) -> Conversation:
        """Skapa ny konversation"""
        db = self._get_db()
        
        conversation = Conversation(
            user_id=user_id,
            title=title,
            conversation_type=conversation_type.value,
            context=context or {},
            is_active=True,
            message_count=0
        )
        
        db.add(conversation)
        db.commit() 
        db.refresh(conversation)
        
        logger.info(f"Created conversation {conversation.id} for user {user_id}")
        return conversation
    
    def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        model_used: str = None,
        response_time_ms: int = None,
        agent_plan_id: str = None,
        agent_action: Dict[str, Any] = None,
        extra_metadata: Dict[str, Any] = None
    ) -> Message:
        """Lägg till meddelande i konversation"""
        db = self._get_db()
        
        message = Message(
            conversation_id=conversation_id,
            role=role.value,
            content=content,
            model_used=model_used,
            response_time_ms=response_time_ms,
            agent_plan_id=agent_plan_id,
            agent_action=agent_action or {},
            extra_metadata=extra_metadata or {}
        )
        
        db.add(message)
        
        # Update conversation
        conversation = db.query(Conversation).get(conversation_id)
        if conversation:
            conversation.message_count += 1
            conversation.last_message_at = datetime.now(timezone.utc)
            
            # Auto-generate title från första user message
            if not conversation.title and role == MessageRole.USER:
                title = content[:50] + "..." if len(content) > 50 else content
                conversation.title = title
        
        db.commit()
        db.refresh(message)
        
        logger.debug(f"Added message {message.id} to conversation {conversation_id}")
        return message
    
    def get_conversation_history(
        self, 
        conversation_id: int, 
        limit: int = 50
    ) -> List[Message]:
        """Hämta conversation history"""
        try:
            db = self._get_db()
            
            messages = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            return list(reversed(messages))  # Oldest first
        finally:
            self._close_db()
    
    def get_recent_conversations(
        self, 
        user_id: int, 
        limit: int = 10
    ) -> List[Conversation]:
        """Hämta recent conversations för user"""
        try:
            db = self._get_db()
            
            conversations = db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_active == True
            ).order_by(Conversation.last_message_at.desc()).limit(limit).all()
            
            return conversations
        finally:
            self._close_db()
    
    def create_chat_session(
        self,
        user_id: int,
        conversation_id: int = None,
        connection_type: str = "http",
        client_info: Dict[str, Any] = None
    ) -> ChatSession:
        """Skapa ny chat session"""
        db = self._get_db()
        
        session = ChatSession(
            user_id=user_id,
            conversation_id=conversation_id,
            connection_type=connection_type,
            client_info=client_info or {},
            is_active=True
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session
    
    def update_session_ping(self, session_token: str):
        """Update session last ping"""
        db = self._get_db()
        
        session = db.query(ChatSession).filter(
            ChatSession.session_token == session_token
        ).first()
        
        if session:
            session.last_ping = datetime.now(timezone.utc)
            db.commit()
    
    def close_session(self, session_token: str):
        """Close chat session"""
        db = self._get_db()
        
        session = db.query(ChatSession).filter(
            ChatSession.session_token == session_token
        ).first()
        
        if session:
            session.is_active = False
            session.disconnected_at = datetime.now(timezone.utc)
            db.commit()
    
    def process_chat_request(
        self,
        user_message: str,
        username: str = "alice_user",
        conversation_id: int = None,
        model_used: str = None,
        response_time_ms: int = None,
        agent_plan_id: str = None,
        agent_action: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process complete chat request with database persistence
        
        Returns:
            Dict med conversation_id, message_id, user och andra metadata
        """
        try:
            # Get or create user
            user = self.get_or_create_user(username)
            
            # Get or create conversation
            if conversation_id:
                db = self._get_db()
                conversation = db.query(Conversation).get(conversation_id)
                if not conversation or conversation.user_id != user.id:
                    conversation = self.create_conversation(user.id)
            else:
                conversation = self.create_conversation(user.id)
            
            # Add user message
            user_message_obj = self.add_message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=user_message
            )
            
            return {
                "success": True,
                "conversation_id": conversation.id,
                "conversation_session_id": conversation.session_id,
                "user_message_id": user_message_obj.id,
                "user_id": user.id,
                "username": user.username,
                "message_count": conversation.message_count,
                "ready_for_response": True
            }
            
        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self._close_db()
    
    def save_assistant_response(
        self,
        conversation_id: int,
        response_content: str,
        model_used: str = None,
        response_time_ms: int = None,
        agent_plan_id: str = None,
        agent_action: Dict[str, Any] = None,
        extra_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Save assistant response to database"""
        try:
            assistant_message = self.add_message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=response_content,
                model_used=model_used,
                response_time_ms=response_time_ms,
                agent_plan_id=agent_plan_id,
                agent_action=agent_action,
                extra_metadata=extra_metadata
            )
            
            return {
                "success": True,
                "message_id": assistant_message.id,
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error saving assistant response: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            self._close_db()

# Global chat service instance
chat_service = ChatService()