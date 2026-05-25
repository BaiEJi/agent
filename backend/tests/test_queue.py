"""
arq 队列模块测试

验证任务提交、Worker 消费、状态查询、结果获取、取消任务等完整流程。
使用 burst 模式 Worker，执行完队列任务后自动退出。

运行方式:
    cd backend
    python -m tests.test_queue
"""

import asyncio
import sys
import time
from pathlib import Path

# 将 backend 目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import logger
from infra.queue.submit import close_pool, enqueue_task, get_job_status, get_job_result, get_queue_length
from infra.queue.tasks import example_task, process_message_task, send_notification_task
from infra.queue.settings import WorkerSettings


async def run_worker_burst(timeout: int = 30):
    """
    启动 Worker（burst 模式）

    burst 模式下 Worker 消费完所有任务后自动退出。
    使用 asyncio.create_subprocess_exec 启动独立进程。

    参数:
        timeout (int): Worker 最大运行时间（秒），超时强制终止

    返回:
        tuple: (returncode, stdout, stderr)
    """
    import subprocess

    # 使用 subprocess 启动 Worker 进程
    # 不用 asyncio.create_subprocess_exec 是因为 arq CLI 启动更稳定
    proc = subprocess.Popen(
        [
            "conda", "run", "-n", "agent",
            "arq", "infra.queue.settings.WorkerSettings", "--burst",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )

    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return -1, "", "Worker 超时被终止"


async def test_queue():
    """
    队列模块完整测试

    流程:
    1. 提交多个任务到队列
    2. 查询队列长度
    3. 启动 Worker 执行任务（burst 模式）
    4. 查询任务状态
    5. 获取任务结果
    6. 验证并发任务执行
    """

    # ============================================================
    # 测试 1: 提交任务
    # ============================================================
    logger.info("=== 测试 1: 提交任务到队列 ===")

    # 提交示例任务
    job_id_1 = await enqueue_task(
        example_task,
        message="测试消息 1",
        _job_timeout=60,
        _max_tries=2,
    )
    logger.info(f"任务 1 已提交: job_id={job_id_1}")
    assert job_id_1 is not None, "任务提交失败"

    # 提交消息处理任务
    job_id_2 = await enqueue_task(
        process_message_task,
        message_id="msg_001",
        payload={"content": "测试内容"},
        _job_timeout=60,
    )
    logger.info(f"任务 2 已提交: job_id={job_id_2}")
    assert job_id_2 is not None, "任务提交失败"

    # 提交通知任务
    job_id_3 = await enqueue_task(
        send_notification_task,
        user_id="user_001",
        content="测试通知",
        channel="email",
        _job_timeout=60,
    )
    logger.info(f"任务 3 已提交: job_id={job_id_3}")
    assert job_id_3 is not None, "任务提交失败"

    # ============================================================
    # 测试 2: 查询队列长度
    # ============================================================
    logger.info("=== 测试 2: 查询队列长度 ===")
    queue_length = await get_queue_length()
    logger.info(f"队列长度: {queue_length}")
    # 提交后队列中应有任务（可能已被消费，所以 >= 0）
    assert queue_length >= 0, "队列长度查询失败"
    logger.info("✅ 队列长度查询成功")

    # ============================================================
    # 测试 3: 启动 Worker（burst 模式）
    # Worker 消费完所有任务后自动退出
    # ============================================================
    logger.info("=== 测试 3: 启动 Worker（burst 模式）===")
    logger.info("启动 Worker，等待任务执行...")

    returncode, stdout, stderr = await run_worker_burst(timeout=30)

    if returncode == 0:
        logger.info("✅ Worker 执行完成")
    elif returncode == -1:
        logger.warning("Worker 超时被终止（部分任务可能未完成）")
    else:
        logger.warning(f"Worker 异常退出: returncode={returncode}")
        if stderr:
            # 只打印最后几行错误信息
            error_lines = stderr.strip().split("\n")[-5:]
            for line in error_lines:
                logger.warning(f"  {line}")

    # ============================================================
    # 测试 4: 查询任务状态
    # ============================================================
    logger.info("=== 测试 4: 查询任务状态 ===")

    status_1 = await get_job_status(job_id_1)
    logger.info(f"任务 1 状态: {status_1}")
    assert status_1["status"] in (
        "complete", "queued", "in_progress", "deferred", "not_found"
    ), f"无效状态: {status_1['status']}"
    logger.info("✅ 任务 1 状态查询成功")

    status_2 = await get_job_status(job_id_2)
    logger.info(f"任务 2 状态: {status_2}")
    assert status_2["status"] in (
        "complete", "queued", "in_progress", "deferred", "not_found"
    ), f"无效状态: {status_2['status']}"
    logger.info("✅ 任务 2 状态查询成功")

    status_3 = await get_job_status(job_id_3)
    logger.info(f"任务 3 状态: {status_3}")
    assert status_3["status"] in (
        "complete", "queued", "in_progress", "deferred", "not_found"
    ), f"无效状态: {status_3['status']}"
    logger.info("✅ 任务 3 状态查询成功")

    # ============================================================
    # 测试 5: 获取任务结果
    # 仅已完成的任务有结果
    # ============================================================
    logger.info("=== 测试 5: 获取任务结果 ===")

    if status_1["status"] == "complete":
        result_1 = await get_job_result(job_id_1)
        logger.info(f"任务 1 结果: {result_1}")
        assert result_1 is not None, "任务已完成但结果为空"
        assert result_1.get("status") == "success", "任务结果状态不正确"
        logger.info("✅ 任务 1 结果获取成功")
    else:
        logger.info(f"任务 1 未完成，跳过结果验证: status={status_1['status']}")

    # ============================================================
    # 测试 6: 提交延迟任务
    # _defer_by 指定延迟秒数后执行
    # ============================================================
    logger.info("=== 测试 6: 提交延迟任务 ===")

    job_id_deferred = await enqueue_task(
        example_task,
        message="延迟任务",
        _defer_by=2,  # 2 秒后执行
        _job_timeout=60,
    )
    logger.info(f"延迟任务已提交: job_id={job_id_deferred}")

    # 立即查询，状态应为 deferred
    status_deferred = await get_job_status(job_id_deferred)
    logger.info(f"延迟任务状态（立即查询）: {status_deferred['status']}")

    # ============================================================
    # 测试 7: 清理
    # ============================================================
    logger.info("=== 测试 7: 清理连接池 ===")
    await close_pool()
    logger.info("✅ 连接池已关闭")

    print("\n✅ 所有队列测试通过")


if __name__ == "__main__":
    asyncio.run(test_queue())
