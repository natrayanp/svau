import firebase_admin
from firebase_admin import auth, credentials
from fastapi import HTTPException, status
import os

class FirebaseManager:
    def __init__(self):
        # Check if running against emulator
        use_emulator = os.getenv("FIREBASE_EMULATOR_HOST") is not None   
        print(use_emulator)             
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            if use_emulator:
                # Initialize with dummy credentials (emulator ignores real keys)
                '''
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID", "demo-project"),
                    "private_key_id": "dummy",
                    "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
                    "client_email": "dummy@demo-project.iam.gserviceaccount.com",
                    "client_id": "dummy",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy"
                })
                '''
                firebase_admin.initialize_app(options={
                    "projectId": os.getenv("FIREBASE_PROJECT_ID", "demo-project"),
                })
                print("Firebase Admin initialized for Emulator")

            else:
                # Real Firebase
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                })
                firebase_admin.initialize_app(cred)
                print("Firebase Admin initialized for Production")

    def verify_firebase_token(self, firebase_token: str) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            decoded_token = auth.verify_id_token(firebase_token)
            return {
                "uid": decoded_token["uid"],
                "email": decoded_token.get("email"),
                "email_verified": decoded_token.get("email_verified", False),
                "display_name": decoded_token.get("name"),
                "picture": decoded_token.get("picture")
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Firebase token: {str(e)}"
            )

# Global Firebase manager instance
firebase_manager = FirebaseManager()