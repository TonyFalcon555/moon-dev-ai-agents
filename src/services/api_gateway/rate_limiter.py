"""
🌙 Moon Dev's Redis-Backed Rate Limiter
Production-grade rate limiting with Redis persistence

Features:
- Sliding window rate limiting
- Redis persistence (survives restarts)
- Fallback to in-memory when Redis unavailable
- Per-key and per-plan limits
"""

import os
import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory rate limiting.")


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int
    reset_in: int
    limit: int


class RateLimiter:
    """
    Sliding window rate limiter with Redis backend.
    Falls back to in-memory if Redis is unavailable.
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self._redis: Optional[redis.Redis] = None
        self._memory_store: Dict[str, Dict] = {}
        self._connect_redis()
    
    def _connect_redis(self) -> None:
        """Attempt to connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.info("Redis package not available, using in-memory rate limiting")
            return
            
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self._redis.ping()
            logger.info("✅ Connected to Redis for rate limiting")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Using in-memory fallback.")
            self._redis = None
    
    def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int = 60
    ) -> RateLimitResult:
        """
        Check if a request should be allowed under rate limits.
        
        Args:
            key: Unique identifier (usually API key hash)
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds (default 60)
            
        Returns:
            RateLimitResult with allowed status and metadata
        """
        if self._redis:
            return self._check_redis(key, limit, window_seconds)
        return self._check_memory(key, limit, window_seconds)
    
    def _check_redis(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> RateLimitResult:
        """Redis-backed rate limit check using sliding window"""
        redis_key = f"ratelimit:{key}"
        now = time.time()
        window_start = now - window_seconds
        
        try:
            pipe = self._redis.pipeline()
            
            # Remove old entries outside window
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            
            # Set expiry on key
            pipe.expire(redis_key, window_seconds + 1)
            
            results = pipe.execute()
            current_count = results[1]
            
            remaining = max(0, limit - current_count - 1)
            reset_in = window_seconds
            
            if current_count >= limit:
                # Over limit - remove the request we just added
                self._redis.zrem(redis_key, str(now))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_in=reset_in,
                    limit=limit
                )
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_in=reset_in,
                limit=limit
            )
            
        except Exception as e:
            logger.error(f"Redis error: {e}. Falling back to memory.")
            self._redis = None
            return self._check_memory(key, limit, window_seconds)
    
    def _check_memory(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> RateLimitResult:
        """In-memory fallback rate limit check"""
        now = int(time.time())
        window = now // window_seconds
        
        if key not in self._memory_store:
            self._memory_store[key] = {"window": window, "count": 0}
        
        state = self._memory_store[key]
        
        # Reset if window changed
        if state["window"] != window:
            state["window"] = window
            state["count"] = 0
        
        reset_in = window_seconds - (now % window_seconds)
        
        if state["count"] >= limit:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in=reset_in,
                limit=limit
            )
        
        state["count"] += 1
        remaining = limit - state["count"]
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_in=reset_in,
            limit=limit
        )
    
    def get_usage(self, key: str, window_seconds: int = 60) -> int:
        """Get current usage count for a key"""
        if self._redis:
            try:
                redis_key = f"ratelimit:{key}"
                now = time.time()
                window_start = now - window_seconds
                return self._redis.zcount(redis_key, window_start, now)
            except Exception:
                pass
        
        state = self._memory_store.get(key, {})
        return state.get("count", 0)
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key (admin operation)"""
        if self._redis:
            try:
                self._redis.delete(f"ratelimit:{key}")
            except Exception:
                pass
        
        if key in self._memory_store:
            del self._memory_store[key]


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
