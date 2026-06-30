import json
import functools
import hashlib
from typing import Any, Callable
from loguru import logger
from fastapi.encoders import jsonable_encoder

def get_redis_client():
    from app.main import app
    return getattr(app.state, "redis", None)

def redis_cache(expire: int = 60):
    """
    Custom caching decorator that works with Upstash Redis and bypasses fastapi-cache2 bugs.
    It caches the synchronous or asynchronous function's return value in Redis.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            redis = get_redis_client()
            if not redis:
                return func(*args, **kwargs)

            # Generate cache key based on function name and arguments
            key_str = f"{func.__name__}:{args}:{kwargs}"
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            cache_key = f"cache:{func.__name__}:{key_hash}"

            import asyncio
            
            try:
                # Try to get from cache (must run inside asyncio event loop because redis is async)
                loop = asyncio.get_event_loop()
                cached_data = loop.run_until_complete(redis.get(cache_key))
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                pass

            # Execute function
            result = func(*args, **kwargs)

            try:
                # Save to cache
                serialized = json.dumps(jsonable_encoder(result))
                loop = asyncio.get_event_loop()
                loop.run_until_complete(redis.set(cache_key, serialized, ex=expire))
            except Exception as e:
                pass

            return result
        return sync_wrapper
    return decorator
