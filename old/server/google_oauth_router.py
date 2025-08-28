"""
Google OAuth Router for Calendar/Gmail Integration
Production-ready API endpoints for Google service access
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging

from database import get_db
from deps import get_current_user
from auth_models import User
from google_oauth_service import GoogleOAuthService, GoogleToken
from rate_limiter import RateLimiter

logger = logging.getLogger("alice.google_oauth_router")

# Initialize rate limiter for OAuth operations
oauth_rate_limiter = RateLimiter(
    calls=10,  # 10 OAuth operations
    period=300,  # per 5 minutes
    identifier_func=lambda request: f"oauth_{request.client.host}"
)

router = APIRouter(prefix="/api/v1/oauth/google", tags=["Google OAuth"])

# Pydantic models
class OAuthAuthorizationRequest(BaseModel):
    scope_set: str = Field(..., description="Predefined scope set: basic, calendar, calendar_write, gmail, gmail_send, full_access")
    redirect_after_auth: Optional[str] = Field(None, description="URL to redirect to after successful auth")

class OAuthAuthorizationResponse(BaseModel):
    authorization_url: str
    state: str
    scope_description: Dict[str, str]
    expires_in: int = Field(default=600, description="State expires in seconds")

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    code_verifier: str

class OAuthStatusResponse(BaseModel):
    connected: bool
    scopes: List[str]
    scope_descriptions: Dict[str, str] = {}
    expires_at: Optional[str] = None
    needs_refresh: bool = False
    has_refresh_token: bool = False
    last_updated: Optional[str] = None
    available_scope_sets: List[str] = []
    missing_scopes: Dict[str, List[str]] = {}

class ScopeUpgradeRequest(BaseModel):
    additional_scope_set: str = Field(..., description="Additional scope set to request")

def get_google_oauth_service(db: Session = Depends(get_db)) -> GoogleOAuthService:
    """Dependency to get Google OAuth service"""
    return GoogleOAuthService(db)

@router.get("/status", response_model=OAuthStatusResponse)
async def get_oauth_status(
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Get current Google OAuth connection status"""
    try:
        status_data = oauth_service.get_token_status(current_user.id)
        return OAuthStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"Failed to get OAuth status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta OAuth-status"
        )

@router.get("/scope-sets")
async def list_scope_sets(
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """List available OAuth scope sets with descriptions"""
    scope_sets = {}
    
    for scope_set, scopes in GoogleOAuthService.SCOPE_SETS.items():
        descriptions = oauth_service._describe_scopes(scopes)
        scope_sets[scope_set] = {
            "scopes": scopes,
            "descriptions": descriptions,
            "total_permissions": len(scopes)
        }
    
    return {
        "scope_sets": scope_sets,
        "recommendation": {
            "basic": "För grundläggande profil-åtkomst",
            "calendar": "För att läsa kalenderevenemang och påminnelser",
            "calendar_write": "För att skapa och redigera kalenderevenemang", 
            "gmail": "För att läsa e-post och etiketter",
            "gmail_send": "För att skicka e-post",
            "full_access": "För full integrering med Google-tjänster (rekommenderas)"
        }
    }

@router.post("/authorize", response_model=OAuthAuthorizationResponse)
async def start_oauth_flow(
    request_data: OAuthAuthorizationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Start Google OAuth authorization flow"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_start_{current_user.id}")
    
    if not oauth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth-integration är inte konfigurerad på servern"
        )
    
    try:
        # Get authorization URL for requested scope set
        auth_data = oauth_service.get_scope_set_url(
            scope_set=request_data.scope_set,
            user_id=current_user.id,
            state=f"{request_data.scope_set}_{current_user.id}"
        )
        
        # Store state and code_verifier in session/cache for callback
        # In production, you might want to use Redis or database storage
        request.session[f"oauth_state_{auth_data['state']}"] = {
            "code_verifier": auth_data["code_verifier"],
            "user_id": current_user.id,
            "scope_set": request_data.scope_set,
            "redirect_after_auth": request_data.redirect_after_auth
        }
        
        logger.info(f"Started OAuth flow for user {current_user.id} with scope set: {request_data.scope_set}")
        
        return OAuthAuthorizationResponse(
            authorization_url=auth_data["authorization_url"],
            state=auth_data["state"],
            scope_description=auth_data["scope_description"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start OAuth flow for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte starta OAuth-auktorisering"
        )

@router.post("/callback")
async def oauth_callback(
    callback_data: OAuthCallbackRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Handle OAuth callback from Google"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_callback_{current_user.id}")
    
    # Retrieve stored state data
    session_key = f"oauth_state_{callback_data.state}"
    state_data = request.session.get(session_key)
    
    if not state_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ogiltigt eller utgånget OAuth-tillstånd"
        )
    
    # Verify user matches
    if state_data["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OAuth-tillstånd matchar inte aktuell användare"
        )
    
    try:
        # Exchange code for tokens
        google_token = await oauth_service.exchange_code_for_tokens(
            code=callback_data.code,
            state=callback_data.state,
            code_verifier=callback_data.code_verifier,
            user_id=current_user.id
        )
        
        # Clear session state
        request.session.pop(session_key, None)
        
        logger.info(f"Successfully completed OAuth flow for user {current_user.id}")
        
        # Determine redirect URL
        redirect_url = state_data.get("redirect_after_auth", "/dashboard?oauth=success")
        
        return {
            "success": True,
            "message": "Google-kontot är nu anslutet till Alice",
            "scopes": google_token.scopes,
            "redirect_url": redirect_url,
            "token_expires": google_token.expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth-auktorisering misslyckades"
        )

