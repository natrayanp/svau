# utils/auth/firebase_utils.py

import firebase_admin
from firebase_admin import auth, credentials, exceptions
from fastapi import HTTPException, status
import os
import json
import logging
import jwt  # Add this import

logger = logging.getLogger(__name__)

class FirebaseManager:
    def __init__(self):
        self.use_emulator = os.getenv("FIREBASE_EMULATOR_HOST") is not None
        self.initialized = False
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            if self.use_emulator:
                # For emulator, we don't need real Firebase Admin initialization
                # Just set a flag
                logger.info("🔧 Firebase Emulator mode - skipping Admin SDK initialization")
                self.initialized = False
            else:
                # Real Firebase production - your existing code
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
                    
                    if not cred_dict["private_key"] or not cred_dict["project_id"]:
                        logger.error("Missing Firebase credentials")
                        # For emulator, don't raise error
                        if not self.use_emulator:
                            raise ValueError("Firebase credentials not configured")
                        else:
                            logger.info("No Firebase credentials in emulator mode - continuing")
                            return
                    
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred)
                    self.initialized = True
                    logger.info("✅ Firebase Admin initialized for Production")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Firebase: {str(e)}")
                    if not self.use_emulator:
                        raise
                    else:
                        logger.info("Continuing in emulator mode without Firebase Admin")

    def verify_firebase_token(self, firebase_token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            if self.use_emulator or not self.initialized:
                # For emulator or when Firebase Admin is not initialized,
                # decode the token without verification
                logger.info("🔧 Emulator mode - decoding token without verification")
                
                # Decode token without verification
                decoded_token = jwt.decode(
                    firebase_token, 
                    options={"verify_signature": False}
                )
                
                # Extract user info
                uid = (
                    decoded_token.get("user_id") or 
                    decoded_token.get("sub") or 
                    decoded_token.get("uid") or 
                    "mock-uid-" + decoded_token.get("email", "unknown").split("@")[0]
                )
                
                return {
                    "uid": uid,
                    "email": decoded_token.get("email", "user@example.com"),
                    "email_verified": decoded_token.get("email_verified", True),
                    "display_name": decoded_token.get("name", "Test User"),
                    "picture": decoded_token.get("picture", ""),
                    "phone_number": decoded_token.get("phone_number", "")
                }
            else:
                # Normal Firebase verification for production
                decoded_token = auth.verify_id_token(firebase_token)
                
                return {
                    "uid": decoded_token["uid"],
                    "email": decoded_token.get("email", ""),
                    "email_verified": decoded_token.get("email_verified", False),
                    "display_name": decoded_token.get("name", ""),
                    "picture": decoded_token.get("picture", ""),
                    "phone_number": decoded_token.get("phone_number", "")
                }
                
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
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
                detail=f"Authentication service error: {str(e)}"
            )

# Global Firebase manager instance
firebase_manager = FirebaseManager()