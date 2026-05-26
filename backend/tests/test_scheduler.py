"""
定时任务调度模块测试

验证 APScheduler + 数据库动态任务管理的完整流程。

测试内容:
1. 数据库初始化
2. 动态添加任务
3. 动态删除任务
4. 动态启用/禁用任务
5. 调度器启停与任务恢复
6. 重复任务名冲突处理

运行方式:
    cd backend
    python -m tests.test_scheduler
"""

import asyncio
import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import logger
from infra.database import init_db, engine, close_db
from infra.scheduler.app import close_scheduler, init_scheduler, get_scheduler
from infra.scheduler.manager import add_task, list_tasks, remove_task, toggle_task


async def test_scheduler():
    """
    定时任务模块完整测试

    按顺序验证:
    1. 数据库表创建
    2. 调度器初始化 + 从数据库恢复
    3. 动态添加任务
    4. 查询任务列表
    5. 禁用/启用任务
    6. 删除任务
    7. 调度器关闭
    8. 清理测试数据
    """

    # ============================================================
    # 测试 1: 数据库初始化
    # 验证 scheduler_tasks 表是否正确创建
    # ============================================================
    logger.info("=== 测试 1: 数据库初始化 ===")
    await init_db()
    logger.info("✅ 数据库初始化成功")

    # ============================================================
    # 测试 2: 初始化调度器
    # 验证调度器能否正常启动（空数据库，无任务恢复）
    # ============================================================
    logger.info("=== 测试 2: 调度器初始化 ===")
    scheduler = await init_scheduler()
    assert scheduler is not None, "调度器初始化失败"
    assert scheduler.running is True, "调度器未运行"
    logger.info(f"✅ 调度器启动成功，当前任务数: {len(scheduler.get_jobs())}")

    # ============================================================
    # 测试 3: 动态添加任务
    # 添加一个 interval 类型的任务，验证数据库和调度器同步
    # ============================================================
    logger.info("=== 测试 3: 动态添加任务 ===")

    # 添加固定间隔任务：每 5 分钟执行一次
    task1 = await add_task(
        name="test_interval_task",
        job_func="example_job",
        trigger="interval",
        trigger_args={"minutes": 5},
        kwargs={"message": "测试消息"},
        enabled=True,
    )
    assert task1["id"] is not None, "任务创建失败，无 ID"
    assert task1["enabled"] is True, "任务应为启用状态"
    logger.info(f"✅ 任务添加成功: {task1}")

    # 添加 cron 类型任务：每天 9 点执行
    task2 = await add_task(
        name="test_cron_task",
        job_func="health_check_job",
        trigger="cron",
        trigger_args={"hour": 9, "minute": 0},
        enabled=True,
    )
    assert task2["id"] is not None, "任务创建失败"
    logger.info(f"✅ Cron 任务添加成功: {task2}")

    # 验证调度器中任务数
    jobs = scheduler.get_jobs()
    logger.info(f"调度器中任务数: {len(jobs)}")
    assert len(jobs) >= 2, f"期望至少 2 个任务，实际 {len(jobs)}"
    logger.info("✅ 调度器任务同步成功")

    # ============================================================
    # 测试 4: 查询任务列表
    # 从数据库读取所有任务，验证数量和内容
    # ============================================================
    logger.info("=== 测试 4: 查询任务列表 ===")
    tasks = await list_tasks()
    logger.info(f"查询到 {len(tasks)} 个任务")
    for t in tasks:
        logger.info(f"  - {t['name']} | trigger={t['trigger']} | enabled={t['enabled']}")
    assert len(tasks) >= 2, f"期望至少 2 个任务，实际 {len(tasks)}"
    logger.info("✅ 任务列表查询成功")

    # ============================================================
    # 测试 5: 重复任务名冲突
    # 尝试添加同名任务，应抛出 ValueError
    # ============================================================
    logger.info("=== 测试 5: 重复任务名冲突 ===")
    try:
        await add_task(
            name="test_interval_task",
            job_func="example_job",
            trigger="interval",
            trigger_args={"minutes": 10},
        )
        assert False, "应抛出 ValueError 但未抛出"
    except ValueError as e:
        logger.info(f"✅ 重复任务名正确抛出异常: {e}")

    # ============================================================
    # 测试 6: 禁用/启用任务
    # 禁用后调度器中应移除，启用后应恢复
    # ============================================================
    logger.info("=== 测试 6: 禁用/启用任务 ===")
    task_id = task1["id"]

    # 禁用
    toggled = await toggle_task(task_id, enabled=False)
    assert toggled["enabled"] is False, "禁用失败"
    # 验证调度器中已移除
    job = scheduler.get_job(f"task_{task_id}")
    assert job is None, "禁用后调度器中应移除此任务"
    logger.info("✅ 任务禁用成功")

    # 启用
    toggled = await toggle_task(task_id, enabled=True)
    assert toggled["enabled"] is True, "启用失败"
    # 验证调度器中已恢复
    job = scheduler.get_job(f"task_{task_id}")
    assert job is not None, "启用后调度器中应恢复此任务"
    logger.info("✅ 任务启用成功")

    # ============================================================
    # 测试 7: 删除任务
    # 从数据库和调度器中同时移除
    # ============================================================
    logger.info("=== 测试 7: 删除任务 ===")
    removed = await remove_task(task_id)
    assert removed["removed"] is True, "删除失败"
    # 验证调度器中已移除
    job = scheduler.get_job(f"task_{task_id}")
    assert job is None, "删除后调度器中应移除此任务"
    logger.info(f"✅ 任务删除成功: {removed}")

    # 删除第二个任务
    await remove_task(task2["id"])
    logger.info("✅ 第二个任务删除成功")

    # ============================================================
    # 测试 8: 调度器关闭
    # ============================================================
    logger.info("=== 测试 8: 调度器关闭 ===")
    await close_scheduler()
    scheduler = get_scheduler()
    assert scheduler is None, "关闭后调度器应为 None"
    logger.info("✅ 调度器关闭成功")

    # ============================================================
    # 测试 9: 清理测试数据
    # 删除 scheduler_tasks 表中所有测试数据
    # ============================================================
    logger.info("=== 测试 9: 清理测试数据 ===")
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM scheduler_tasks"))
    logger.info("✅ 测试数据清理完成")

    # ============================================================
    # 测试 10: 关闭数据库引擎
    # ============================================================
    logger.info("=== 测试 10: 关闭数据库引擎 ===")
    await close_db()
    logger.info("✅ 数据库引擎已关闭")

    print("\n✅ 所有定时任务调度测试通过")


if __name__ == "__main__":
    asyncio.run(test_scheduler())
