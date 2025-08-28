"""
OAuth Integration Service for Google and GitHub
Secure OAuth 2.0 authentication flow with PKCE support
"""
import os
import secrets
import hashlib
import base64
import httpx
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Request
from urllib.parse import urlencode

from auth_models import User, AuditEventType, SWEDISH_ERROR_MESSAGES
from auth_service import AuthService

logger = logging.getLogger("alice.oauth")

class OAuthService:
    """OAuth 2.0 authentication service"""
    
    def __init__(self, db_session: Session, auth_service: AuthService):
        self.db = db_session
        self.auth_service = auth_service
        
        # OAuth configurations
        self.providers = {
            "google": {
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "scopes": ["openid", "email", "profile"],
                "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:3000/auth/google/callback")
            },
            "github": {
                "client_id": os.getenv("GITHUB_CLIENT_ID"),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
                "auth_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_info_url": "https://api.github.com/user",
                "scopes": ["user:email", "read:user"],
                "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:3000/auth/github/callback")
            }
        }
        
        # Validate OAuth configuration
        for provider_name, config in self.providers.items():
            if not config["client_id"] or not config["client_secret"]:
                logger.warning(f"OAuth provider {provider_name} is not properly configured")
    
    def generate_pkce_challenge(self) -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge for OAuth security"""
        # Generate code verifier (43-128 characters, URL-safe)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode('utf-8').rstrip('=')
        
        # Generate code challenge (SHA256 hash of verifier)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode('utf-8').rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(
        self, 
        provider: str, 
        state: Optional[str] = None,
        use_pkce: bool = True
    ) -> Dict[str, str]:
        """Generate OAuth authorization URL with PKCE"""
        if provider not in self.providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth-leverantör '{provider}' stöds inte"
            )
        
        config = self.providers[provider]
        
        if not config["client_id"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OAuth-integration för {provider} är inte konfigurerad"
            )
        
        # Generate state for CSRF protection
        if not state:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "scope": " ".join(config["scopes"]),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # For refresh tokens
            "prompt": "select_account"  # Always show account picker
        }
        
        # Add PKCE parameters if supported
        code_verifier = None
        if use_pkce and provider == "google":  # Google supports PKCE
            code_verifier, code_challenge = self.generate_pkce_challenge()
            params.update({
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            })
        
        authorization_url = f"{config['auth_url']}?{urlencode(params)}"
        
        return {
            "authorization_url": authorization_url,
            "state": state,
            "code_verifier": code_verifier  # Store this securely on client side
        }
    
    async def exchange_code_for_token(
        self, 
        provider: str, 
        code: str, 
        state: str,
        code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        if provider not in self.providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth-leverantör '{provider}' stöds inte"
            )
        
        config = self.providers[provider]
        
        # Prepare token exchange request
        token_data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": config["redirect_uri"]
        }
        
        # Add PKCE verifier if provided
        if code_verifier:
            token_data["code_verifier"] = code_verifier
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    config["token_url"],
                    data=token_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"OAuth token exchange failed: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="OAuth-autentisering misslyckades"
                    )
                
                token_response = response.json()
                
                if "error" in token_response:
                    logger.error(f"OAuth error: {token_response}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=SWEDISH_ERROR_MESSAGES["oauth_error"]
                    )
                
                return token_response
                
        except httpx.RequestError as e:
            logger.error(f"OAuth request failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kunde inte ansluta till OAuth-leverantör"
            )
    
    async def get_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """Get user information from OAuth provider"""
        if provider not in self.providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth-leverantör '{provider}' stöds inte"
            )
        
        config = self.providers[provider]
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get user info
                response = await client.get(config["user_info_url"], headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to get user info: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Kunde inte hämta användarinformation"
                    )
                
                user_info = response.json()
                
                # For GitHub, we need to get email separately if not public
                if provider == "github" and not user_info.get("email"):
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers=headers
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        primary_email = next(
                            (email["email"] for email in emails if email.get("primary")),
                            None
                        )
                        if primary_email:
                            user_info["email"] = primary_email
                
                return self._normalize_user_info(provider, user_info)
                
        except httpx.RequestError as e:
            logger.error(f"Failed to get user info: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Kunde inte hämta användarinformation"
            )
    
    def _normalize_user_info(self, provider: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize user info from different providers"""
        if provider == "google":
            return {
                "provider_id": user_info.get("id"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "first_name": user_info.get("given_name"),
                "last_name": user_info.get("family_name"),
                "avatar_url": user_info.get("picture"),
                "verified_email": user_info.get("verified_email", False),
                "provider": "google"
            }
        elif provider == "github":
            return {
                "provider_id": str(user_info.get("id")),
                "email": user_info.get("email"),
                "name": user_info.get("name") or user_info.get("login"),
                "username": user_info.get("login"),
                "avatar_url": user_info.get("avatar_url"),
                "bio": user_info.get("bio"),
                "company": user_info.get("company"),
                "location": user_info.get("location"),
                "provider": "github"
            }
        else:
            return user_info
    
    async def authenticate_with_oauth(
        self, 
        provider: str, 
        code: str, 
        state: str,
        code_verifier: Optional[str] = None,
        request: Optional[Request] = None
    ) -> Tuple[User, str, str]:
        """Complete OAuth authentication flow"""
        try:
            # Exchange code for token
            token_response = await self.exchange_code_for_token(
                provider, code, state, code_verifier
            )
            
            # Get user information
            user_info = await self.get_user_info(provider, token_response["access_token"])
            
            if not user_info.get("email"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="E-postadress krävs för OAuth-autentisering"
                )
            
            # Find or create user
            user = await self._find_or_create_oauth_user(provider, user_info, request)
            
            # Create session and tokens
            access_token, refresh_token = self.auth_service._create_tokens(user, True)
            
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            self.auth_service._log_audit_event(
                AuditEventType.OAUTH_LOGIN,
                user_id=user.id,
                request=request,
                details={
                    "provider": provider,
                    "provider_id": user_info.get("provider_id"),
                    "method": "oauth"
                }
            )
            
            return user, access_token, refresh_token
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            
            self.auth_service._log_audit_event(
                AuditEventType.OAUTH_FAILED,
                request=request,
                success=False,
                details={"provider": provider, "error": str(e)}
            )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth-autentisering misslyckades"
            )
    
    async def _find_or_create_oauth_user(
        self, 
        provider: str, 
        user_info: Dict[str, Any],
        request: Optional[Request] = None
    ) -> User:
        """Find existing user or create new one from OAuth info"""
        provider_id = user_info["provider_id"]
        email = user_info["email"]
        
        # First, try to find user by OAuth provider ID
        user = None
        if provider == "google":
            user = self.db.query(User).filter(User.google_id == provider_id).first()
        elif provider == "github":
            user = self.db.query(User).filter(User.github_id == int(provider_id)).first()
        
        # If not found, try to find by email
        if not user:
            user = self.db.query(User).filter(User.email == email).first()
            
            if user:
                # Link OAuth account to existing user
                if provider == "google":
                    user.google_id = provider_id
                elif provider == "github":
                    user.github_id = int(provider_id)
                
                # Update OAuth providers list
                if not user.oauth_providers:
                    user.oauth_providers = []
                if provider not in user.oauth_providers:
                    user.oauth_providers.append(provider)
                
                self.db.commit()
        
        # Create new user if not found
        if not user:
            username = self._generate_username_from_oauth(user_info)
            
            user = User(
                username=username,
                email=email,
                full_name=user_info.get("name"),
                is_verified=user_info.get("verified_email", False),
                oauth_providers=[provider],
                language="sv"  # Default to Swedish
            )
            
            # Set OAuth provider ID
            if provider == "google":
                user.google_id = provider_id
            elif provider == "github":
                user.github_id = int(provider_id)
            
            # Set a random password (OAuth users don't use password login)
            user.set_password(secrets.token_urlsafe(32))
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Created new OAuth user: {username} via {provider}")
        
        return user
    
    def _generate_username_from_oauth(self, user_info: Dict[str, Any]) -> str:
        """Generate unique username from OAuth user info"""
        base_username = (
            user_info.get("username") or 
            user_info.get("email", "").split("@")[0] or
            user_info.get("name", "").lower().replace(" ", "_") or
            "user"
        )
        
        # Clean username
        base_username = "".join(c for c in base_username if c.isalnum() or c in "_-")[:30]
        
        # Ensure uniqueness
        username = base_username
        counter = 1
        while self.db.query(User).filter(User.username == username).first():
            username = f"{base_username}_{counter}"
            counter += 1
            if counter > 1000:  # Prevent infinite loop
                username = f"{base_username}_{secrets.token_hex(4)}"
                break
        
        return username
    
    def unlink_oauth_provider(
        self, 
        user_id: int, 
        provider: str, 
        password: str,
        request: Optional[Request] = None
    ):
        """Unlink OAuth provider from user account"""
        user = self.auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Användaren hittades inte"
            )
        
        # Verify password (unless user only has OAuth login)
        has_password = user.password_hash and len(user.password_hash) < 100  # OAuth users have long random passwords
        if has_password and not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=SWEDISH_ERROR_MESSAGES["invalid_credentials"]
            )
        
        # Ensure user has other login methods
        other_providers = [p for p in (user.oauth_providers or []) if p != provider]
        if not has_password and not other_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kan inte ta bort den sista inloggningsmetoden"
            )
        
        # Remove OAuth provider
        if provider == "google":
            user.google_id = None
        elif provider == "github":
            user.github_id = None
        
        if user.oauth_providers and provider in user.oauth_providers:
            user.oauth_providers.remove(provider)
        
        self.db.commit()
        
        self.auth_service._log_audit_event(
            AuditEventType.OAUTH_FAILED,  # Reusing for unlinking
            user_id=user_id,
            request=request,
            details={"action": "oauth_unlinked", "provider": provider}
        )
    
    def get_oauth_status(self, user_id: int) -> Dict[str, Any]:
        """Get OAuth connection status for user"""
        user = self.auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Användaren hittades inte"
            )
        
        return {
            "google": {
                "connected": bool(user.google_id),
                "available": bool(self.providers["google"]["client_id"])
            },
            "github": {
                "connected": bool(user.github_id),
                "available": bool(self.providers["github"]["client_id"])
            },
            "has_password": bool(user.password_hash and len(user.password_hash) < 100)
        }