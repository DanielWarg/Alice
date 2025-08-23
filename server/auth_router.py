"""
Authentication Router for Alice AI Assistant
Comprehensive authentication endpoints with security features
"""
import os
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from auth_models import (
    User, UserCreate, UserLogin, PasswordChange, TOTPSetup, TOTPVerify,
    APIKeyCreate, OAuthConnect, SessionInfo, UserResponse,
    SWEDISH_ERROR_MESSAGES
)
from auth_service import AuthService, get_current_user, require_role, UserRole
from oauth_service import OAuthService
from auth_rate_limiter import check_request_rate_limit, SWEDISH_RATE_LIMIT_MESSAGES
from deps import get_db_session

logger = logging.getLogger("alice.auth_router")

# Security scheme
security = HTTPBearer(auto_error=False)

def get_auth_service(db: Session = Depends(get_db_session)) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db)

def get_oauth_service(
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
) -> OAuthService:
    """Get OAuth service instance"""
    return OAuthService(db, auth_service)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register new user account"""
    # Check rate limit
    allowed, retry_after, stats = check_request_rate_limit(
        request, "auth", db, auth_service
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=SWEDISH_RATE_LIMIT_MESSAGES["rate_limit_exceeded"],
            headers={"Retry-After": str(retry_after)} if retry_after else {}
        )
    
    try:
        user = auth_service.create_user(user_data, request)
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ett fel uppstod vid registreringen"
        )

@router.post("/login")
async def login_user(
    login_data: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return tokens"""
    # Check rate limit
    allowed, retry_after, stats = check_request_rate_limit(
        request, "auth", db, auth_service
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=SWEDISH_RATE_LIMIT_MESSAGES["rate_limit_exceeded"],
            headers={"Retry-After": str(retry_after)} if retry_after else {}
        )
    
    try:
        user, access_token, refresh_token = auth_service.authenticate_user(login_data, request)
        
        # Set secure HTTP-only cookie for refresh token
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=os.getenv("FORCE_SECURE_COOKIES", "0") == "1",
            samesite="strict",
            max_age=7 * 24 * 3600  # 7 days
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": auth_service.access_token_expire_minutes * 60,
            "user": UserResponse(**user.to_dict()),
            "message": "Inloggning lyckades"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ett fel uppstod vid inloggningen"
        )

@router.post("/logout")
async def logout_user(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Logout user and invalidate session"""
    token = credentials.credentials if credentials else None
    
    auth_service.logout_user(current_user.id, token, request)
    
    # Clear refresh token cookie
    response.delete_cookie("refresh_token")
    
    return {"message": "Utloggning lyckades"}

@router.post("/refresh")
async def refresh_access_token(
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token"""
    # Get refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=SWEDISH_ERROR_MESSAGES["invalid_token"]
        )
    
    new_access_token = auth_service.refresh_access_token(refresh_token)
    if not new_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=SWEDISH_ERROR_MESSAGES["session_expired"]
        )
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_expire_minutes * 60
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(**current_user.to_dict())

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """Update current user information"""
    # Only allow updating certain fields
    allowed_fields = {"full_name", "language", "timezone"}
    update_fields = {k: v for k, v in user_update.items() if k in allowed_fields}
    
    for field, value in update_fields.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse(**current_user.to_dict())

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Change user password"""
    auth_service.change_password(current_user.id, password_data, request)
    return {"message": "Lösenordet har ändrats"}

# Two-Factor Authentication Endpoints

@router.post("/2fa/setup")
async def setup_2fa(
    setup_data: TOTPSetup,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Setup TOTP 2FA for user"""
    result = auth_service.setup_2fa(current_user.id, setup_data, request)
    return {
        "message": "Tvåfaktorautentisering har konfigurerats",
        "qr_code": f"data:image/png;base64,{result['qr_code']}",
        "secret": result["secret"],
        "backup_codes": result["backup_codes"]
    }

