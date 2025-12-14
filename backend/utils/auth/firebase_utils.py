# utils/auth/firebase_utils.py

import firebase_admin
from firebase_admin import auth, credentials, exceptions
from fastapi import HTTPException, status
import os
import logging

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self):
        self.use_emulator = os.getenv("FIREBASE_EMULATOR_HOST") is not None
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            if self.use_emulator:
                # Initialize with dummy credentials for emulator
                try:
                    firebase_admin.initialize_app(options={
                        "projectId": os.getenv("FIREBASE_PROJECT_ID", "local-svelte-app"),
                    })
                    logger.info("✅ Firebase Admin initialized for Emulator")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Firebase emulator: {str(e)}")
                    raise
            else:
                # Real Firebase production
                try:
                    cred_dict = {
                        "type": "service_account",
                        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
                        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                    
                    # Validate required fields
                    if not cred_dict["private_key"] or not cred_dict["project_id"]:
                        logger.error("Missing Firebase credentials")
                        raise ValueError("Firebase credentials not configured")
                    
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase Admin initialized for Production")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Firebase: {str(e)}")
                    raise

    def verify_firebase_token(self, firebase_token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            decoded_token = auth.verify_id_token(firebase_token)
            
            return {
                "uid": decoded_token["uid"],
                "email": decoded_token.get("email", ""),
                "email_verified": decoded_token.get("email_verified", False),
                "display_name": decoded_token.get("name", ""),
                "picture": decoded_token.get("picture", ""),
                "phone_number": decoded_token.get("phone_number", "")
            }
            
        except exceptions.FirebaseError as e:
            logger.warning(f"Firebase token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        except ValueError as e:
            logger.warning(f"Invalid token format: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token format"
            )
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )

# Global Firebase manager instance
firebase_manager = FirebaseManager()