"""
arq Worker 配置模块

定义 WorkerSettings 类，包含连接池、超时、重试、限流等全部配置。
arq 通过此配置启动 Worker 进程。

使用方式:
    arq infra.queue.settings.WorkerSettings
"""

from arq import cron
from arq.connections import RedisSettings
from config.env import settings


def _build_redis_settings() -> RedisSettings:
    """
    构建 arq 专用的 Redis 连接配置

    arq 有自己的 RedisSettings 类，与 redis-py 的连接池参数分开管理。
    通过 .env 中的 REDIS_* 变量统一配置。

    返回:
        RedisSettings: arq 连接配置实例
    """
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        # --- 连接超时 ---
        # 连接 Redis 的最大等待时间（秒）
        conn_timeout=5,
        # 连接重试次数
        conn_retries=5,
        # 重试间隔（秒）
        conn_retry_delay=1,
        # TCP keepalive，检测对端是否断开
        # socket_keepalive 不是 RedisSettings 的参数，arq 内部处理
        # 超时时自动重试
        retry_on_timeout=True,
    )


class WorkerSettings:
    """
    arq Worker 配置类

    arq 启动时加载此类，读取所有配置项。
    Worker 进程根据此配置连接 Redis、消费任务、管理并发。
    """

    # ============================================================
    # Redis 连接配置
    # 使用 .env 中的统一配置构建
    # ============================================================
    redis_settings = _build_redis_settings()

    # ============================================================
    # 队列名称配置
    # 不同用途的任务可以分到不同队列
    # ============================================================
    queue_name = 'arq:agent:queue'
    default_queue_name = 'arq:agent:queue'

    # ============================================================
    # 任务超时配置
    # ============================================================
    # 单个任务最大执行时间（秒）
    # 超时后 Worker 会强制终止任务，标记为失败
    default_timeout = 300

    # 任务执行超时（与 default_timeout 作用相同，优先级更高）
    job_timeout = 300

    # ============================================================
    # 重试配置
    # ============================================================
    # 重试间隔（秒），任务失败后等待多久重试
    retry_delay = 60

    # 最大重试次数，超过此数任务标记为 DEAD（死信）
    max_tries = 3

    # ============================================================
    # 并发控制
    # ============================================================
    # 单个 Worker 最大同时执行的任务数
    # 每个 Worker 是独立进程，max_jobs 控制进程内并发
    max_jobs = 10

    # 并发信号量，限制同时执行的异步任务数量
    job_semaphore = 10

    # ============================================================
    # Worker 进程配置
    # ============================================================
    # Worker 名称，用于日志标识和健康检查
    worker_name = 'agent-worker'

    # 单次 burst 模式最大处理任务数（0=不限制）
    max_burst_jobs = 0

    # 是否 burst 模式
    # True: 队列空时 Worker 自动退出，适合一次性任务
    # False: 持续运行，适合常驻服务
    burst = False

    # ============================================================
    # 健康检查配置
    # ============================================================
    # Worker 向 Redis 写入心跳的间隔（秒）
    health_check_interval = 10

    # 健康检查键名，用于监控 Worker 存活状态
    health_check_key = 'arq:agent:health'

    # ============================================================
    # 密钥轮换配置
    # 用于任务结果加密的盐值，防止结果被伪造
    # ============================================================
    job_keys_salt = 'arq:agent:salt'

    # ============================================================
    # 中间件配置
    # 按顺序执行，任务执行前/后/异常时触发
    # ============================================================
    from infra.queue.middleware import JobMiddleware
    middleware = [JobMiddleware]

    # ============================================================
    # 任务函数注册
    # Worker 会自动发现并执行列表中的任务
    # 新增任务后必须在此注册，否则 Worker 无法识别
    # ============================================================
    from infra.queue.tasks import (
        example_task,
        process_message_task,
        send_notification_task,
        generate_report_task,
    )
    functions = [
        example_task,
        process_message_task,
        send_notification_task,
        generate_report_task,
    ]

    # ============================================================
    # Cron 定时任务（arq 内置）
    # 与 APScheduler 互补：arq cron 适合需要 Worker 执行的任务
    # ============================================================
    cron_jobs = [
        # 每 5 分钟清理过期结果缓存
        cron(
            'infra.queue.tasks.cleanup_expired_results',
            minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55},
        ),
    ]