@router.post("/2fa/verify")
async def verify_2fa_setup(
    verify_data: TOTPVerify,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Verify and enable TOTP 2FA"""
    auth_service.verify_2fa_setup(current_user.id, verify_data, request)
    return {"message": "Tvåfaktorautentisering har aktiverats"}

@router.delete("/2fa")
async def disable_2fa(
    password: str,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Disable TOTP 2FA for user"""
    auth_service.disable_2fa(current_user.id, password, request)
    return {"message": "Tvåfaktorautentisering har inaktiverats"}

# API Key Management

@router.post("/api-keys")
async def create_api_key(
    key_data: APIKeyCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Create new API key"""
    result = auth_service.create_api_key(current_user.id, key_data, request)
    return {
        "message": "API-nyckel har skapats",
        "api_key": result["key"],  # Only shown once
        "id": result["id"],
        "name": result["name"],
        "created_at": result["created_at"],
        "expires_at": result["expires_at"]
    }

@router.get("/api-keys")
async def list_api_keys(
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """List user's API keys (without key values)"""
    keys = auth_service.get_user_api_keys(current_user.id)
    return {"api_keys": keys}

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Revoke API key"""
    auth_service.revoke_api_key(current_user.id, key_id, request)
    return {"message": "API-nyckeln har återkallats"}

# Session Management

@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """List active sessions for user"""
    sessions = auth_service.get_user_sessions(current_user.id)
    return sessions

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user)
):
    """Revoke specific session"""
    # This would require additional implementation in auth_service
    # For now, just logout all sessions
    auth_service.logout_user(current_user.id, request=request)
    return {"message": "Session har återkallats"}

# OAuth Endpoints

@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Get OAuth authorization URL"""
    try:
        result = oauth_service.get_authorization_url(provider)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth authorization URL generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kunde inte generera {provider} auktorisering"
        )

@router.post("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
    code_verifier: Optional[str] = None,
    db: Session = Depends(get_db_session),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Handle OAuth callback and complete authentication"""
    try:
        user, access_token, refresh_token = await oauth_service.authenticate_with_oauth(
            provider, code, state, code_verifier, request
        )
        
        # Set secure HTTP-only cookie for refresh token
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=os.getenv("FORCE_SECURE_COOKIES", "0") == "1",
            samesite="strict",
            max_age=7 * 24 * 3600  # 7 days
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "user": UserResponse(**user.to_dict()),
            "message": f"Inloggning via {provider} lyckades"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth-autentisering via {provider} misslyckades"
        )

@router.get("/oauth/status")
async def get_oauth_status(
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: User = Depends(get_current_user)
):
    """Get OAuth connection status for user"""
    status_info = oauth_service.get_oauth_status(current_user.id)
    return status_info

@router.delete("/oauth/{provider}")
async def unlink_oauth_provider(
    provider: str,
    password: str,
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service),
    current_user: User = Depends(get_current_user)
):
    """Unlink OAuth provider from user account"""
    oauth_service.unlink_oauth_provider(current_user.id, provider, password, request)
    return {"message": f"{provider.title()}-integrationen har kopplats bort"}

# Admin-only endpoints

@router.get("/users", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """List all users (admin only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "users": [UserResponse(**user.to_dict()) for user in users],
        "count": len(users)
    }

@router.patch("/users/{user_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_user(
    user_id: int,
    user_update: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user (admin only)"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Användaren hittades inte"
        )
    
    # Allow updating admin fields
    allowed_fields = {"role", "is_active", "is_verified", "full_name", "language"}
    update_fields = {k: v for k, v in user_update.items() if k in allowed_fields}
    
    for field, value in update_fields.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return UserResponse(**user.to_dict())

@router.delete("/users/{user_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Delete user (admin only)"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Användaren hittades inte"
        )
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    
    auth_service._log_audit_event(
        auth_service.AuditEventType.LOGIN_FAILED,  # Reusing for admin actions
        user_id=user_id,
        request=request,
        details={"action": "user_deleted", "admin_action": True}
    )
    
    return {"message": "Användaren har inaktiverats"}

# Rate limit status endpoint
@router.get("/rate-limit-status")
async def get_rate_limit_status(
    request: Request,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get current rate limit status for user"""
    from auth_rate_limiter import UserRateLimiter
    
    rate_limiter = UserRateLimiter(db)
    
    if current_user:
        status = rate_limiter.get_user_rate_limit_status(current_user)
    else:
        # Anonymous user status
        client_ip = request.client.host if request.client else "unknown"
        status = {
            "type": "anonymous",
            "client_ip": client_ip,
            "message": "Registrera dig för högre gränser"
        }
    
    return status