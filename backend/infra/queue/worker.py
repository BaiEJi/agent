"""
arq Worker 启动入口

提供两种启动方式:
1. 命令行直接启动（生产环境）
2. FastAPI lifespan 中启动（开发环境，与主进程同生命周期）

使用方式:
    # 命令行启动（推荐生产环境）
    arq infra.queue.worker.WorkerSettings

    # 或使用此模块中的 start_worker()
"""

from arq.worker import Worker

from config import logger
from infra.queue.settings import WorkerSettings


def start_worker():
    """
    启动 Worker 的辅助函数

    主要用于开发调试，生产环境建议直接用 arq CLI:
        arq infra.queue.worker.WorkerSettings
    """
    logger.info("启动 arq Worker...")
    Worker(
        settings=WorkerSettings,
        burst=WorkerSettings.burst,
    ).run()


if __name__ == "__main__":
    start_worker()
