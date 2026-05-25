"""
arq 任务提交模块

提供任务提交、状态查询、结果获取、取消任务等接口。
FastAPI 路由中通过此模块与 arq 队列交互。

使用方式:
    from infra.queue import enqueue_task, get_job_status
    job_id = await enqueue_task(example_task, message="hello")
    status = await get_job_status(job_id)
"""

import asyncio
from typing import Any, Callable

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from config import logger
from config.env import settings
from infra.queue.settings import _build_redis_settings


# ============================================================
# arq Redis 连接池
# 与 redis-py 的 ConnectionPool 独立管理
# arq 自己维护连接池，用于提交任务和查询状态
# ============================================================
_pool: ArqRedis | None = None


async def _get_pool() -> ArqRedis:
    """
    获取 arq Redis 连接池

    首次调用时创建连接池并缓存，后续复用。
    使用 arq 自己的 create_pool，与 WorkerSettings 中的 redis_settings 一致。

    返回:
        ArqRedis: arq 异步 Redis 客户端
    """
    global _pool
    if _pool is None:
        _pool = await create_pool(_build_redis_settings())
        logger.info("arq 连接池初始化完成")
    return _pool


async def close_pool() -> None:
    """
    关闭 arq 连接池

    FastAPI shutdown 时调用，释放连接资源。
    """
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("arq 连接池已关闭")


async def enqueue_task(
    func: Callable,
    *args,
    _queue: str = 'arq:agent:queue',
    _job_timeout: int = 300,
    _max_tries: int = 3,
    _retry_delay: int = 60,
    _defer_by: int = 0,
    _depends_on: str = None,
    **kwargs,
) -> str:
    """
    提交任务到队列

    将任务函数和参数序列化后推入 Redis 队列，等待 Worker 消费执行。

    参数:
        func (Callable): 任务函数，如 example_task
        *args: 位置参数
        _queue (str): 队列名，默认 arq:agent:queue
        _job_timeout (int): 任务执行超时（秒），默认 300
        _max_tries (int): 最大重试次数，默认 3
        _retry_delay (int): 重试间隔（秒），默认 60
        _defer_by (int): 延迟执行（秒），默认 0（立即执行）
        _depends_on (str): 依赖的任务 ID，该任务完成后才执行
        **kwargs: 关键字参数

    返回:
        str: 任务 ID，用于查询状态和结果

    示例:
        job_id = await enqueue_task(example_task, message="hello")
        job_id = await enqueue_task(
            example_task,
            message="delayed",
            _defer_by=60,  # 60 秒后执行
        )
    """
    pool = await _get_pool()

    # arq 的 enqueue_job 是 ArqRedis 实例的方法
    # 通过 pool.enqueue_job() 提交任务
    # 返回 Job 对象，需要提取 job_id 字符串
    job = await pool.enqueue_job(
        func,
        *args,
        queue=_queue,
        _job_timeout=_job_timeout,
        _max_tries=_max_tries,
        _retry_delay=_retry_delay,
        _defer_by=_defer_by,
        _depends_on=_depends_on,
        _queue_name='arq:agent:queue',
        **kwargs,
    )

    # 提取字符串格式的 job_id
    job_id = job.job_id if job else None

    logger.info(
        f"任务已提交 | job_id={job_id} function={func.__name__} "
        f"queue={_queue} timeout={_job_timeout}"
    )

    return job_id


async def get_job_status(job_id: str) -> dict:
    """
    查询任务状态

    从 Redis 中读取任务元信息，返回当前状态。

    参数:
        job_id (str): 任务 ID

    返回:
        dict: 任务状态信息:
            - job_id: 任务 ID
            - status: 状态（queued/in_progress/completed/failed/deferred/not_found）
            - result: 任务结果（仅 completed 状态）
    """
    pool = await _get_pool()

    # arq 的 Job 类封装了任务状态查询
    from arq.jobs import Job

    # 创建 Job 实例，_queue_name 使用 arq 默认队列名
    job = Job(job_id, pool, _queue_name='arq:agent:queue')

    try:
        status = await job.status()
    except Exception:
        status = 'not_found'

    result = None
    if status == 'complete':
        try:
            result = await job.result()
        except Exception:
            pass

    return {
        "job_id": job_id,
        "status": status,
        "result": result,
    }


async def get_job_result(job_id: str) -> Any:
    """
    获取任务执行结果

    从 Redis 中读取任务返回值。仅任务完成后有效。

    参数:
        job_id (str): 任务 ID

    返回:
        Any: 任务返回值，任务未完成或失败时返回 None
    """
    pool = await _get_pool()

    from arq.jobs import Job

    job = Job(job_id, pool, queue_name='arq:agent:queue')

    try:
        status = await job.status()
        if status == 'complete':
            return await job.result()
        return None
    except Exception as e:
        logger.warning(f"获取任务结果失败: job_id={job_id} error={e}")
        return None


async def cancel_job(job_id: str) -> bool:
    """
    取消任务

    将任务从队列中移除，阻止其执行。
    如果任务正在执行中，无法取消。

    参数:
        job_id (str): 任务 ID

    返回:
        bool: 是否成功取消
    """
    pool = await _get_pool()

    from arq.jobs import Job

    job = Job(job_id, pool, queue_name='arq:agent:queue')

    try:
        await job.abort()
        logger.info(f"任务已取消: job_id={job_id}")
        return True
    except Exception as e:
        logger.warning(f"取消任务失败: job_id={job_id} error={e}")
        return False


async def get_queue_length() -> int:
    """
    获取队列中待执行的任务数量

    arq 使用 Redis Sorted Set 存储队列，用 ZCARD 获取长度。

    返回:
        int: 队列长度
    """
    pool = await _get_pool()

    # arq 的队列是 sorted set，用 zcard 获取元素数量
    length = await pool.zcard('arq:agent:queue')
    return length or 0
