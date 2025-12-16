"""
utils/auth/auth_manager.py

Authentication manager factory.
Provides a singleton that can switch between different auth providers.
"""
import os
from typing import Dict, Any, Optional
import logging
from functools import lru_cache

from utils.auth.auth_provider import AuthProvider, AuthProviderUser
from utils.auth.providers.firebase_provider import FirebaseProvider

logger = logging.getLogger(__name__)


class AuthManager:
    """
    Singleton manager for authentication providers.
    Use this instead of direct Firebase imports.
    """
    _instance = None
    _provider = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize with configuration from environment"""
        if not self._initialized:
            self._provider = self._create_provider()
            self._initialized = True
    
    def _create_provider(self) -> AuthProvider:
        """Create auth provider based on configuration"""
        provider_type = os.getenv("AUTH_PROVIDER", "firebase").lower()
        
        if provider_type == "firebase":
            # Firebase configuration from environment
            config = {
                "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                "use_emulator": os.getenv("FIREBASE_EMULATOR_HOST") is not None
            }
            return FirebaseProvider(config)
        
        elif provider_type == "cognito":
            # Placeholder for AWS Cognito
            # To implement: from .providers.cognito_provider import CognitoProvider
            raise NotImplementedError("AWS Cognito provider not implemented yet")
        
        elif provider_type == "supabase":
            # Placeholder for Supabase
            # To implement: from .providers.supabase_provider import SupabaseProvider
            raise NotImplementedError("Supabase provider not implemented yet")
        
        else:
            raise ValueError(f"Unknown auth provider: {provider_type}")
    
    def get_provider(self) -> AuthProvider:
        """Get current auth provider"""
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider
    
    def set_provider(self, provider: AuthProvider):
        """Set custom provider (for testing or advanced use)"""
        self._provider = provider
    
    # Convenience methods that delegate to the provider
    def verify_token(self, token: str) -> AuthProviderUser:
        """Verify token using current provider"""
        return self.get_provider().verify_token(token)
    
    def create_user(self, email: str, password: str, **kwargs) -> AuthProviderUser:
        """Create user using current provider"""
        return self.get_provider().create_user(email, password, **kwargs)
    
    def update_user(self, provider_id: str, **kwargs) -> AuthProviderUser:
        """Update user using current provider"""
        return self.get_provider().update_user(provider_id, **kwargs)
    
    def delete_user(self, provider_id: str) -> bool:
        """Delete user using current provider"""
        return self.get_provider().delete_user(provider_id)
    
    def get_provider_name(self) -> str:
        """Get current provider name"""
        return self.get_provider().get_provider_name()


# Global singleton instance
auth_manager = AuthManager()


@lru_cache()
def get_auth_manager():
    """Get the singleton auth manager instance"""
    return auth_manager