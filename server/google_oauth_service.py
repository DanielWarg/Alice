"""
Enhanced Google OAuth Service for Calendar/Gmail Access
Production-ready OAuth 2.0 implementation with proper scope management
"""
import os
import secrets
import hashlib
import base64
import httpx
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from fastapi import HTTPException, status, Request
from urllib.parse import urlencode
import json

from database import Base
from auth_models import User, AuditEventType

logger = logging.getLogger("alice.google_oauth")

class GoogleToken(Base):
    """Model for storing Google OAuth tokens with scope management"""
    __tablename__ = "google_tokens"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)  # One token set per user
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime, nullable=False)
    scopes = Column(JSON, nullable=False)  # List of granted scopes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Additional metadata
    client_id = Column(String(255), nullable=True)
    granted_permissions = Column(JSON, nullable=True)  # Detailed permissions
    revoked_at = Column(DateTime, nullable=True)

class GoogleOAuthService:
    """Enhanced Google OAuth service for Calendar/Gmail integration"""
    
    # Predefined scope sets for different use cases
    SCOPE_SETS = {
        "basic": [
            "openid",
            "email", 
            "profile"
        ],
        "calendar": [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events.readonly"
        ],
        "calendar_write": [
            "openid",
            "email", 
            "profile",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events"
        ],
        "gmail": [
            "openid",
            "email",
            "profile", 
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.labels"
        ],
        "gmail_send": [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/gmail.send"
        ],
        "full_access": [
            "openid",
            "email",
            "profile",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.modify"
        ]
    }
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
        # OAuth configuration
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
        
        # Google OAuth endpoints
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.revoke_url = "https://oauth2.googleapis.com/revoke"
        self.user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.token_info_url = "https://oauth2.googleapis.com/tokeninfo"
        
        if not self.client_id or not self.client_secret:
            logger.warning("Google OAuth is not properly configured")
    
    def is_configured(self) -> bool:
        """Check if Google OAuth is properly configured"""
        return bool(self.client_id and self.client_secret)
    
    def generate_pkce_pair(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        return code_verifier, code_challenge
    
    def build_authorization_url(
        self,
        scopes: List[str],
        state: Optional[str] = None,
        user_hint: Optional[str] = None,
        prompt: str = "consent",
        access_type: str = "offline"
    ) -> Dict[str, str]:
        """
        Build Google OAuth authorization URL with enhanced options
        
        Args:
            scopes: List of OAuth scopes to request
            state: CSRF protection state parameter
            user_hint: Email hint for account selection
            prompt: OAuth prompt parameter (consent, select_account, none)
            access_type: offline for refresh tokens, online for access only
        """
        if not self.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth integration är inte konfigurerad"
            )
        
        # Validate scopes
        validated_scopes = self._validate_scopes(scopes)
        
        # Generate security parameters
        if not state:
            state = secrets.token_urlsafe(32)
        
        code_verifier, code_challenge = self.generate_pkce_pair()
        
        # Build parameters
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(validated_scopes),
            "response_type": "code",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": access_type,
            "prompt": prompt,
            "include_granted_scopes": "true"  # Incremental authorization
        }
        
        if user_hint:
            params["login_hint"] = user_hint
        
        authorization_url = f"{self.auth_url}?{urlencode(params)}"
        
        return {
            "authorization_url": authorization_url,
            "state": state,
            "code_verifier": code_verifier,
            "requested_scopes": validated_scopes,
            "scope_description": self._describe_scopes(validated_scopes)
        }
    
    def get_scope_set_url(
        self,
        scope_set: str,
        user_id: Optional[int] = None,
        state: Optional[str] = None
    ) -> Dict[str, str]:
        """Get authorization URL for predefined scope set"""
        if scope_set not in self.SCOPE_SETS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Okänd behörighetsgrupp: {scope_set}"
            )
        
        scopes = self.SCOPE_SETS[scope_set].copy()
        user_hint = None
        
        # Add user email hint if user provided
        if user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if user and user.email:
                user_hint = user.email
        
        return self.build_authorization_url(
            scopes=scopes,
            state=state or f"{scope_set}_{secrets.token_urlsafe(16)}",
            user_hint=user_hint,
            prompt="consent"  # Always ask for consent for service scopes
        )
    
    async def exchange_code_for_tokens(
        self,
        code: str,
        state: str,
        code_verifier: str,
        user_id: int
    ) -> GoogleToken:
        """Exchange authorization code for access and refresh tokens"""
        token_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=token_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Kunde inte utväxla auktoriseringskod mot tokens"
                    )
                
                token_response = response.json()
                
                if "error" in token_response:
                    logger.error(f"OAuth error: {token_response}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"OAuth-fel: {token_response.get('error_description', token_response['error'])}"
                    )
                
                # Parse granted scopes
                granted_scopes = token_response.get("scope", "").split()
                
                # Calculate expiration time
                expires_in = token_response.get("expires_in", 3600)
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                # Store or update token
                google_token = await self._store_tokens(
                    user_id=user_id,
                    access_token=token_response["access_token"],
                    refresh_token=token_response.get("refresh_token"),
                    token_type=token_response.get("token_type", "Bearer"),
                    expires_at=expires_at,
                    scopes=granted_scopes
                )
                
                logger.info(f"Successfully stored Google tokens for user {user_id} with scopes: {granted_scopes}")
                return google_token
                
        except httpx.RequestError as e:
            logger.error(f"Token exchange request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kunde inte ansluta till Google OAuth-tjänsten"
            )
    
    async def _store_tokens(
        self,
        user_id: int,
        access_token: str,
        refresh_token: Optional[str],
        token_type: str,
        expires_at: datetime,
        scopes: List[str]
    ) -> GoogleToken:
        """Store or update Google tokens in database"""
        # Check for existing token
        existing_token = self.db.query(GoogleToken).filter(GoogleToken.user_id == user_id).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = access_token
            if refresh_token:  # Only update if new refresh token provided
                existing_token.refresh_token = refresh_token
            existing_token.token_type = token_type
            existing_token.expires_at = expires_at
            existing_token.scopes = scopes
            existing_token.updated_at = datetime.utcnow()
            existing_token.is_active = True
            existing_token.revoked_at = None
            
            google_token = existing_token
        else:
            # Create new token
            google_token = GoogleToken(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_type=token_type,
                expires_at=expires_at,
                scopes=scopes,
                client_id=self.client_id
            )
            self.db.add(google_token)
        
        self.db.commit()
        self.db.refresh(google_token)
        return google_token
    
    async def refresh_access_token(self, user_id: int) -> Optional[GoogleToken]:
        """Refresh expired access token using refresh token"""
        google_token = self.db.query(GoogleToken).filter(
            GoogleToken.user_id == user_id,
            GoogleToken.is_active == True
        ).first()
        
        if not google_token or not google_token.refresh_token:
            logger.warning(f"No refresh token available for user {user_id}")
            return None
        
        refresh_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": google_token.refresh_token,
            "grant_type": "refresh_token"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.token_url,
                    data=refresh_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    # Mark token as inactive if refresh fails
                    google_token.is_active = False
                    self.db.commit()
                    return None
                
                token_response = response.json()
                
                if "error" in token_response:
                    logger.error(f"Token refresh error: {token_response}")
                    google_token.is_active = False
                    self.db.commit()
                    return None
                
                # Update token
                google_token.access_token = token_response["access_token"]
                if "refresh_token" in token_response:  # New refresh token provided
                    google_token.refresh_token = token_response["refresh_token"]
                
                expires_in = token_response.get("expires_in", 3600)
                google_token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                google_token.updated_at = datetime.utcnow()
                
                self.db.commit()
                self.db.refresh(google_token)
                
                logger.info(f"Successfully refreshed token for user {user_id}")
                return google_token
                
        except httpx.RequestError as e:
            logger.error(f"Token refresh request failed: {e}")
            return None
    
    async def get_valid_token(self, user_id: int) -> Optional[str]:
        """Get valid access token, refreshing if necessary"""
        google_token = self.db.query(GoogleToken).filter(
            GoogleToken.user_id == user_id,
            GoogleToken.is_active == True
        ).first()
        
        if not google_token:
            return None
        
        # Check if token is expired
        now = datetime.utcnow()
        if google_token.expires_at <= now + timedelta(minutes=5):  # Refresh 5 minutes early
            logger.info(f"Token expired for user {user_id}, attempting refresh")
            google_token = await self.refresh_access_token(user_id)
            if not google_token:
                return None
        
        return google_token.access_token
    
    async def revoke_tokens(self, user_id: int) -> bool:
        """Revoke all Google tokens for user"""
        google_token = self.db.query(GoogleToken).filter(
            GoogleToken.user_id == user_id,
            GoogleToken.is_active == True
        ).first()
        
        if not google_token:
            return True  # No tokens to revoke
        
        # Revoke with Google
        success = False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try to revoke access token
                response = await client.post(
                    self.revoke_url,
                    params={"token": google_token.access_token}
                )
                success = response.status_code == 200
                
                # Also try refresh token if available
                if google_token.refresh_token:
                    refresh_response = await client.post(
                        self.revoke_url,
                        params={"token": google_token.refresh_token}
                    )
                    success = success or refresh_response.status_code == 200
                    
        except httpx.RequestError as e:
            logger.error(f"Token revocation request failed: {e}")
        
        # Mark as inactive in database regardless of revocation result
        google_token.is_active = False
        google_token.revoked_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Revoked Google tokens for user {user_id}")
        return success
    
    def get_token_status(self, user_id: int) -> Dict[str, Any]:
        """Get detailed token status for user"""
        google_token = self.db.query(GoogleToken).filter(
            GoogleToken.user_id == user_id,
            GoogleToken.is_active == True
        ).first()
        
        if not google_token:
            return {
                "connected": False,
                "scopes": [],
                "expires_at": None,
                "needs_refresh": False,
                "available_scope_sets": list(self.SCOPE_SETS.keys())
            }
        
        now = datetime.utcnow()
        needs_refresh = google_token.expires_at <= now + timedelta(minutes=10)
        
        return {
            "connected": True,
            "scopes": google_token.scopes or [],
            "scope_descriptions": self._describe_scopes(google_token.scopes or []),
            "expires_at": google_token.expires_at.isoformat(),
            "needs_refresh": needs_refresh,
            "has_refresh_token": bool(google_token.refresh_token),
            "last_updated": google_token.updated_at.isoformat(),
            "available_scope_sets": list(self.SCOPE_SETS.keys()),
            "missing_scopes": self._find_missing_scopes(google_token.scopes or [])
        }
    
    def _validate_scopes(self, scopes: List[str]) -> List[str]:
        """Validate and filter OAuth scopes"""
        # Known Google OAuth scopes for Calendar and Gmail
        valid_scopes = {
            # Basic
            "openid", "email", "profile",
            # Calendar
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/calendar.events.readonly",
            # Gmail
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.compose"
        }
        
        validated = [scope for scope in scopes if scope in valid_scopes]
        
        # Ensure basic scopes are included
        for basic_scope in ["openid", "email", "profile"]:
            if basic_scope not in validated:
                validated.insert(0, basic_scope)
        
        return validated
    
    def _describe_scopes(self, scopes: List[str]) -> Dict[str, str]:
        """Provide human-readable descriptions of OAuth scopes"""
        descriptions = {
            "openid": "Grundläggande identifiering",
            "email": "Åtkomst till e-postadress", 
            "profile": "Åtkomst till profilinformation",
            "https://www.googleapis.com/auth/calendar": "Full åtkomst till kalendrar",
            "https://www.googleapis.com/auth/calendar.readonly": "Läsa kalendrar och evenemang",
            "https://www.googleapis.com/auth/calendar.events": "Skapa och redigera kalenderevenemang",
            "https://www.googleapis.com/auth/calendar.events.readonly": "Läsa kalenderevenemang",
            "https://www.googleapis.com/auth/gmail.readonly": "Läsa e-post och etiketter",
            "https://www.googleapis.com/auth/gmail.send": "Skicka e-post för din räkning",
            "https://www.googleapis.com/auth/gmail.labels": "Hantera e-postetiketter",
            "https://www.googleapis.com/auth/gmail.modify": "Ändra e-post (markera som läst, arkivera)",
            "https://www.googleapis.com/auth/gmail.compose": "Skriva e-post"
        }
        
        return {scope: descriptions.get(scope, "Okänd behörighet") for scope in scopes}
    
    def _find_missing_scopes(self, current_scopes: List[str]) -> Dict[str, List[str]]:
        """Find what additional scopes are needed for each scope set"""
        missing = {}
        
        for scope_set, required_scopes in self.SCOPE_SETS.items():
            missing_for_set = [scope for scope in required_scopes if scope not in current_scopes]
            if missing_for_set:
                missing[scope_set] = missing_for_set
        
        return missing
    
    async def test_token_validity(self, user_id: int) -> Dict[str, Any]:
        """Test if stored token is valid by making a test API call"""
        access_token = await self.get_valid_token(user_id)
        if not access_token:
            return {"valid": False, "error": "No valid token available"}
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.token_info_url,
                    params={"access_token": access_token}
                )
                
                if response.status_code == 200:
                    token_info = response.json()
                    return {
                        "valid": True,
                        "expires_in": token_info.get("expires_in"),
                        "scope": token_info.get("scope"),
                        "audience": token_info.get("aud")
                    }
                else:
                    return {"valid": False, "error": "Token validation failed"}
                    
        except httpx.RequestError as e:
            return {"valid": False, "error": f"Network error: {str(e)}"}

