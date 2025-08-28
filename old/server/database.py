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
    "sqlite:///./data/alice_auth.db"
)

# Create SQLAlchemy engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration with enhanced connection pooling
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
            "isolation_level": None  # Enables autocommit mode for better concurrency
        },
        poolclass=StaticPool,
        pool_pre_ping=True,  # Test connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
        echo=os.getenv("SQL_DEBUG", "0") == "1"
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=memory")
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
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
        from auth_models import User, UserSession, APIKey, AuditLog
        
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
        # Create default admin user if none exists
        create_default_admin_user()
        
    except Exception as e:
        logger.error(f"Failed to create database: {e}")
        raise

def create_default_admin_user():
    """Create default admin user if no users exist"""
    try:
        from auth_models import User, UserRole
        
        db = SessionLocal()
        
        # Check if any users exist
        user_count = db.query(User).count()
        if user_count == 0:
            # Create default admin user
            admin_user = User(
                username="admin",
                email="admin@alice-ai.local",
                full_name="Administrator",
                role=UserRole.ADMIN.value,
                is_active=True,
                is_verified=True,
                language="sv"
            )
            
            # Set default password (should be changed immediately)
            admin_user.set_password("admin123!")
            
            db.add(admin_user)
            db.commit()
            
            logger.warning(
                "Created default admin user: admin / admin123! "
                "CHANGE PASSWORD IMMEDIATELY in production!"
            )
        
        db.close()
        
    except Exception as e:
        logger.error(f"Failed to create default admin user: {e}")

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
        from auth_models import User, UserSession, APIKey, AuditLog
        
        db = SessionLocal()
        
        stats = {
            "total_users": db.query(User).count(),
            "active_users": db.query(User).filter(User.is_active == True).count(),
            "verified_users": db.query(User).filter(User.is_verified == True).count(),
            "active_sessions": db.query(UserSession).filter(
                UserSession.status == "active"
            ).count(),
            "total_api_keys": db.query(APIKey).count(),
            "active_api_keys": db.query(APIKey).filter(APIKey.is_active == True).count(),
            "total_audit_events": db.query(AuditLog).count()
        }
        
        db.close()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

# Database maintenance functions

def cleanup_expired_sessions():
    """Clean up expired sessions and tokens"""
    try:
        from auth_models import UserSession
        from datetime import datetime
        
        db = SessionLocal()
        
        # Update expired sessions
        expired_count = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow(),
            UserSession.status == "active"
        ).update({"status": "expired"})
        
        db.commit()
        db.close()
        
        if expired_count > 0:
            logger.info(f"Marked {expired_count} sessions as expired")
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {e}")

def cleanup_old_audit_logs(days_to_keep: int = 90):
    """Clean up old audit log entries"""
    try:
        from auth_models import AuditLog
        from datetime import datetime, timedelta
        
        db = SessionLocal()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).delete()
        
        db.commit()
        db.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old audit log entries")
        
    except Exception as e:
        logger.error(f"Failed to cleanup old audit logs: {e}")

def run_database_maintenance():
    """Run regular database maintenance tasks"""
    logger.info("Running database maintenance...")
    
    cleanup_expired_sessions()
    cleanup_old_audit_logs()
    
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