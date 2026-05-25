"""
Redis 连接池监控模块

提供连接池运行时状态的读取能力，用于健康检查接口和问题排查。

核心功能:
- get_pool_stats(): 读取连接池各项指标
- check_redis_health(): Redis 健康状态综合检查

使用方式:
    from infra.redis.monitor import get_pool_stats, check_redis_health
    stats = get_pool_stats()
    health = await check_redis_health()
"""

from config import logger
from config.env import settings
from infra.redis.client import get_pool, get_redis


def get_pool_stats() -> dict:
    """
    获取 Redis 连接池实时状态

    通过读取 ConnectionPool 内部属性计算各项指标。
    这些属性在 redis-py 中是可靠的，但属于内部 API，
    如果 redis-py 大版本升级可能需要适配。

    返回:
        dict: 连接池状态字典，结构如下:
            - created (int): 已创建的 TCP 连接总数
            - in_use (int): 正在被占用的连接数
            - idle (int): 空闲可用的连接数
            - max (int): 连接池上限
    """
    pool = get_pool()
    if pool is None:
        return {
            "created": 0,
            "in_use": 0,
            "idle": 0,
            "max": 50,
            "status": "not_initialized",
        }

    # _available_connections: deque 类型，存放空闲连接
    # _in_use_connections: dict 类型，key 为连接 ID，存放正在使用的连接
    # 两个集合的总和就是已创建的 TCP 连接总数
    idle = len(pool._available_connections)
    in_use = len(pool._in_use_connections)
    created = idle + in_use

    return {
        "created": created,
        "in_use": in_use,
        "idle": idle,
        "max": 50,
        "status": "ok",
    }


async def check_redis_health() -> dict:
    """
    Redis 服务健康状态综合检查

    验证连接池状态 + PING 响应时间，用于 /health 接口。

    返回:
        dict: 健康检查结果:
            - pool (dict): 连接池状态（同 get_pool_stats）
            - ping_ms (float): PING 响应毫秒数，-1 表示失败
            - ok (bool): 综合健康状态
    """
    import time

    stats = get_pool_stats()

    # PING 探活：计算往返时间
    try:
        client = get_redis()
        start = time.monotonic()
        await client.ping()
        ping_ms = round((time.monotonic() - start) * 1000, 2)
    except Exception as e:
        # 连接失败时返回错误信息，不抛异常
        logger.error(f"Redis PING 失败: {e}")
        stats["status"] = "connection_error"
        return {
            "pool": stats,
            "ping_ms": -1,
            "ok": False,
            "error": str(e),
        }

    return {
        "pool": stats,
        "ping_ms": ping_ms,
        "ok": stats["status"] == "ok",
    }
