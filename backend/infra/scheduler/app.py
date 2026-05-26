"""
APScheduler 初始化与生命周期管理

负责创建调度器实例、从数据库恢复任务、启动/停止调度器。

使用方式:
    由 FastAPI lifespan 调用:
        init_scheduler()  # startup
        close_scheduler() # shutdown
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import logger
from config.env import settings
from infra.database import get_session, init_db
from infra.scheduler.jobs import get_job_func
from infra.scheduler.manager import set_scheduler
from infra.scheduler.models import SchedulerTask

# ============================================================
# 全局调度器实例
# AsyncIOScheduler 基于 asyncio 事件循环，与 FastAPI 天然兼容
# ============================================================
_scheduler: AsyncIOScheduler | None = None


async def init_scheduler() -> AsyncIOScheduler:
    """
    初始化调度器

    流程:
    1. 创建数据库表（如果不存在）
    2. 创建 AsyncIOScheduler 实例
    3. 注册调度器到 manager 模块
    4. 从数据库加载所有已启用的任务
    5. 启动调度器

    返回:
        AsyncIOScheduler: 初始化完成的调度器实例
    """
    global _scheduler

    if _scheduler is not None:
        logger.warning("调度器已初始化，跳过重复调用")
        return _scheduler

    # --- Step 1: 初始化数据库表 ---
    await init_db()

    # --- Step 2: 创建调度器 ---
    # BackgroundScheduler 适合大多数场景，任务在独立线程中执行
    # 如果任务是纯 IO 操作，可考虑 AsyncIOScheduler
    _scheduler = AsyncIOScheduler(
        timezone="Asia/Shanghai",
        job_defaults={
            "coalesce": True,           # 错过的任务合并执行一次
            "max_instances": 1,         # 同一任务最多同时运行 1 个实例
            "misfire_grace_time": 300,  # 错过触发时间 5 分钟内仍执行
        },
    )

    # --- Step 3: 注册到 manager ---
    set_scheduler(_scheduler)

    # --- Step 4: 从数据库恢复任务 ---
    session = await get_session()
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SchedulerTask).where(SchedulerTask.enabled == True)
        )
        tasks = result.scalars().all()

        for task in tasks:
            func = get_job_func(task.job_func)
            if func is None:
                logger.warning(f"跳过无效任务: name={task.name} func={task.job_func}")
                continue

            trigger_args = dict(task.trigger_args) if task.trigger_args else {}
            kwargs_data = dict(task.kwargs) if task.kwargs else {}

            _scheduler.add_job(
                func,
                trigger=task.trigger,
                id=f"task_{task.id}",
                name=task.name,
                kwargs={"job_id": task.id, **kwargs_data},
                replace_existing=True,
                **trigger_args,
            )
            logger.info(f"恢复定时任务: name={task.name} trigger={task.trigger}")

    finally:
        await session.close()

    # --- Step 5: 启动调度器 ---
    _scheduler.start()
    logger.info(
        f"调度器启动完成 | "
        f"已加载 {len(_scheduler.get_jobs())} 个任务 | "
        f"时区: Asia/Shanghai"
    )

    return _scheduler


async def close_scheduler() -> None:
    """
    优雅关闭调度器

    等待所有正在执行的任务完成，然后关闭调度器。
    FastAPI shutdown 时调用。
    """
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=True)
        _scheduler = None
        logger.info("调度器已关闭")


def get_scheduler() -> AsyncIOScheduler | None:
    """
    获取当前调度器实例

    返回:
        AsyncIOScheduler | None: 调度器实例，未初始化时返回 None
    """
    return _scheduler
