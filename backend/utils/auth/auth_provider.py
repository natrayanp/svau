"""
utils/auth/auth_provider.py

Abstract authentication provider interface.
All auth providers must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AuthProviderUser(BaseModel):
    """Standardized user data from any auth provider"""
    provider_id: str  # Unique ID from provider (Firebase UID, Cognito Sub, etc.)
    email: str
    email_verified: bool
    name: Optional[str] = None
    picture: Optional[str] = None
    provider_name: str = "unknown"


class AuthProvider(ABC):
    """Abstract interface for all auth providers"""
    
    @abstractmethod
    def verify_token(self, token: str) -> AuthProviderUser:
        """Verify token and return standardized user data"""
        pass
    
    @abstractmethod
    def create_user(self, email: str, password: str, **kwargs) -> AuthProviderUser:
        """Create new user in auth provider"""
        pass
    
    @abstractmethod
    def update_user(self, provider_id: str, **kwargs) -> AuthProviderUser:
        """Update user in auth provider"""
        pass
    
    @abstractmethod
    def delete_user(self, provider_id: str) -> bool:
        """Delete user from auth provider"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider identifier"""
        pass