@router.post("/upgrade-scopes")
async def upgrade_scopes(
    upgrade_request: ScopeUpgradeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Request additional scopes (incremental authorization)"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_upgrade_{current_user.id}")
    
    # Check current status
    current_status = oauth_service.get_token_status(current_user.id)
    if not current_status["connected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inget Google-konto anslutet. Anslut först ett konto."
        )
    
    # Check if upgrade is needed
    if upgrade_request.additional_scope_set not in current_status["missing_scopes"]:
        return {
            "success": True,
            "message": "Begärda behörigheter är redan tillgängliga",
            "current_scopes": current_status["scopes"]
        }
    
    try:
        # Start incremental authorization
        auth_data = oauth_service.get_scope_set_url(
            scope_set=upgrade_request.additional_scope_set,
            user_id=current_user.id,
            state=f"upgrade_{upgrade_request.additional_scope_set}_{current_user.id}"
        )
        
        # Store state for callback
        request.session[f"oauth_state_{auth_data['state']}"] = {
            "code_verifier": auth_data["code_verifier"],
            "user_id": current_user.id,
            "scope_set": upgrade_request.additional_scope_set,
            "is_upgrade": True
        }
        
        return {
            "authorization_url": auth_data["authorization_url"],
            "state": auth_data["state"],
            "additional_scopes": auth_data["scope_description"],
            "message": "Omdirigerar till Google för ytterligare behörigheter"
        }
        
    except Exception as e:
        logger.error(f"Scope upgrade failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte begära ytterligare behörigheter"
        )

@router.post("/refresh")
async def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Manually refresh Google OAuth token"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_refresh_{current_user.id}")
    
    try:
        refreshed_token = await oauth_service.refresh_access_token(current_user.id)
        
        if not refreshed_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Kunde inte förnya åtkomst-token. Omauktorisering kan krävas."
            )
        
        return {
            "success": True,
            "message": "Token förnyades framgångsrikt",
            "expires_at": refreshed_token.expires_at.isoformat(),
            "scopes": refreshed_token.scopes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token-förnyelse misslyckades"
        )

@router.post("/test-connection")
async def test_connection(
    request: Request,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Test Google OAuth connection and token validity"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_test_{current_user.id}")
    
    try:
        test_result = await oauth_service.test_token_validity(current_user.id)
        
        if test_result["valid"]:
            return {
                "success": True,
                "message": "Google-anslutning fungerar korrekt",
                "token_info": test_result
            }
        else:
            return {
                "success": False,
                "message": "Google-anslutning har problem",
                "error": test_result.get("error"),
                "recommendation": "Försök förnya token eller återanslut ditt Google-konto"
            }
            
    except Exception as e:
        logger.error(f"Connection test failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte testa Google-anslutning"
        )

@router.delete("/disconnect")
async def disconnect_google(
    request: Request,
    current_user: User = Depends(get_current_user),
    oauth_service: GoogleOAuthService = Depends(get_google_oauth_service)
):
    """Disconnect Google account and revoke tokens"""
    # Apply rate limiting
    await oauth_rate_limiter.check_rate_limit(request, f"oauth_disconnect_{current_user.id}")
    
    try:
        success = await oauth_service.revoke_tokens(current_user.id)
        
        return {
            "success": True,
            "message": "Google-konto frånkopplat från Alice",
            "revoked_successfully": success,
            "note": "Du kan återansluta ditt Google-konto när som helst"
        }
        
    except Exception as e:
        logger.error(f"Google disconnect failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte koppla från Google-konto"
        )

# Admin endpoints (if needed)
@router.get("/admin/stats")
async def get_oauth_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get OAuth usage statistics (admin only)"""
    # Check if user is admin (implement your admin check logic)
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administratörsbehörighet krävs"
        )
    
    try:
        # Get OAuth statistics
        total_tokens = db.query(GoogleToken).count()
        active_tokens = db.query(GoogleToken).filter(GoogleToken.is_active == True).count()
        
        # Scope usage statistics
        scope_usage = {}
        tokens = db.query(GoogleToken).filter(GoogleToken.is_active == True).all()
        
        for token in tokens:
            for scope in token.scopes or []:
                scope_usage[scope] = scope_usage.get(scope, 0) + 1
        
        return {
            "total_oauth_connections": total_tokens,
            "active_connections": active_tokens,
            "inactive_connections": total_tokens - active_tokens,
            "scope_usage": scope_usage,
            "most_requested_scopes": sorted(
                scope_usage.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
        }
        
    except Exception as e:
        logger.error(f"Failed to get OAuth stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Kunde inte hämta OAuth-statistik"
        )