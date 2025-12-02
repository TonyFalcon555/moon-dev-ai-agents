"""
Tests for the Redis-backed rate limiter
"""

import pytest
import time
from unittest.mock import MagicMock, patch

# Import the rate limiter
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.services.api_gateway.rate_limiter import RateLimiter, RateLimitResult


class TestRateLimiterMemory:
    """Test in-memory fallback rate limiting"""
    
    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with no Redis connection"""
        with patch('src.services.api_gateway.rate_limiter.REDIS_AVAILABLE', False):
            return RateLimiter()
    
    def test_allows_requests_under_limit(self, limiter):
        """Should allow requests under the limit"""
        result = limiter.check_rate_limit("test_key", limit=10, window_seconds=60)
        
        assert result.allowed is True
        assert result.remaining == 9
        assert result.limit == 10
    
    def test_blocks_requests_over_limit(self, limiter):
        """Should block requests when limit exceeded"""
        key = "test_over_limit"
        limit = 5
        
        # Make requests up to limit
        for i in range(limit):
            result = limiter.check_rate_limit(key, limit=limit)
            assert result.allowed is True
        
        # Next request should be blocked
        result = limiter.check_rate_limit(key, limit=limit)
        assert result.allowed is False
        assert result.remaining == 0
    
    def test_different_keys_independent(self, limiter):
        """Different keys should have independent limits"""
        result1 = limiter.check_rate_limit("key1", limit=5)
        result2 = limiter.check_rate_limit("key2", limit=5)
        
        assert result1.allowed is True
        assert result2.allowed is True
        assert result1.remaining == 4
        assert result2.remaining == 4
    
    def test_get_usage(self, limiter):
        """Should return current usage count"""
        key = "usage_test"
        
        for _ in range(3):
            limiter.check_rate_limit(key, limit=10)
        
        usage = limiter.get_usage(key)
        assert usage == 3
    
    def test_reset(self, limiter):
        """Reset should clear usage for a key"""
        key = "reset_test"
        
        for _ in range(5):
            limiter.check_rate_limit(key, limit=10)
        
        limiter.reset(key)
        usage = limiter.get_usage(key)
        assert usage == 0


class TestRateLimiterRedis:
    """Test Redis-backed rate limiting"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client"""
        mock = MagicMock()
        mock.ping.return_value = True
        return mock
    
    @pytest.fixture
    def limiter_with_redis(self, mock_redis):
        """Create a rate limiter with mocked Redis"""
        with patch('src.services.api_gateway.rate_limiter.REDIS_AVAILABLE', True):
            with patch('src.services.api_gateway.rate_limiter.redis') as mock_redis_module:
                mock_redis_module.from_url.return_value = mock_redis
                limiter = RateLimiter(redis_url="redis://localhost:6379/0")
                limiter._redis = mock_redis
                return limiter
    
    def test_redis_pipeline_used(self, limiter_with_redis, mock_redis):
        """Should use Redis pipeline for atomic operations"""
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [None, 0, None, None]
        mock_redis.pipeline.return_value = mock_pipe
        
        result = limiter_with_redis.check_rate_limit("test", limit=10)
        
        mock_redis.pipeline.assert_called_once()
        mock_pipe.execute.assert_called_once()
    
    def test_falls_back_on_redis_error(self, limiter_with_redis, mock_redis):
        """Should fall back to memory on Redis errors"""
        mock_redis.pipeline.side_effect = Exception("Redis error")
        
        result = limiter_with_redis.check_rate_limit("test", limit=10)
        
        # Should still return a result using memory fallback
        assert result is not None
        assert isinstance(result, RateLimitResult)


class TestRateLimitResult:
    """Test RateLimitResult dataclass"""
    
    def test_result_attributes(self):
        """Should have all expected attributes"""
        result = RateLimitResult(
            allowed=True,
            remaining=5,
            reset_in=30,
            limit=10
        )
        
        assert result.allowed is True
        assert result.remaining == 5
        assert result.reset_in == 30
        assert result.limit == 10
    
    def test_result_blocked(self):
        """Should represent blocked state correctly"""
        result = RateLimitResult(
            allowed=False,
            remaining=0,
            reset_in=45,
            limit=10
        )
        
        assert result.allowed is False
        assert result.remaining == 0
