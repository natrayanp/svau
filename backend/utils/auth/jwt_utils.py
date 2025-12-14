# utils/auth/jwt_utils.py
import jwt
import datetime
import secrets
import hashlib
import uuid
import os
import logging
import json
import ipaddress
from typing import Dict, Any, Optional, Tuple

from fastapi import HTTPException, status, Request
from datetime import timedelta

from .token_storage import PostgreSQLStorage, RedisStorage, TokenStorage

logger = logging.getLogger(__name__)


class SecureJWTManager:
    """Enhanced JWT manager with configurable storage"""

    def __init__(self, db_manager=None, storage: Optional[TokenStorage] = None):
        # Security configurations
        self.secret_key = self._get_secure_secret()
        self.algorithm = os.getenv("JWT_ALGORITHM", "HS256")

        # Token lifetimes
        self.access_token_ttl = int(os.getenv("JWT_ACCESS_TTL", "300"))
        self.refresh_token_ttl = int(os.getenv("JWT_REFRESH_TTL", "86400"))

        # Security claims
        self.issuer = os.getenv("JWT_ISSUER", "your-app")
        self.audience = os.getenv("JWT_AUDIENCE", "your-app-api")

        # Initialize storage backend
        self.storage = storage or self._init_storage(db_manager)

        logger.info(
            f"🔐 Secure JWT Manager initialized with storage backend: "
            f"{type(self.storage).__name__}"
        )

    def _init_storage(self, db_manager):
        """Initialize storage based on configuration"""
        storage_backend = os.getenv("TOKEN_STORAGE_BACKEND", "postgresql").lower()

        if storage_backend == "redis":
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                raise ValueError("REDIS_URL must be set for Redis storage")
            return RedisStorage(redis_url)
        elif storage_backend == "postgresql":
            if not db_manager:
                raise ValueError("Database manager required for PostgreSQL storage")
            return PostgreSQLStorage(db_manager)
        else:
            raise ValueError(f"Unsupported storage backend: {storage_backend}")

    def _get_secure_secret(self) -> str:
        """Get or generate cryptographically secure secret"""
        # Implement your secure secret retrieval (env, KMS, etc.)
        secret = os.getenv("JWT_SECRET_KEY")
        if not secret:
            # In production, you'd likely fail fast instead of generating
            secret = secrets.token_urlsafe(64)
            logger.warning(
                "JWT_SECRET_KEY not set; generated ephemeral secret. "
                "All tokens will be invalid on restart."
            )
        return secret

    def _generate_jti(self) -> str:
        """Generate unique JWT ID"""
        return str(uuid.uuid4())

    def _create_device_fingerprint(self, request: Request) -> str:
        """Create unique device fingerprint (example implementation)"""
        user_agent = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else "unknown"
        raw = f"{user_agent}|{ip}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def create_access_token(
        self,
        user_data: Dict[str, Any],
        request: Request,
        refresh_jti: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create secure access token with device binding"""
        jti = self._generate_jti()
        device_fp = self._create_device_fingerprint(request)
        client_ip = request.client.host if request.client else "unknown"

        now = datetime.datetime.utcnow()
        expire = now + timedelta(seconds=self.access_token_ttl)

        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(user_data.get("id")),
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": jti,
            "type": "access",
            "user_id": user_data.get("id"),
            "email": user_data.get("email"),
            "role": user_data.get("role"),
            "device_fp": device_fp,
            "client_ip": client_ip,
            "refresh_jti": refresh_jti,
            "version": "1.0",
        }

        access_token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        # Track device in storage; treat failure as fatal for issuance
        device_tracked = await self.storage.track_device(
            user_id=str(user_data.get("id")),
            device_fp=device_fp,
            expires_in=self.refresh_token_ttl,
            metadata={
                "ip": client_ip,
                "user_agent": request.headers.get("user-agent"),
                "last_seen": now.isoformat(),
            },
        )

        if not device_tracked:
            logger.error("Failed to track device during access token creation")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed",
            )

        return access_token, jti

    async def create_refresh_token(
        self,
        user_data: Dict[str, Any],
        request: Request,
    ) -> Tuple[str, str]:
        """Create secure refresh token"""
        jti = self._generate_jti()
        device_fp = self._create_device_fingerprint(request)

        now = datetime.datetime.utcnow()
        expire = now + timedelta(seconds=self.refresh_token_ttl)

        claims = {
            "iss": self.issuer,
            "aud": self.audience,
            "sub": str(user_data.get("id")),
            "exp": expire,
            "iat": now,
            "nbf": now,
            "jti": jti,
            "type": "refresh",
            "user_id": user_data.get("id"),
            "device_fp": device_fp,
            "client_ip": request.client.host if request.client else "unknown",
            "version": "1.0",
        }

        refresh_token = jwt.encode(claims, self.secret_key, algorithm=self.algorithm)

        stored = await self.storage.store_refresh_token(
            jti=jti,
            user_id=str(user_data.get("id")),
            device_fp=device_fp,
            expires_in=self.refresh_token_ttl,
            metadata={
                "created_at": now.isoformat(),
                "expires_at": expire.isoformat(),
                "valid": True,
            },
        )

        if not stored:
            logger.error("Failed to persist refresh token")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed",
            )

        return refresh_token, jti

    async def verify_token(
        self,
        token: str,
        request: Request,
        token_type: str = "access",
    ) -> Dict[str, Any]:
        """Verify token with multiple security checks"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": ["exp", "iat", "nbf", "iss", "aud", "jti", "type"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )

            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Expected {token_type}",
                )

            # Blacklist check (fail closed if storage fails)
            if await self.storage.is_token_blacklisted(payload.get("jti")):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                )

            # Access tokens: enforce link to a valid refresh token if refresh_jti exists
            if token_type == "access":
                refresh_jti = payload.get("refresh_jti")
                if refresh_jti:
                    refresh_data = await self.storage.get_refresh_token(refresh_jti)
                    if not refresh_data:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token no longer valid",
                        )

            # Device fingerprint validation
            current_device_fp = self._create_device_fingerprint(request)
            token_device_fp = payload.get("device_fp")

            if token_device_fp and token_device_fp != current_device_fp:
                logger.warning(
                    "Device fingerprint mismatch for user %s",
                    payload.get("user_id"),
                )

                devices = await self.storage.get_user_devices(payload.get("user_id"))
                device_fps = [d["device_fp"] for d in devices]

                if token_device_fp not in device_fps:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Device authorization changed",
                    )

                # We do NOT update payload["device_fp"] persistently here.
                # Caller can decide how to handle drift.

            # IP validation (optional)
            if os.getenv("ENABLE_IP_VALIDATION", "false").lower() == "true":
                token_ip = payload.get("client_ip")
                current_ip = request.client.host if request.client else None

                if token_ip and current_ip and token_ip != current_ip:
                    if not self._is_ip_change_allowed(token_ip, current_ip):
                        logger.warning(
                            "IP address changed for user %s: %s -> %s",
                            payload.get("user_id"),
                            token_ip,
                            current_ip,
                        )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid token: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception("Token verification error")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token verification failed",
            )

    def _is_ip_change_allowed(self, old_ip: str, new_ip: str) -> bool:
        """Check if IP change is within acceptable range (example)"""
        try:
            old_net = ipaddress.ip_network(old_ip + "/24", strict=False)
            new_addr = ipaddress.ip_address(new_ip)
            return new_addr in old_net
        except Exception:
            # If parsing fails, be conservative: treat change as not allowed
            return False

    async def blacklist_token(
        self,
        jti: str,
        user_id: str,
        expiry_seconds: int = 300,
    ) -> bool:
        """Add token to blacklist"""
        return await self.storage.blacklist_token(jti, user_id, expiry_seconds)

    async def revoke_user_tokens(self, user_id: str) -> bool:
        """Revoke all tokens for a user"""
        return await self.storage.revoke_user_tokens(user_id)

    async def revoke_device(self, user_id: str, device_fp: str) -> bool:
        """Revoke specific device"""
        return await self.storage.revoke_device(user_id, device_fp)

    async def get_user_devices(self, user_id: str) -> list:
        """Get list of authorized devices for user"""
        return await self.storage.get_user_devices(user_id)

    async def cleanup_expired_tokens(self) -> bool:
        """Cleanup expired tokens from storage"""
        return await self.storage.cleanup_expired()


# Global instance - initialized with database in main app
jwt_manager: Optional[SecureJWTManager] = None


def init_jwt_manager(db_manager, storage: Optional[TokenStorage] = None):
    """Initialize JWT manager with database or custom storage"""
    global jwt_manager
    jwt_manager = SecureJWTManager(db_manager=db_manager, storage=storage)
    return jwt_manager


def get_jwt_manager() -> SecureJWTManager:
    """Get JWT manager instance"""
    if jwt_manager is None:
        raise RuntimeError("JWT Manager not initialized")
    return jwt_manager
