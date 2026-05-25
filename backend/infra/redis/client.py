"""
Redis 异步客户端模块

负责创建和管理全局唯一的 Redis 连接池与客户端实例。
所有模块通过此文件获取 Redis 客户端，避免重复创建连接。

核心组件:
- init_pool(): 初始化连接池 + 客户端（FastAPI startup 时调用）
- close_pool(): 优雅关闭连接池（FastAPI shutdown 时调用）
- get_redis(): 获取全局客户端实例（各业务模块调用）

运行方式:
    通常由 FastAPI lifespan 自动管理，不直接运行。
"""

from redis.asyncio import ConnectionPool, Redis

from config import logger
from config.env import settings

# ============================================================
# 全局连接池和客户端实例
# 在 init_pool() 中赋值，close_pool() 中置空
# 所有模块通过 get_redis() 获取同一个实例
# ============================================================
_pool: ConnectionPool | None = None
_client: Redis | None = None


def init_pool() -> Redis:
    """
    初始化 Redis 连接池并创建客户端实例

    连接池参数说明:
    - max_connections=50: 连接池上限，防止耗尽 Redis 服务端连接
    - timeout=5: 获取连接最大等待秒数，超时抛 ConnectionError
    - retry_on_timeout=True: 超时时自动重试
    - health_check_interval=30: 每 30 秒对空闲连接发 PING 探活，剔除死连接
    - socket_keepalive=True: 启用 TCP keepalive，检测对端是否断开
    - socket_connect_timeout=5: TCP 建连超时
    - socket_timeout=5: 读写超时，防止慢查询卡住连接

    返回:
        Redis: 初始化好的客户端实例
    """
    global _pool, _client

    # 如果已经初始化过，直接返回现有实例
    if _client is not None:
        logger.warning("Redis 连接池已初始化，跳过重复调用")
        return _client

    # 创建连接池
    # ConnectionPool 在首次调用时不会建立真实 TCP 连接
    # 实际连接按需创建，直到达到 max_connections 上限
    _pool = ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        db=settings.REDIS_DB,
        max_connections=50,
        # 以下参数通过 connection_kwargs 传给 Connection 类
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        socket_keepalive=True,
        socket_keepalive_options={
            6: 15,    # TCP_KEEPIDLE: 空闲 15 秒后开始探测
            5: 5,     # TCP_KEEPINTVL: 每 5 秒探测一次
            4: 3,     # TCP_KEEPCNT: 连续 3 次失败判定断开
        },
        retry_on_timeout=True,
        health_check_interval=30,
    )

    # 基于连接池创建客户端实例
    # 所有 Redis 操作都通过此实例发起
    _client = Redis(connection_pool=_pool)

    logger.info(
        f"Redis 连接池初始化完成 | "
        f"host={settings.REDIS_HOST}:{settings.REDIS_PORT} "
        f"max_connections=50 health_check=30s"
    )

    return _client


async def close_pool() -> None:
    """
    优雅关闭 Redis 连接池

    释放所有池中的 TCP 连接，清理全局实例。
    FastAPI shutdown 时调用，确保无连接泄漏。
    """
    global _pool, _client

    if _client is not None:
        # aclose() 是 async 上下文管理器的等价物
        # 会关闭底层所有 TCP 连接
        await _client.aclose()
        _client = None
        logger.info("Redis 客户端已关闭")

    if _pool is not None:
        # disconnect 断开连接池中所有空闲连接
        await _pool.disconnect()
        _pool = None
        logger.info("Redis 连接池已断开")


def get_redis() -> Redis:
    """
    获取全局 Redis 客户端实例

    所有业务模块通过此函数获取同一个客户端：
        from infra.redis import get_redis
        r = get_redis()
        await r.get("key")

    返回:
        Redis: 全局客户端实例

    异常:
        RuntimeError: 在 init_pool() 调用前调用此函数时抛出
    """
    if _client is None:
        raise RuntimeError(
            "Redis 客户端未初始化，请先调用 init_pool() "
            "（通常在 FastAPI lifespan startup 中）"
        )
    return _client


def get_pool() -> ConnectionPool | None:
    """
    获取当前连接池实例（供 monitor 模块读取状态）

    返回:
        ConnectionPool | None: 连接池实例，未初始化时返回 None
    """
    return _pool
