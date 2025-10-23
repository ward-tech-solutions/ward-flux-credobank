"""
Redis Caching Utilities
Provides caching layer for frequently accessed data
"""

import os
import json
import logging
import redis
from functools import wraps
from typing import Any, Optional, Callable
from datetime import timedelta

logger = logging.getLogger(__name__)

# Redis client singleton
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get or create Redis client singleton

    Returns:
        Redis client or None if connection fails
    """
    global _redis_client

    if _redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(
                redis_url,
                decode_responses=True,  # Auto-decode bytes to strings
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Redis cache client initialized: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis cache unavailable: {e} (caching disabled)")
            _redis_client = None

    return _redis_client


def cache_result(ttl_seconds: int = 60, key_prefix: str = ""):
    """
    Decorator to cache function results in Redis

    Args:
        ttl_seconds: Time to live in seconds (default 60)
        key_prefix: Optional prefix for cache keys

    Example:
        @cache_result(ttl_seconds=300, key_prefix="device")
        def get_device(device_id: str):
            return db.query(Device).filter_by(id=device_id).first()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            client = get_redis_client()

            # If Redis unavailable, skip caching
            if client is None:
                return func(*args, **kwargs)

            try:
                # Build cache key from function name and arguments
                # Skip first arg if it's a database session
                cache_args = args
                if args and hasattr(args[0], 'query'):  # Detect SQLAlchemy session
                    cache_args = args[1:]

                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(arg) for arg in cache_args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)

                # Try to get from cache
                cached = client.get(cache_key)
                if cached:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return json.loads(cached)

                # Cache miss - call function
                logger.debug(f"Cache MISS: {cache_key}")
                result = func(*args, **kwargs)

                # Store in cache
                try:
                    client.setex(
                        cache_key,
                        ttl_seconds,
                        json.dumps(result, default=str)  # Handle datetime serialization
                    )
                except (TypeError, ValueError) as e:
                    # If result not JSON-serializable, skip caching
                    logger.debug(f"Result not cacheable: {e}")

                return result

            except Exception as e:
                # On any cache error, fallback to uncached call
                logger.warning(f"Cache error for {func.__name__}: {e}")
                return func(*args, **kwargs)

        return wrapper
    return decorator


def invalidate_cache(pattern: str = "*"):
    """
    Invalidate cache entries matching pattern

    Args:
        pattern: Redis key pattern (e.g., "device:*", "monitoring_profile:*")

    Example:
        invalidate_cache("device:123")  # Invalidate specific device
        invalidate_cache("device:*")     # Invalidate all devices
    """
    client = get_redis_client()
    if client is None:
        return

    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache entries matching '{pattern}'")
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")


def cache_monitoring_profile(ttl_seconds: int = 300):
    """
    Cache decorator specifically for monitoring profile
    Longer TTL since it changes rarely

    Example:
        @cache_monitoring_profile()
        def get_active_profile(db):
            return db.query(MonitoringProfile).filter_by(is_active=True).first()
    """
    return cache_result(ttl_seconds=ttl_seconds, key_prefix="monitoring_profile")


def cache_alert_rules(ttl_seconds: int = 60):
    """
    Cache decorator for alert rules

    Example:
        @cache_alert_rules()
        def get_enabled_rules(db):
            return db.query(AlertRule).filter_by(enabled=True).all()
    """
    return cache_result(ttl_seconds=ttl_seconds, key_prefix="alert_rules")


def cache_device_list(ttl_seconds: int = 30):
    """
    Cache decorator for device lists
    Short TTL since device status changes frequently

    Example:
        @cache_device_list()
        def get_enabled_devices(db):
            return db.query(StandaloneDevice).filter_by(enabled=True).all()
    """
    return cache_result(ttl_seconds=ttl_seconds, key_prefix="devices")
