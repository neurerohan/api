"""
Simple in-memory caching system for the Nepali Data API.
"""
import time
from typing import Dict, Any, Callable, Optional, TypeVar
import logging
import functools

# Set up logging
logger = logging.getLogger(__name__)

# Type variable for return type
T = TypeVar('T')

# Global cache storage
_cache: Dict[str, Dict[str, Any]] = {}

def cache_response(ttl_seconds: int = 3600):
    """
    Decorator that caches function responses.
    
    Args:
        ttl_seconds: Time-to-live in seconds for cached responses (default: 1 hour)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cache_key = func.__qualname__
        
        if cache_key not in _cache:
            _cache[cache_key] = {}
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a key from the function arguments
            key_parts = [str(arg) for arg in args]
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            arg_key = ":".join(key_parts)
            
            # Check if result is in cache and still valid
            cache = _cache[cache_key]
            if arg_key in cache:
                result, timestamp = cache[arg_key]
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            # Call the function and cache the result
            result = await func(*args, **kwargs)
            cache[arg_key] = (result, time.time())
            logger.debug(f"Cache miss for {func.__name__}, cached new result")
            
            return result
        
        # Add method to invalidate cache for testing
        def invalidate_cache():
            """Clear the cache for this function"""
            if cache_key in _cache:
                _cache[cache_key].clear()
                logger.info(f"Cache invalidated for {func.__name__}")
        
        wrapper.invalidate_cache = invalidate_cache
        
        return wrapper
    
    return decorator

def clear_all_caches():
    """Clear all caches"""
    global _cache
    _cache = {}
    logger.info("All caches cleared")
