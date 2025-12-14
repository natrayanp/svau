# utils/auth/token_storage.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os
from utils.database.database import DatabaseManager, get_db, DatabaseError

logger = logging.getLogger(__name__)


class TokenStorage(ABC):
    """Abstract interface for token storage"""

    @abstractmethod
    async def blacklist_token(self, jti: str, user_id: str, expires_in: int) -> bool:
        """Add token to blacklist"""
        pass

    @abstractmethod
    async def is_token_blacklisted(self, jti: str) -> bool:
        """Check if token is blacklisted"""
        pass

    @abstractmethod
    async def store_refresh_token(
        self,
        jti: str,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        """Store refresh token metadata"""
        pass

    @abstractmethod
    async def get_refresh_token(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get refresh token metadata"""
        pass

    @abstractmethod
    async def revoke_user_tokens(self, user_id: str) -> bool:
        """Revoke all tokens for user (refresh + devices)"""
        pass

    @abstractmethod
    async def revoke_device(self, user_id: str, device_fp: str) -> bool:
        """Revoke specific device (tokens + device registration)"""
        pass

    @abstractmethod
    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's authorized devices"""
        pass

    @abstractmethod
    async def track_device(
        self,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        """Track authorized device"""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> bool:
        """Cleanup expired entries; return True on success"""
        pass


class PostgreSQLStorage(TokenStorage):
    """PostgreSQL implementation of token storage"""

    def __init__(self, db_manager):
        self.db = db_manager
        logger.info("✅ PostgreSQL token storage initialized")

    async def blacklist_token(self, jti: str, user_id: str, expires_in: int) -> bool:
        # Use parameterized interval arithmetic to avoid unsafe formatting
        query = """
            INSERT INTO token_blacklist (jti, user_id, expires_at)
            VALUES (%s, %s, NOW() + (%s * INTERVAL '1 second'))
            ON CONFLICT (jti) DO NOTHING
        """
        try:
            await self.db.execute_update(query, (jti, user_id, expires_in))
            return True
        except Exception:
            logger.exception("Failed to blacklist token")
            return False

    async def is_token_blacklisted(self, jti: str) -> bool:
        query = "SELECT 1 FROM token_blacklist WHERE jti = %s AND expires_at > NOW()"
        try:
            result = await self.db.fetch_one(query, (jti,))
            return bool(result)
        except Exception:
            # Fail closed: if storage is unavailable, treat as blacklisted
            logger.exception("Failed to check if token is blacklisted")
            return True

    async def store_refresh_token(
        self,
        jti: str,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        # Store individual token
        token_query = """
            INSERT INTO refresh_tokens (jti, user_id, device_fp, expires_at, metadata)
            VALUES (%s, %s, %s, NOW() + (%s * INTERVAL '1 second'), %s)
            ON CONFLICT (jti) DO UPDATE SET expires_at = EXCLUDED.expires_at,
                                          metadata = EXCLUDED.metadata
        """

        # Add to user's active tokens list (limit number)
        user_tokens_query = """
            WITH current_tokens AS (
                SELECT jti FROM refresh_tokens 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            )
            DELETE FROM refresh_tokens 
            WHERE user_id = %s 
              AND jti NOT IN (SELECT jti FROM current_tokens)
        """

        try:
            await self.db.execute_update(
                token_query, (jti, user_id, device_fp, expires_in, metadata)
            )

            max_tokens = int(os.getenv("MAX_REFRESH_TOKENS", "5"))
            await self.db.execute_update(
                user_tokens_query, (user_id, max_tokens, user_id)
            )

            return True
        except Exception:
            logger.exception("Failed to store refresh token")
            return False

    async def get_refresh_token(self, jti: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT jti, user_id, device_fp, metadata
            FROM refresh_tokens 
            WHERE jti = %s AND expires_at > NOW()
        """
        try:
            result = await self.db.fetch_one(query, (jti,))
            return result
        except Exception:
            logger.exception("Failed to get refresh token")
            return None

    async def revoke_user_tokens(self, user_id: str) -> bool:
        try:
            # Blacklist all user's active refresh tokens
            blacklist_query = """
                INSERT INTO token_blacklist (jti, user_id, expires_at)
                SELECT jti, user_id, expires_at 
                FROM refresh_tokens 
                WHERE user_id = %s AND expires_at > NOW()
                ON CONFLICT (jti) DO NOTHING
            """
            await self.db.execute_update(blacklist_query, (user_id,))

            # Delete user's refresh tokens
            delete_tokens_query = "DELETE FROM refresh_tokens WHERE user_id = %s"
            await self.db.execute_update(delete_tokens_query, (user_id,))

            # Delete user's devices
            delete_devices_query = "DELETE FROM user_devices WHERE user_id = %s"
            await self.db.execute_update(delete_devices_query, (user_id,))

            return True
        except Exception:
            logger.exception("Failed to revoke user tokens")
            return False

    async def revoke_device(self, user_id: str, device_fp: str) -> bool:
        try:
            # Blacklist tokens from this device
            blacklist_query = """
                INSERT INTO token_blacklist (jti, user_id, expires_at)
                SELECT jti, user_id, expires_at 
                FROM refresh_tokens 
                WHERE user_id = %s AND device_fp = %s
                ON CONFLICT (jti) DO NOTHING
            """
            await self.db.execute_update(blacklist_query, (user_id, device_fp))

            # Delete device tokens
            delete_tokens_query = """
                DELETE FROM refresh_tokens 
                WHERE user_id = %s AND device_fp = %s
            """
            await self.db.execute_update(delete_tokens_query, (user_id, device_fp))

            # Delete device registration
            delete_device_query = """
                DELETE FROM user_devices 
                WHERE user_id = %s AND device_fp = %s
            """
            await self.db.execute_update(delete_device_query, (user_id, device_fp))

            return True
        except Exception:
            logger.exception("Failed to revoke device")
            return False

    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT device_fp, metadata, last_seen
            FROM user_devices 
            WHERE user_id = %s AND expires_at > NOW()
            ORDER BY last_seen DESC
        """
        try:
            results = await self.db.fetch_all(query, (user_id,))
            return results or []
        except Exception:
            logger.exception("Failed to get user devices")
            return []

    async def track_device(
        self,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        query = """
            INSERT INTO user_devices (user_id, device_fp, expires_at, metadata)
            VALUES (%s, %s, NOW() + (%s * INTERVAL '1 second'), %s)
            ON CONFLICT (user_id, device_fp) 
            DO UPDATE SET 
                expires_at = EXCLUDED.expires_at,
                metadata = EXCLUDED.metadata,
                last_seen = NOW()
        """
        try:
            await self.db.execute_update(query, (user_id, device_fp, expires_in, metadata))
            return True
        except Exception:
            logger.exception("Failed to track device")
            return False

    async def cleanup_expired(self) -> bool:
        """Cleanup expired tokens and devices; return True on success."""
        try:
            blacklist_query = "DELETE FROM token_blacklist WHERE expires_at <= NOW()"
            await self.db.execute_update(blacklist_query)

            token_query = "DELETE FROM refresh_tokens WHERE expires_at <= NOW()"
            await self.db.execute_update(token_query)

            device_query = "DELETE FROM user_devices WHERE expires_at <= NOW()"
            await self.db.execute_update(device_query)

            return True
        except Exception:
            logger.exception("Cleanup of expired tokens/devices failed")
            return False


# Redis implementation (for future use)
class RedisStorage(TokenStorage):
    """Redis implementation of token storage (partial)"""

    def __init__(self, redis_url: str):
        import redis

        self.client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
        )
        logger.info("✅ Redis token storage initialized")

    async def blacklist_token(self, jti: str, user_id: str, expires_in: int) -> bool:
        key = f"blacklist:{jti}"
        try:
            self.client.setex(key, expires_in, user_id)
            return True
        except Exception:
            logger.exception("Redis: Failed to blacklist token")
            return False

    async def is_token_blacklisted(self, jti: str) -> bool:
        try:
            return self.client.exists(f"blacklist:{jti}") > 0
        except Exception:
            logger.exception("Redis: Failed to check blacklist; failing closed")
            return True

    # The rest of the methods should be implemented to match PostgreSQL semantics
    async def store_refresh_token(
        self,
        jti: str,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        raise NotImplementedError("RedisStorage.store_refresh_token not implemented yet")

    async def get_refresh_token(self, jti: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("RedisStorage.get_refresh_token not implemented yet")

    async def revoke_user_tokens(self, user_id: str) -> bool:
        raise NotImplementedError("RedisStorage.revoke_user_tokens not implemented yet")

    async def revoke_device(self, user_id: str, device_fp: str) -> bool:
        raise NotImplementedError("RedisStorage.revoke_device not implemented yet")

    async def get_user_devices(self, user_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError("RedisStorage.get_user_devices not implemented yet")

    async def track_device(
        self,
        user_id: str,
        device_fp: str,
        expires_in: int,
        metadata: Dict[str, Any],
    ) -> bool:
        raise NotImplementedError("RedisStorage.track_device not implemented yet")

    async def cleanup_expired(self) -> bool:
        # For Redis, cleanup is mostly TTL-based; you can make this a no-op or housekeeping
        return True
