"""
infra.redis 包的初始化模块

统一导出 Redis 相关组件，方便外部使用:
    from infra.redis import get_redis, init_pool, close_pool
    from infra.redis import get_pool_stats, check_redis_health
"""

from infra.redis.client import close_pool, get_pool, get_redis, init_pool
from infra.redis.monitor import check_redis_health, get_pool_stats

__all__ = [
    "init_pool",
    "close_pool",
    "get_redis",
    "get_pool",
    "get_pool_stats",
    "check_redis_health",
]
