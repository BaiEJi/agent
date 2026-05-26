"""
定时任务动态管理模块

提供增删改查操作，同时更新数据库和 APScheduler 调度器。
所有操作都是原子的：数据库写入成功后才更新调度器，保证数据一致。

使用方式:
    from infra.scheduler.manager import add_task, remove_task, list_tasks
"""

import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import logger
from infra.database import get_session
from infra.scheduler.jobs import get_job_func
from infra.scheduler.models import SchedulerTask

# ============================================================
# 全局调度器实例引用
# 在 init_scheduler() 中赋值，此处仅做引用声明
# ============================================================
_scheduler: AsyncIOScheduler | None = None


def set_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    注册调度器实例

    由 app.py 在创建调度器后调用，建立 manager 与 scheduler 的关联。

    参数:
        scheduler (AsyncIOScheduler): APScheduler 异步调度器实例
    """
    global _scheduler
    _scheduler = scheduler


async def add_task(
    name: str,
    job_func: str,
    trigger: str,
    trigger_args: dict = None,
    kwargs: dict = None,
    enabled: bool = True,
) -> dict:
    """
    新增定时任务

    流程:
    1. 验证函数路径是否有效
    2. 写入数据库（名称唯一约束）
    3. 如果 enabled=True，同步加入 APScheduler 调度

    参数:
        name (str): 任务名称，全局唯一
        job_func (str): 函数路径，如 "example_job"
        trigger (str): 触发类型，支持 interval / cron / date
        trigger_args (dict): 触发参数，如 {"hours": 1} 或 {"hour": 9, "minute": 0}
        kwargs (dict): 函数参数，会传入任务函数
        enabled (bool): 是否立即启用

    返回:
        dict: 创建的任务信息

    异常:
        ValueError: 函数名不存在
        ValueError: 任务名已存在
    """
    # 验证函数是否存在
    func = get_job_func(job_func)
    if func is None:
        raise ValueError(f"任务函数不存在: {job_func}")

    trigger_args = trigger_args or {}
    kwargs = kwargs or {}

    session = await get_session()
    try:
        # 检查名称是否重复
        from sqlalchemy import select
        existing = await session.execute(
            select(SchedulerTask).where(SchedulerTask.name == name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ValueError(f"任务名已存在: {name}")

        # 写入数据库
        task = SchedulerTask(
            name=name,
            job_func=job_func,
            trigger=trigger,
            trigger_args=json.dumps(trigger_args),
            kwargs=json.dumps(kwargs),
            enabled=enabled,
        )
        session.add(task)
        await session.commit()
        # 刷新获取自增 ID
        await session.refresh(task)

        # 加入调度器
        if enabled and _scheduler is not None:
            _scheduler.add_job(
                func,
                trigger=trigger,
                id=f"task_{task.id}",
                name=name,
                kwargs={"job_id": task.id, **kwargs},
                replace_existing=True,
                **trigger_args,
            )
            logger.info(f"定时任务已添加: name={name} trigger={trigger}")

        return {
            "id": task.id,
            "name": task.name,
            "job_func": task.job_func,
            "trigger": task.trigger,
            "trigger_args": trigger_args,
            "kwargs": kwargs,
            "enabled": task.enabled,
        }

    except ValueError:
        raise
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def remove_task(task_id: int) -> dict:
    """
    删除定时任务

    流程:
    1. 从 APScheduler 移除调度
    2. 从数据库删除记录

    参数:
        task_id (int): 任务 ID

    返回:
        dict: 被删除的任务信息

    异常:
        ValueError: 任务不存在
    """
    session = await get_session()
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SchedulerTask).where(SchedulerTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if task is None:
            raise ValueError(f"任务不存在: id={task_id}")

        # 从调度器移除
        if _scheduler is not None:
            try:
                _scheduler.remove_job(f"task_{task_id}")
            except Exception:
                pass  # 调度器中可能没有此任务，忽略

        # 从数据库删除
        await session.delete(task)
        await session.commit()

        logger.info(f"定时任务已删除: name={task.name} id={task_id}")
        return {"id": task_id, "name": task.name, "removed": True}

    except ValueError:
        raise
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def list_tasks() -> list[dict]:
    """
    查询所有定时任务

    返回数据库中所有任务的当前状态。

    返回:
        list[dict]: 任务列表，每个元素包含 id/name/trigger/enabled 等字段
    """
    session = await get_session()
    try:
        from sqlalchemy import select
        result = await session.execute(select(SchedulerTask).order_by(SchedulerTask.id))
        tasks = result.scalars().all()

        # 获取调度器中各任务的下次执行时间
        next_runs = {}
        if _scheduler is not None:
            for job in _scheduler.get_jobs():
                if job.id.startswith("task_"):
                    next_runs[job.id] = str(job.next_run_time) if job.next_run_time else None

        return [
            {
                "id": t.id,
                "name": t.name,
                "job_func": t.job_func,
                "trigger": t.trigger,
                "trigger_args": json.loads(t.trigger_args),
                "kwargs": json.loads(t.kwargs),
                "enabled": t.enabled,
                "next_run": next_runs.get(f"task_{t.id}"),
                "created_at": str(t.created_at) if t.created_at else None,
            }
            for t in tasks
        ]

    finally:
        await session.close()


async def toggle_task(task_id: int, enabled: bool) -> dict:
    """
    启用/禁用定时任务

    不删除数据库记录，仅切换 enabled 状态并同步调度器。

    参数:
        task_id (int): 任务 ID
        enabled (bool): True=启用，False=禁用

    返回:
        dict: 更新后的任务信息

    异常:
        ValueError: 任务不存在
    """
    session = await get_session()
    try:
        from sqlalchemy import select
        result = await session.execute(
            select(SchedulerTask).where(SchedulerTask.id == task_id)
        )
        task = result.scalar_one_or_none()

        if task is None:
            raise ValueError(f"任务不存在: id={task_id}")

        task.enabled = enabled
        await session.commit()

        # 同步调度器
        if _scheduler is not None:
            job_id = f"task_{task_id}"
            existing_job = _scheduler.get_job(job_id)

            if enabled and existing_job is None:
                # 启用：添加到调度器
                func = get_job_func(task.job_func)
                if func:
                    trigger_args = json.loads(task.trigger_args)
                    kwargs_data = json.loads(task.kwargs)
                    _scheduler.add_job(
                        func,
                        trigger=task.trigger,
                        id=job_id,
                        name=task.name,
                        kwargs={"job_id": task.id, **kwargs_data},
                        replace_existing=True,
                        **trigger_args,
                    )
                    logger.info(f"定时任务已启用: name={task.name}")
            elif not enabled and existing_job is not None:
                # 禁用：从调度器移除
                _scheduler.remove_job(job_id)
                logger.info(f"定时任务已禁用: name={task.name}")

        return {
            "id": task.id,
            "name": task.name,
            "enabled": task.enabled,
        }

    except ValueError:
        raise
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()
