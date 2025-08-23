"""
Authentication Models and Database Schema
Comprehensive user management, sessions, API keys, and security audit logging
"""
import secrets
import hashlib
import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.sqlite import JSON
from pydantic import BaseModel, Field, validator, EmailStr
from passlib.context import CryptContext
import logging

logger = logging.getLogger("alice.auth")

Base = declarative_base()

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    GUEST = "guest"

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"

class AuditEventType(str, Enum):
    """Audit event types for security logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    _2FA_ENABLED = "2fa_enabled"
    _2FA_DISABLED = "2fa_disabled"
    _2FA_SUCCESS = "2fa_success"
    _2FA_FAILED = "2fa_failed"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    OAUTH_LOGIN = "oauth_login"
    OAUTH_FAILED = "oauth_failed"
    SESSION_TIMEOUT = "session_timeout"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SECURITY_VIOLATION = "security_violation"

# Database Models

class User(Base):
    """User model with comprehensive security features"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(255))
    role = Column(String(20), default=UserRole.USER)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    last_password_change = Column(DateTime, default=datetime.utcnow)
    
    # Security features
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    password_reset_token = Column(String(128))
    password_reset_expires = Column(DateTime)
    
    # Two-factor authentication
    totp_secret = Column(String(32))  # Base32 encoded TOTP secret
    totp_enabled = Column(Boolean, default=False)
    backup_codes = Column(JSON)  # List of backup codes
    
    # OAuth integration
    google_id = Column(String(255), unique=True)
    github_id = Column(Integer, unique=True)
    oauth_providers = Column(JSON)  # List of connected OAuth providers
    
    # Swedish language preference
    language = Column(String(5), default="sv")
    timezone = Column(String(50), default="Europe/Stockholm")
    
    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return pwd_context.verify(password, self.password_hash)
    
    def set_password(self, password: str):
        """Set new password hash"""
        self.password_hash = pwd_context.hash(password)
        self.last_password_change = datetime.utcnow()
    
    def generate_totp_secret(self) -> str:
        """Generate new TOTP secret for 2FA"""
        secret = pyotp.random_base32()
        self.totp_secret = secret
        return secret
    
    def get_totp_qr_code(self, issuer_name: str = "Alice AI") -> str:
        """Generate QR code for TOTP setup"""
        if not self.totp_secret:
            self.generate_totp_secret()
        
        totp_uri = pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code = base64.b64encode(buffer.getvalue()).decode()
        
        return qr_code
    
    def verify_totp(self, token: str) -> bool:
        """Verify TOTP token"""
        if not self.totp_secret or not self.totp_enabled:
            return False
        
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 window tolerance
    
    def generate_backup_codes(self, count: int = 8) -> List[str]:
        """Generate backup codes for 2FA recovery"""
        codes = [secrets.token_hex(4) for _ in range(count)]
        # Store hashed versions
        self.backup_codes = [hashlib.sha256(code.encode()).hexdigest() for code in codes]
        return codes
    
    def verify_backup_code(self, code: str) -> bool:
        """Verify and consume backup code"""
        if not self.backup_codes:
            return False
        
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash in self.backup_codes:
            # Remove used backup code
            self.backup_codes.remove(code_hash)
            return True
        return False
    
    def is_locked(self) -> bool:
        """Check if account is locked due to failed attempts"""
        if self.account_locked_until:
            if datetime.utcnow() < self.account_locked_until:
                return True
            else:
                # Clear expired lock
                self.account_locked_until = None
                self.failed_login_attempts = 0
        return False
    
    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration"""
        self.account_locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary (excluding sensitive data)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "totp_enabled": self.totp_enabled,
            "language": self.language,
            "timezone": self.timezone,
            "oauth_providers": self.oauth_providers or []
        }

class UserSession(Base):
    """User session model for JWT token management"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(128), unique=True, index=True, nullable=False)
    refresh_token = Column(String(128), unique=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    status = Column(String(20), default=SessionStatus.ACTIVE)
    device_info = Column(JSON)  # Browser, OS, IP, etc.
    
    user = relationship("User", back_populates="sessions")
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid and active"""
        return (self.status == SessionStatus.ACTIVE and 
                not self.is_expired())
    
    def refresh(self, duration_minutes: int = 60):
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self.last_accessed = datetime.utcnow()

class APIKey(Base):
    """API key model for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)  # User-friendly name
    key_hash = Column(String(128), unique=True, index=True, nullable=False)
    key_prefix = Column(String(16), index=True, nullable=False)  # First 8 chars for identification
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Optional expiration
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON)  # Granular permissions
    rate_limit = Column(Integer)  # Requests per hour
    
    user = relationship("User", back_populates="api_keys")
    
    @staticmethod
    def generate_key() -> str:
        """Generate new API key"""
        return f"alice_{secrets.token_urlsafe(32)}"
    
    def set_key(self, key: str):
        """Set API key hash and prefix"""
        self.key_hash = hashlib.sha256(key.encode()).hexdigest()
        self.key_prefix = key[:16]  # Store prefix for identification
    
    def verify_key(self, key: str) -> bool:
        """Verify API key"""
        return hashlib.sha256(key.encode()).hexdigest() == self.key_hash
    
    def is_valid(self) -> bool:
        """Check if API key is valid"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        return True
    
    def record_usage(self):
        """Record API key usage"""
        self.last_used = datetime.utcnow()
        self.usage_count += 1

class AuditLog(Base):
    """Security audit log for authentication events"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Can be null for failed logins
    event_type = Column(String(50), nullable=False, index=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Event details
    success = Column(Boolean, default=True)
    details = Column(JSON)  # Additional event-specific data
    
    # Geographic info (optional)
    country = Column(String(2))
    region = Column(String(100))
    city = Column(String(100))
    
    user = relationship("User", back_populates="audit_logs")
    
    # Index for common queries
    __table_args__ = (
        Index('ix_audit_timestamp_type', 'timestamp', 'event_type'),
        Index('ix_audit_user_timestamp', 'user_id', 'timestamp'),
    )

# Pydantic Models for API

class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = Field(None, max_length=255)
    language: str = Field("sv", pattern=r'^(sv|en)$')
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength (Swedish error messages)"""
        if len(v) < 8:
            raise ValueError("Lösenordet måste vara minst 8 tecken långt")
        if not any(c.isupper() for c in v):
            raise ValueError("Lösenordet måste innehålla minst en stor bokstav")
        if not any(c.islower() for c in v):
            raise ValueError("Lösenordet måste innehålla minst en liten bokstav")
        if not any(c.isdigit() for c in v):
            raise ValueError("Lösenordet måste innehålla minst en siffra")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Lösenordet måste innehålla minst ett specialtecken")
        return v

class UserLogin(BaseModel):
    """User login model"""
    username: str
    password: str
    totp_code: Optional[str] = None
    remember_me: bool = False

class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate new password strength"""
        return UserCreate.validate_password(v)

class TOTPSetup(BaseModel):
    """TOTP setup model"""
    password: str  # Require password confirmation
    
class TOTPVerify(BaseModel):
    """TOTP verification model"""
    token: str = Field(..., min_length=6, max_length=6)

class APIKeyCreate(BaseModel):
    """API key creation model"""
    name: str = Field(..., min_length=1, max_length=100)
    expires_days: Optional[int] = Field(None, gt=0, le=365)
    permissions: Optional[List[str]] = []
    rate_limit: Optional[int] = Field(100, gt=0, le=10000)  # Per hour

class OAuthConnect(BaseModel):
    """OAuth connection model"""
    provider: str = Field(..., pattern=r'^(google|github)$')
    code: str
    state: Optional[str] = None

class SessionInfo(BaseModel):
    """Session information model"""
    id: int
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    device_info: Optional[Dict[str, Any]] = None
    status: str

class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    totp_enabled: bool
    language: str
    timezone: str
    oauth_providers: List[str] = []

# Swedish error messages for validation
SWEDISH_ERROR_MESSAGES = {
    "invalid_credentials": "Ogiltigt användarnamn eller lösenord",
    "account_locked": "Kontot är låst på grund av för många misslyckade inloggningsförsök",
    "account_inactive": "Kontot är inaktiverat",
    "account_unverified": "Kontot är inte verifierat",
    "2fa_required": "Tvåfaktorautentisering krävs",
    "invalid_2fa": "Ogiltig tvåfaktorskod",
    "session_expired": "Sessionen har löpt ut",
    "invalid_token": "Ogiltig token",
    "permission_denied": "Åtkomst nekad",
    "user_exists": "Användaren finns redan",
    "weak_password": "Lösenordet är för svagt",
    "rate_limit_exceeded": "För många förfrågningar. Försök igen senare",
    "oauth_error": "OAuth-autentisering misslyckades",
    "api_key_invalid": "Ogiltig API-nyckel",
    "backup_code_invalid": "Ogiltig backup-kod"
}