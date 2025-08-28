"""
Database Configuration for Alice Authentication System
SQLite database setup with SQLAlchemy ORM
"""
import os
import logging
from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger("alice.database")

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./data/alice.db"
)

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration with optimized connection pooling for production
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
            "isolation_level": None  # Enables autocommit mode for better concurrency
        },
        poolclass=StaticPool,
        pool_pre_ping=True,  # Test connections before use
        pool_recycle=1800,   # Recycle connections after 30min (var 1h)
        echo=os.getenv("SQL_DEBUG", "0") == "1"
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Production optimized SQLite PRAGMA settings
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging för concurrency
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balanced durability/performance
        cursor.execute("PRAGMA temp_store=memory")  # Use memory för temp storage
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB memory mapping
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache (negative = KB)
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s busy timeout
        cursor.execute("PRAGMA wal_autocheckpoint=1000")  # WAL checkpoint every 1000 pages
        cursor.close()
        
else:
    # PostgreSQL/MySQL configuration with enhanced connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "10")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        echo=os.getenv("SQL_DEBUG", "0") == "1"
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions
    Creates a new session for each request and closes it when done
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_database():
    """Create database tables"""
    try:
        # Import all models to ensure they're registered with Base
        from chat_models import User, Conversation, Message, AgentExecution, SystemMetric, ChatSession
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
        # Create default user if none exists
        create_default_user()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

def create_default_user():
    """Create default user if no users exist"""
    try:
        from chat_models import User
        
        db = SessionLocal()
        
        # Check if any users exist
        user_count = db.query(User).count()
        if user_count == 0:
            # Create default user
            default_user = User(
                username="alice_user",
                display_name="Alice User",
                language="sv",
                timezone="Europe/Stockholm",
                is_active=True
            )
            
            db.add(default_user)
            db.commit()
            
            logger.info("Created default user: alice_user")
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to create default user: {e}")

def init_database():
    """Initialize database (called at startup)"""
    try:
        create_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def check_database_health() -> bool:
    """Check database connection and health"""
    try:
        db = SessionLocal()
        
        # Simple health check query
        if DATABASE_URL.startswith("sqlite"):
            db.execute(text("SELECT 1"))
        else:
            db.execute(text("SELECT version()"))
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def get_database_stats() -> dict:
    """Get database statistics"""
    try:
        from chat_models import User, Conversation, Message, AgentExecution, ChatSession
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        # Calculate stats for last 24 hours
        yesterday = datetime.now() - timedelta(days=1)
        
        stats = {
            "total_users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "total_conversations": db.query(Conversation).count(),
            "active_conversations": db.query(Conversation).filter(Conversation.is_active == True).count(),
            "conversations_24h": db.query(Conversation).filter(Conversation.started_at > yesterday).count(),
            "total_messages": db.query(Message).count(),
            "messages_24h": db.query(Message).filter(Message.created_at > yesterday).count(),
            "agent_executions": db.query(AgentExecution).count(),
            "active_chat_sessions": db.query(ChatSession).filter(ChatSession.is_active == True).count()
        }
        
        db.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

# Database maintenance functions

def cleanup_expired_sessions():
    """Clean up expired chat sessions"""
    try:
        from chat_models import ChatSession
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        # Sessions inactive for more than 1 hour are expired
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        # Update expired sessions
        expired_count = db.query(ChatSession).filter(
            ChatSession.last_ping < cutoff_time,
            ChatSession.is_active == True
        ).update({
            "is_active": False,
            "disconnected_at": datetime.now()
        })
        
        db.commit()
        db.close()
        
        if expired_count > 0:
            logger.info(f"Marked {expired_count} chat sessions as expired")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")

def cleanup_old_messages(days_to_keep: int = 90):
    """Clean up old messages and conversations"""
    try:
        from chat_models import Message, Conversation
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Delete old messages
        deleted_messages = db.query(Message).filter(
            Message.created_at < cutoff_date
        ).delete()
        
        # Delete conversations with no messages
        deleted_conversations = db.query(Conversation).filter(
            ~Conversation.messages.any()
        ).delete()
        
        db.commit()
        db.close()
        
        if deleted_messages > 0 or deleted_conversations > 0:
            logger.info(f"Cleaned up {deleted_messages} old messages and {deleted_conversations} empty conversations")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old messages: {e}")

def run_database_maintenance():
    """Run regular database maintenance tasks"""
    logger.info("Running database maintenance...")
    
    cleanup_expired_sessions()
    cleanup_old_messages()
    
    # Vacuum SQLite database if using SQLite
    if DATABASE_URL.startswith("sqlite"):
        try:
            db = SessionLocal()
            db.execute(text("VACUUM"))
            db.close()
            logger.info("SQLite database vacuumed")
        except Exception as e:
            logger.error(f"Failed to vacuum database: {e}")
    
    logger.info("Database maintenance completed")

# Add to deps.py integration
def add_db_session_to_deps():
    """Add database session to deps.py for FastAPI dependency injection"""
    import sys
    import importlib
    
    # Add get_db_session to deps module
    deps_module = sys.modules.get("deps")
    if deps_module:
        setattr(deps_module, "get_db_session", get_db_session)
    
    logger.info("Added database session to deps module")