# Utility functions for service integration
async def require_google_token(oauth_service: GoogleOAuthService, user_id: int) -> str:
    """Require valid Google token or raise HTTP exception"""
    token = await oauth_service.get_valid_token(user_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google OAuth-auktorisering krävs. Vänligen anslut ditt Google-konto."
        )
    return token

async def require_calendar_access(oauth_service: GoogleOAuthService, user_id: int) -> str:
    """Require Google token with Calendar access"""
    token_status = oauth_service.get_token_status(user_id)
    
    if not token_status["connected"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google-kontoanslutning krävs för kalenderåtkomst"
        )
    
    # Check for calendar scopes
    scopes = token_status["scopes"]
    has_calendar = any(
        "calendar" in scope for scope in scopes
        if scope.startswith("https://www.googleapis.com/auth/")
    )
    
    if not has_calendar:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kalenderbehörigheter saknas. Vänligen ge åtkomst till din Google Kalender."
        )
    
    return await oauth_service.get_valid_token(user_id)

async def require_gmail_access(oauth_service: GoogleOAuthService, user_id: int) -> str:
    """Require Google token with Gmail access"""
    token_status = oauth_service.get_token_status(user_id)
    
    if not token_status["connected"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google-kontoanslutning krävs för Gmail-åtkomst"
        )
    
    # Check for Gmail scopes
    scopes = token_status["scopes"]
    has_gmail = any(
        "gmail" in scope for scope in scopes
        if scope.startswith("https://www.googleapis.com/auth/")
    )
    
    if not has_gmail:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Gmail-behörigheter saknas. Vänligen ge åtkomst till ditt Gmail-konto."
        )
    
    return await oauth_service.get_valid_token(user_id)