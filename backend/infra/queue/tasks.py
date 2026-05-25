"""
arq 任务函数定义

每个任务是一个 async 函数，接收 ctx 上下文 + 业务参数。
ctx 由 arq 框架注入，包含 job_id、job_try、enqueue_time 等元信息。

命名规范:
- 函数名即任务标识，必须与 settings.py 中 functions 列表一致
- 后缀 _task 区分于 APScheduler 的 jobs.py 中的函数
- 函数必须是 async 的（arq 要求）

使用方式:
    # 提交任务
    await enqueue_task(example_task, message="hello")

    # Worker 自动发现并执行
"""

import asyncio
import random

from config import logger
from config.env import settings


async def example_task(ctx, message: str = "hello") -> dict:
    """
    示例异步任务

    演示 arq 任务的基本结构。
    任务可以是任意耗时操作：API 调用、数据处理、文件生成等。

    参数:
        ctx (dict): arq 上下文，包含 job_id（任务ID）、job_try（当前第几次尝试）等
        message (str): 业务参数，由提交时传入

    返回:
        dict: 任务执行结果，存储在 Redis 中供查询
    """
    job_id = ctx.get("job_id", "unknown")
    job_try = ctx.get("job_try", 1)

    logger.info(
        f"[队列任务] 执行 example_task | "
        f"job_id={job_id} try={job_try} message={message}"
    )

    # 模拟异步耗时操作（实际项目中替换为真实业务逻辑）
    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "message": message,
        "processed_by": settings.WORKER_NAME if hasattr(settings, 'WORKER_NAME') else 'agent-worker',
    }


async def process_message_task(ctx, message_id: str, payload: dict = None) -> dict:
    """
    消息处理任务

    接收消息 ID，从存储中读取消息内容并处理。
    典型场景：用户提交的异步请求、Webhook 回调处理等。

    参数:
        ctx: arq 上下文
        message_id (str): 消息唯一标识
        payload (dict): 消息内容，可选

    返回:
        dict: 处理结果
    """
    job_id = ctx.get("job_id", "unknown")
    payload = payload or {}

    logger.info(
        f"[队列任务] 执行 process_message_task | "
        f"job_id={job_id} message_id={message_id}"
    )

    await asyncio.sleep(0.1)

    return {
        "status": "success",
        "message_id": message_id,
        "result": f"消息 {message_id} 处理完成",
    }


async def send_notification_task(ctx, user_id: str, content: str, channel: str = "email") -> dict:
    """
    发送通知任务

    向指定用户发送通知，支持多种渠道（email/sms/push）。
    失败时会自动重试（由 WorkerSettings.max_tries 控制）。

    参数:
        ctx: arq 上下文
        user_id (str): 目标用户 ID
        content (str): 通知内容
        channel (str): 发送渠道，默认 email

    返回:
        dict: 发送结果
    """
    job_id = ctx.get("job_id", "unknown")

    logger.info(
        f"[队列任务] 执行 send_notification_task | "
        f"job_id={job_id} user={user_id} channel={channel}"
    )

    # 模拟发送耗时
    await asyncio.sleep(0.05)

    # 模拟随机失败（10% 概率），用于测试重试机制
    if random.random() < 0.1:
        raise RuntimeError(f"通知发送失败: user={user_id} channel={channel}")

    return {
        "status": "success",
        "user_id": user_id,
        "channel": channel,
        "sent": True,
    }


async def generate_report_task(ctx, report_type: str, params: dict = None) -> dict:
    """
    生成报表任务

    根据类型和参数生成报表，耗时较长，适合异步执行。
    生成完成后可通知用户或存储到文件系统。

    参数:
        ctx: arq 上下文
        report_type (str): 报表类型（daily/weekly/monthly）
        params (dict): 报表参数（日期范围、筛选条件等）

    返回:
        dict: 报表结果，包含文件路径等
    """
    job_id = ctx.get("job_id", "unknown")
    params = params or {}

    logger.info(
        f"[队列任务] 执行 generate_report_task | "
        f"job_id={job_id} type={report_type}"
    )

    # 模拟报表生成耗时
    await asyncio.sleep(0.2)

    return {
        "status": "success",
        "report_type": report_type,
        "file_path": f"/tmp/reports/{report_type}_report.pdf",
        "generated_at": "2026-05-26T00:00:00",
    }


async def cleanup_expired_results(ctx) -> dict:
    """
    清理过期任务结果

    定期清理 Redis 中已过期的任务结果缓存。
    由 arq cron 定时触发，不需要手动调用。

    参数:
        ctx: arq 上下文

    返回:
        dict: 清理结果
    """
    logger.info("[队列任务] 执行 cleanup_expired_results")

    return {
        "status": "success",
        "cleaned": 0,
    }
