"""
utils/auth/providers/firebase_provider.py

Firebase authentication provider implementation.
This wraps your existing Firebase code in the provider interface.
"""
import os
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
import logging

from utils.auth.auth_provider import AuthProvider, AuthProviderUser

# Import your existing Firebase components
from utils.auth.firebase_utils import firebase_manager

logger = logging.getLogger(__name__)


class FirebaseProvider(AuthProvider):
    """Firebase authentication provider"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Firebase provider.
        config can be used for future customization if needed.
        """
        # Your existing FirebaseManager is already initialized as a singleton
        # We'll use the existing firebase_manager instance
        self.config = config or {}
        logger.info(f"✅ Firebase provider initialized")
    
    def verify_token(self, token: str) -> AuthProviderUser:
        """Verify Firebase token using your existing code"""
        try:
            # Use your existing firebase_manager
            firebase_user = firebase_manager.verify_firebase_token(token)
            
            return AuthProviderUser(
                provider_id=firebase_user["uid"],
                email=firebase_user.get("email", ""),
                email_verified=firebase_user.get("email_verified", False),
                name=firebase_user.get("display_name"),
                picture=firebase_user.get("picture"),
                provider_name="firebase"
            )
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            logger.error(f"Firebase token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )
    
    def create_user(self, email: str, password: str, **kwargs) -> AuthProviderUser:
        """
        Create user in Firebase.
        Note: This requires Firebase Admin SDK with appropriate permissions.
        """
        try:
            import firebase_admin
            from firebase_admin import auth
            
            # Create user in Firebase
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=kwargs.get('display_name'),
                email_verified=kwargs.get('email_verified', False),
                disabled=kwargs.get('disabled', False)
            )
            
            return AuthProviderUser(
                provider_id=user_record.uid,
                email=user_record.email,
                email_verified=user_record.email_verified,
                name=user_record.display_name,
                picture=kwargs.get('photo_url'),
                provider_name="firebase"
            )
            
        except Exception as e:
            logger.error(f"Firebase user creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user: {str(e)}"
            )
    
    def update_user(self, provider_id: str, **kwargs) -> AuthProviderUser:
        """Update user in Firebase"""
        try:
            import firebase_admin
            from firebase_admin import auth
            
            # Prepare update parameters
            update_params = {}
            if 'email' in kwargs:
                update_params['email'] = kwargs['email']
            if 'password' in kwargs:
                update_params['password'] = kwargs['password']
            if 'display_name' in kwargs:
                update_params['display_name'] = kwargs['display_name']
            if 'email_verified' in kwargs:
                update_params['email_verified'] = kwargs['email_verified']
            if 'photo_url' in kwargs:
                update_params['photo_url'] = kwargs['photo_url']
            if 'disabled' in kwargs:
                update_params['disabled'] = kwargs['disabled']
            
            # Update user in Firebase
            user_record = auth.update_user(provider_id, **update_params)
            
            return AuthProviderUser(
                provider_id=user_record.uid,
                email=user_record.email,
                email_verified=user_record.email_verified,
                name=user_record.display_name,
                picture=user_record.photo_url,
                provider_name="firebase"
            )
            
        except Exception as e:
            logger.error(f"Firebase user update error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to update user: {str(e)}"
            )
    
    def delete_user(self, provider_id: str) -> bool:
        """Delete user from Firebase"""
        try:
            import firebase_admin
            from firebase_admin import auth
            
            auth.delete_user(provider_id)
            logger.info(f"Deleted Firebase user: {provider_id}")
            return True
            
        except Exception as e:
            logger.error(f"Firebase user deletion error: {str(e)}")
            return False
    
    def get_provider_name(self) -> str:
        return "firebase"