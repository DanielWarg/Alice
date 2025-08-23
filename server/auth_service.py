"""
Alice Authentication Service
Secure JWT-based authentication with comprehensive security features
"""
import os
import secrets
import hashlib
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import logging

from auth_models import (
    User, UserSession, APIKey, AuditLog,
    UserCreate, UserLogin, PasswordChange, TOTPSetup, TOTPVerify,
    APIKeyCreate, OAuthConnect, SessionInfo, UserResponse,
    UserRole, SessionStatus, AuditEventType,
    SWEDISH_ERROR_MESSAGES, pwd_context
)

logger = logging.getLogger("alice.auth")

class AuthService:
    """Comprehensive authentication service"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", self._generate_jwt_secret())
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.refresh_token_expire_days = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        
        # Rate limiting settings
        self.max_login_attempts = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
        self.lockout_duration_minutes = int(os.getenv("LOCKOUT_DURATION_MINUTES", "30"))
        
        # OAuth settings
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.github_client_id = os.getenv("GITHUB_CLIENT_ID")
        self.github_client_secret = os.getenv("GITHUB_CLIENT_SECRET")
        
        if not self.jwt_secret or len(self.jwt_secret) < 32:
            logger.warning("JWT_SECRET_KEY is not set or too short. Generated temporary key.")
    
    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret key"""
        return secrets.token_urlsafe(64)
    
    def _log_audit_event(
        self, 
        event_type: AuditEventType, 
        user_id: Optional[int] = None,
        request: Optional[Request] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security audit event"""
        try:
            audit_log = AuditLog(
                user_id=user_id,
                event_type=event_type.value,
                success=success,
                details=details or {}
            )
            
            if request:
                audit_log.ip_address = request.client.host if request.client else "unknown"
                audit_log.user_agent = request.headers.get("user-agent", "")[:1000]  # Truncate
            
            self.db.add(audit_log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def create_user(self, user_data: UserCreate, request: Optional[Request] = None) -> UserResponse:
        """Create new user account"""
        try:
            # Check if user already exists
            existing_user = self.db.query(User).filter(
                (User.username == user_data.username) | (User.email == user_data.email)
            ).first()
            
            if existing_user:
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILED,
                    request=request,
                    success=False,
                    details={"reason": "user_exists", "username": user_data.username}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=SWEDISH_ERROR_MESSAGES["user_exists"]
                )
            
            # Create new user
            user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                language=user_data.language,
                timezone="Europe/Stockholm"
            )
            user.set_password(user_data.password)
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            self._log_audit_event(
                AuditEventType.LOGIN_SUCCESS,
                user_id=user.id,
                request=request,
                details={"action": "user_created"}
            )
            
            return UserResponse(**user.to_dict())
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ett fel uppstod vid skapande av användarkonto"
            )
    
    def authenticate_user(
        self, 
        login_data: UserLogin, 
        request: Optional[Request] = None
    ) -> Tuple[User, str, str]:
        """Authenticate user and return tokens"""
        user = self.db.query(User).filter(
            (User.username == login_data.username) | (User.email == login_data.username)
        ).first()
        
        # Always check password even for non-existent users (timing attack prevention)
        if user:
            password_valid = user.verify_password(login_data.password)
        else:
            # Dummy hash check to prevent timing attacks
            pwd_context.verify("dummy_password", "$2b$12$dummy.hash.to.prevent.timing.attacks")
            password_valid = False
        
        if not user or not password_valid:
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= self.max_login_attempts:
                    user.lock_account(self.lockout_duration_minutes)
                    self.db.commit()
                    
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILED,
                    user_id=user.id,
                    request=request,
                    success=False,
                    details={"reason": "invalid_password", "attempt": user.failed_login_attempts}
                )
            else:
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILED,
                    request=request,
                    success=False,
                    details={"reason": "user_not_found", "username": login_data.username}
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=SWEDISH_ERROR_MESSAGES["invalid_credentials"]
            )
        
        # Check if account is locked
        if user.is_locked():
            self._log_audit_event(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                request=request,
                success=False,
                details={"reason": "account_locked"}
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=SWEDISH_ERROR_MESSAGES["account_locked"]
            )
        
        # Check if account is active
        if not user.is_active:
            self._log_audit_event(
                AuditEventType.LOGIN_FAILED,
                user_id=user.id,
                request=request,
                success=False,
                details={"reason": "account_inactive"}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=SWEDISH_ERROR_MESSAGES["account_inactive"]
            )
        
        # Check 2FA if enabled
        if user.totp_enabled:
            if not login_data.totp_code:
                raise HTTPException(
                    status_code=status.HTTP_200_OK,  # Special status for 2FA required
                    detail=SWEDISH_ERROR_MESSAGES["2fa_required"],
                    headers={"X-Require-2FA": "true"}
                )
            
            if not user.verify_totp(login_data.totp_code):
                user.failed_login_attempts += 1
                self.db.commit()
                
                self._log_audit_event(
                    AuditEventType.LOGIN_FAILED,
                    user_id=user.id,
                    request=request,
                    success=False,
                    details={"reason": "invalid_2fa"}
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=SWEDISH_ERROR_MESSAGES["invalid_2fa"]
                )
            
            self._log_audit_event(
                AuditEventType._2FA_SUCCESS,
                user_id=user.id,
                request=request,
                details={"method": "totp"}
            )
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.utcnow()
        
        # Create session and tokens
        access_token, refresh_token = self._create_tokens(user, login_data.remember_me)
        
        self._log_audit_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.id,
            request=request,
            details={"method": "password", "2fa_used": user.totp_enabled}
        )
        
        self.db.commit()
        return user, access_token, refresh_token
    
    def _create_tokens(self, user: User, remember_me: bool = False) -> Tuple[str, str]:
        """Create JWT access and refresh tokens"""
        # Token expiration
        access_expire = timedelta(minutes=self.access_token_expire_minutes)
        refresh_expire = timedelta(
            days=self.refresh_token_expire_days * (4 if remember_me else 1)
        )
        
        # Access token payload
        access_payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "exp": datetime.utcnow() + access_expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # Refresh token payload  
        refresh_payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() + refresh_expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(16)  # JWT ID for invalidation
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Store session
        session = UserSession(
            user_id=user.id,
            session_token=hashlib.sha256(access_token.encode()).hexdigest()[:128],
            refresh_token=hashlib.sha256(refresh_token.encode()).hexdigest()[:128],
            expires_at=datetime.utcnow() + access_expire,
            device_info={}  # Can be populated from request headers
        )
        
        self.db.add(session)
        return access_token, refresh_token
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if it's an access token
            if payload.get("type") != "access":
                return None
            
            # Verify session exists and is active
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:128]
            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.session_token == token_hash,
                    UserSession.status == SessionStatus.ACTIVE
                )
            ).first()
            
            if not session or not session.is_valid():
                return None
            
            # Update last accessed
            session.last_accessed = datetime.utcnow()
            self.db.commit()
            
            return payload
            
        except JWTError as e:
            logger.debug(f"JWT error: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            if payload.get("type") != "refresh":
                return None
            
            user_id = int(payload["sub"])
            user = self.db.query(User).filter(User.id == user_id).first()
            
            if not user or not user.is_active:
                return None
            
            # Verify refresh token exists in database
            token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()[:128]
            session = self.db.query(UserSession).filter(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.refresh_token == token_hash,
                    UserSession.status == SessionStatus.ACTIVE
                )
            ).first()
            
            if not session:
                return None
            
            # Create new access token
            access_token, _ = self._create_tokens(user, False)
            
            # Update session
            session.session_token = hashlib.sha256(access_token.encode()).hexdigest()[:128]
            session.refresh(self.access_token_expire_minutes)
            self.db.commit()
            
            return access_token
            
        except JWTError:
            return None
    
    def logout_user(
        self, 
        user_id: int, 
        token: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Logout user and invalidate session"""
        try:
            if token:
                token_hash = hashlib.sha256(token.encode()).hexdigest()[:128]
                session = self.db.query(UserSession).filter(
                    and_(
                        UserSession.user_id == user_id,
                        UserSession.session_token == token_hash
                    )
                ).first()
                
                if session:
                    session.status = SessionStatus.REVOKED
            else:
                # Logout all sessions
                self.db.query(UserSession).filter(
                    UserSession.user_id == user_id
                ).update({"status": SessionStatus.REVOKED})
            
            self._log_audit_event(
                AuditEventType.LOGOUT,
                user_id=user_id,
                request=request
            )
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            self.db.rollback()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def setup_2fa(
        self, 
        user_id: int, 
        setup_data: TOTPSetup,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Setup TOTP 2FA for user"""
        user = self.get_user_by_id(user_id)
        if not user or not user.verify_password(setup_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=SWEDISH_ERROR_MESSAGES["invalid_credentials"]
            )
        
        # Generate TOTP secret and QR code
        secret = user.generate_totp_secret()
        qr_code = user.get_totp_qr_code()
        backup_codes = user.generate_backup_codes()
        
        self.db.commit()
        
        self._log_audit_event(
            AuditEventType._2FA_ENABLED,
            user_id=user_id,
            request=request,
            details={"method": "totp"}
        )
        
        return {
            "secret": secret,
            "qr_code": qr_code,
            "backup_codes": backup_codes
        }
    
    def verify_2fa_setup(
        self, 
        user_id: int, 
        verify_data: TOTPVerify,
        request: Optional[Request] = None
    ) -> bool:
        """Verify and enable TOTP 2FA"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Användaren hittades inte"
            )
        
        if user.verify_totp(verify_data.token):
            user.totp_enabled = True
            self.db.commit()
            
            self._log_audit_event(
                AuditEventType._2FA_SUCCESS,
                user_id=user_id,
                request=request,
                details={"action": "2fa_enabled"}
            )
            
            return True
        else:
            self._log_audit_event(
                AuditEventType._2FA_FAILED,
                user_id=user_id,
                request=request,
                success=False,
                details={"reason": "invalid_setup_token"}
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=SWEDISH_ERROR_MESSAGES["invalid_2fa"]
            )
    
    def disable_2fa(
        self, 
        user_id: int, 
        password: str,
        request: Optional[Request] = None
    ):
        """Disable TOTP 2FA for user"""
        user = self.get_user_by_id(user_id)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=SWEDISH_ERROR_MESSAGES["invalid_credentials"]
            )
        
        user.totp_enabled = False
        user.totp_secret = None
        user.backup_codes = None
        
        self.db.commit()
        
        self._log_audit_event(
            AuditEventType._2FA_DISABLED,
            user_id=user_id,
            request=request
        )
    
    def create_api_key(
        self, 
        user_id: int, 
        key_data: APIKeyCreate,
        request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Create new API key for user"""
        user = self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Användaren hittades inte"
            )
        
        # Generate API key
        api_key_value = APIKey.generate_key()
        
        api_key = APIKey(
            user_id=user_id,
            name=key_data.name,
            permissions=key_data.permissions or [],
            rate_limit=key_data.rate_limit
        )
        
        if key_data.expires_days:
            api_key.expires_at = datetime.utcnow() + timedelta(days=key_data.expires_days)
        
        api_key.set_key(api_key_value)
        
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        
        self._log_audit_event(
            AuditEventType.API_KEY_CREATED,
            user_id=user_id,
            request=request,
            details={"key_name": key_data.name, "key_id": api_key.id}
        )
        
        return {
            "id": api_key.id,
            "key": api_key_value,  # Only returned once
            "name": api_key.name,
            "created_at": api_key.created_at,
            "expires_at": api_key.expires_at
        }
    
    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key and return associated user"""
        if not api_key.startswith("alice_"):
            return None
        
        # Find by prefix first for performance
        key_prefix = api_key[:16]
        db_key = self.db.query(APIKey).filter(
            APIKey.key_prefix == key_prefix
        ).first()
        
        if not db_key or not db_key.is_valid() or not db_key.verify_key(api_key):
            return None
        
        # Record usage
        db_key.record_usage()
        self.db.commit()
        
        return db_key.user
    
    def revoke_api_key(
        self, 
        user_id: int, 
        key_id: int,
        request: Optional[Request] = None
    ):
        """Revoke API key"""
        api_key = self.db.query(APIKey).filter(
            and_(APIKey.id == key_id, APIKey.user_id == user_id)
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API-nyckeln hittades inte"
            )
        
        api_key.is_active = False
        self.db.commit()
        
        self._log_audit_event(
            AuditEventType.API_KEY_REVOKED,
            user_id=user_id,
            request=request,
            details={"key_name": api_key.name, "key_id": key_id}
        )
    
    def get_user_sessions(self, user_id: int) -> List[SessionInfo]:
        """Get active sessions for user"""
        sessions = self.db.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.status == SessionStatus.ACTIVE
            )
        ).order_by(desc(UserSession.last_accessed)).all()
        
        return [
            SessionInfo(
                id=session.id,
                created_at=session.created_at,
                expires_at=session.expires_at,
                last_accessed=session.last_accessed,
                device_info=session.device_info,
                status=session.status
            )
            for session in sessions
        ]
    
    def get_user_api_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """Get API keys for user (without key values)"""
        keys = self.db.query(APIKey).filter(
            APIKey.user_id == user_id
        ).order_by(desc(APIKey.created_at)).all()
        
        return [
            {
                "id": key.id,
                "name": key.name,
                "created_at": key.created_at,
                "expires_at": key.expires_at,
                "last_used": key.last_used,
                "usage_count": key.usage_count,
                "is_active": key.is_active,
                "rate_limit": key.rate_limit
            }
            for key in keys
        ]
    
    def change_password(
        self, 
        user_id: int, 
        password_data: PasswordChange,
        request: Optional[Request] = None
    ):
        """Change user password"""
        user = self.get_user_by_id(user_id)
        if not user or not user.verify_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=SWEDISH_ERROR_MESSAGES["invalid_credentials"]
            )
        
        user.set_password(password_data.new_password)
        
        # Revoke all existing sessions except current one
        self.db.query(UserSession).filter(
            UserSession.user_id == user_id
        ).update({"status": SessionStatus.REVOKED})
        
        self.db.commit()
        
        self._log_audit_event(
            AuditEventType.PASSWORD_CHANGE,
            user_id=user_id,
            request=request
        )

# FastAPI Security Dependencies
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials, db: Session, auth_service: AuthService) -> User:
    """FastAPI dependency to get current authenticated user"""
    token = credentials.credentials
    payload = auth_service.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=SWEDISH_ERROR_MESSAGES["invalid_token"],
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=SWEDISH_ERROR_MESSAGES["invalid_token"]
        )
    
    return user

def require_role(required_role: UserRole):
    """Decorator to require specific user role"""
    def role_checker(user: User) -> User:
        if user.role != required_role.value and user.role != UserRole.ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=SWEDISH_ERROR_MESSAGES["permission_denied"]
            )
        return user
    return role_checker