"""
Caching layer for improved performance and scalability.

Provides decorators and utilities for caching frequently accessed data.
Supports Redis (if configured) or in-memory caching as fallback.
"""

import json
import functools
from typing import Optional, Callable, Any
from datetime import timedelta

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import Redis, fallback to simple dict cache
try:
    import redis
    REDIS_AVAILABLE = bool(settings.REDIS_URL)
    if REDIS_AVAILABLE:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Redis caching enabled")
    else:
        redis_client = None
        logger.info("Redis URL not configured, using in-memory cache")
except ImportError:
    REDIS_AVAILABLE = False
    redis_client = None
    logger.warning("Redis not installed, using in-memory cache")

# Simple in-memory cache fallback
_memory_cache = {}


class CacheBackend:
    """Abstraction for cache operations (supports Redis or in-memory)."""

    @staticmethod
    def get(key: str) -> Optional[str]:
        """Get value from cache."""
        if redis_client:
            try:
                return redis_client.get(key)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return None
        else:
            return _memory_cache.get(key)

    @staticmethod
    def set(key: str, value: str, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 5 minutes)

        Returns:
            True if successful
        """
        if redis_client:
            try:
                return redis_client.setex(key, ttl, value)
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                return False
        else:
            _memory_cache[key] = value
            return True

    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache."""
        if redis_client:
            try:
                return redis_client.delete(key) > 0
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
                return False
        else:
            if key in _memory_cache:
                del _memory_cache[key]
                return True
            return False

    @staticmethod
    def clear_pattern(pattern: str) -> int:
        """Clear all keys matching pattern (Redis only)."""
        if redis_client:
            try:
                keys = redis_client.keys(pattern)
                if keys:
                    return redis_client.delete(*keys)
                return 0
            except Exception as e:
                logger.error(f"Redis clear pattern error: {e}")
                return 0
        else:
            # For memory cache, clear matching keys
            keys_to_delete = [k for k in _memory_cache.keys() if pattern.replace('*', '') in k]
            for key in keys_to_delete:
                del _memory_cache[key]
            return len(keys_to_delete)


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.

    Usage:
        @cached(ttl=600, key_prefix="company")
        def get_company(company_id: int):
            return db.query(Company).filter(Company.id == company_id).first()

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            cache_key_parts = [key_prefix or func.__name__]

            # Add positional args to key
            for arg in args:
                if isinstance(arg, (int, str, bool)):
                    cache_key_parts.append(str(arg))

            # Add keyword args to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (int, str, bool, type(None))):
                    cache_key_parts.append(f"{k}={v}")

            cache_key = ":".join(cache_key_parts)

            # Try to get from cache
            cached_value = CacheBackend.get(cache_key)
            if cached_value is not None:
                try:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    logger.warning(f"Cache decode error for key: {cache_key}")

            # Cache miss - call function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)

            # Store in cache
            try:
                # Convert result to JSON (for SQLAlchemy models, use schema)
                if hasattr(result, '__dict__'):
                    # For model instances, you should use Pydantic schemas
                    logger.warning(f"Caching ORM model directly - consider using schemas")
                cache_value = json.dumps(result, default=str)
                CacheBackend.set(cache_key, cache_value, ttl)
            except (TypeError, ValueError) as e:
                logger.warning(f"Could not cache result for {cache_key}: {e}")

            return result

        # Add cache invalidation method
        wrapper.invalidate = lambda *args, **kwargs: CacheBackend.delete(
            ":".join([key_prefix or func.__name__] + [str(a) for a in args if isinstance(a, (int, str, bool))])
        )

        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate all cache keys matching pattern.

    Usage:
        invalidate_cache_pattern("company:*")  # Clear all company caches

    Args:
        pattern: Pattern to match (e.g., "company:*")

    Returns:
        Number of keys deleted
    """
    count = CacheBackend.clear_pattern(pattern)
    logger.info(f"Invalidated {count} cache keys matching: {pattern}")
    return count
