"""Caching utilities for performance optimization.

This module provides:
- In-memory caching for frequently accessed data
- Cache expiration and invalidation
- Static data caching for API responses
"""

import asyncio
import hashlib
import json
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

# Cache storage
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = asyncio.Lock()

T = TypeVar("T")


class CacheConfig:
    """Configuration for caching behavior."""

    # Default TTL in seconds
    DEFAULT_TTL = 300  # 5 minutes

    # Cache TTLs for different data types
    PROMPT_LIST_TTL = 60  # 1 minute (prompts change frequently during editing)
    CONFIG_LIST_TTL = 300  # 5 minutes (configs change less frequently)
    RUN_LIST_TTL = 30  # 30 seconds (runs change frequently during execution)
    DOCUMENT_LIST_TTL = 600  # 10 minutes (documents change rarely)
    STATIC_DATA_TTL = 3600  # 1 hour (static data rarely changes)


async def get_cached(key: str, namespace: str = "default") -> Optional[Any]:
    """Get value from cache if it exists and hasn't expired.

    Args:
        key: Cache key
        namespace: Cache namespace for organization

    Returns:
        Cached value or None if not found/expired
    """
    async with _cache_lock:
        ns = _cache.get(namespace, {})
        entry = ns.get(key)

        if entry is None:
            return None

        # Check expiration
        if entry.get("expires_at", 0) < time.time():
            # Expired - remove from cache
            ns.pop(key, None)
            return None

        return entry.get("value")


async def set_cached(
    key: str, value: Any, ttl: int = CacheConfig.DEFAULT_TTL, namespace: str = "default"
) -> None:
    """Set value in cache with TTL.

    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
        namespace: Cache namespace for organization
    """
    async with _cache_lock:
        if namespace not in _cache:
            _cache[namespace] = {}

        _cache[namespace][key] = {
            "value": value,
            "expires_at": time.time() + ttl,
            "created_at": time.time(),
        }


async def invalidate_cache(key: str, namespace: str = "default") -> None:
    """Remove specific key from cache.

    Args:
        key: Cache key to invalidate
        namespace: Cache namespace
    """
    async with _cache_lock:
        ns = _cache.get(namespace, {})
        ns.pop(key, None)


async def invalidate_namespace(namespace: str) -> None:
    """Remove all entries from a namespace.

    Args:
        namespace: Cache namespace to clear
    """
    async with _cache_lock:
        _cache.pop(namespace, None)


async def clear_cache() -> None:
    """Clear all cached data."""
    async with _cache_lock:
        _cache.clear()


def cache_result(
    ttl: int = CacheConfig.DEFAULT_TTL,
    namespace: str = "default",
    key_func: Optional[Callable] = None,
):
    """Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        namespace: Cache namespace
        key_func: Optional function to generate cache key from arguments

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()

            # Try to get from cache
            cached = await get_cached(cache_key, namespace)
            if cached is not None:
                return cached

            # Call function and cache result
            result = await func(*args, **kwargs)
            await set_cached(cache_key, result, ttl, namespace)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # For sync functions, use simple dict-based cache
            if not hasattr(func, "_cache"):
                func._cache = {}
                func._cache_expiry = {}

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()

            # Check cache
            now = time.time()
            if cache_key in func._cache and func._cache_expiry.get(cache_key, 0) > now:
                return func._cache[cache_key]

            # Call and cache
            result = func(*args, **kwargs)
            func._cache[cache_key] = result
            func._cache_expiry[cache_key] = now + ttl
            return result

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Helper function to generate cache key for pagination
def paginated_cache_key(prefix: str, page: int, page_size: int, **filters) -> str:
    """Generate cache key for paginated results.

    Args:
        prefix: Key prefix (e.g., 'prompts', 'configs')
        page: Page number
        page_size: Items per page
        **filters: Additional filter parameters

    Returns:
        Cache key string
    """
    key_parts = [prefix, f"page={page}", f"size={page_size}"]
    if filters:
        key_parts.append(json.dumps(filters, sort_keys=True))
    return hashlib.md5("|".join(key_parts).encode()).hexdigest()


# Cache statistics
async def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    async with _cache_lock:
        stats = {"namespaces": {}, "total_entries": 0, "total_size_bytes": 0}

        for namespace, entries in _cache.items():
            ns_stats = {
                "entries": len(entries),
                "expired": sum(
                    1 for e in entries.values() if e.get("expires_at", 0) < time.time()
                ),
            }
            stats["namespaces"][namespace] = ns_stats
            stats["total_entries"] += ns_stats["entries"]

        # Rough estimate of memory usage
        stats["total_size_bytes"] = len(json.dumps(_cache).encode())

        return stats
