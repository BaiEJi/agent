"""
Redis 模块测试

验证 Redis 连接池、基本读写、健康监控是否正常。

运行方式:
    cd backend
    python -m tests.test_redis
"""

import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import logger
from config.env import settings
from infra.redis import check_redis_health, close_pool, get_pool_stats, init_pool


async def test_redis_pool():
    """
    测试 Redis 连接池完整生命周期

    验证点:
    1. init_pool() 能正常初始化连接池
    2. get_pool_stats() 返回有效的连接池状态
    3. check_redis_health() PING 正常
    4. 基本读写操作正常
    5. close_pool() 正常关闭
    """
    logger.info("--- 开始连接池测试 ---")

    # --- 测试 1: 初始化连接池 ---
    client = init_pool()
    assert client is not None, "init_pool() 返回 None"
    logger.info("✅ 连接池初始化成功")

    # --- 测试 2: 连接池状态 ---
    stats = get_pool_stats()
    logger.info(f"连接池状态: {stats}")
    assert stats["status"] == "ok", f"连接池状态异常: {stats['status']}"
    assert stats["max"] == 50, f"最大连接数期望 50，实际 {stats['max']}"
    # 初始化后不应有连接创建（懒加载）
    assert stats["created"] == 0, f"初始化后不应有连接，实际 {stats['created']}"
    logger.info("✅ 连接池状态检查通过")

    # --- 测试 3: 基本读写操作 ---
    test_key = "test:pool"
    test_value = "pool_test_value"
    await client.set(test_key, test_value)
    got_value = await client.get(test_key)
    assert got_value == test_value, f"GET 期望 '{test_value}'，实际 '{got_value}'"
    logger.info("✅ SET/GET 读写测试通过")

    # --- 测试 4: 查看连接是否被创建 ---
    # 读写操作后，连接池应该创建了至少 1 个连接
    stats_after = get_pool_stats()
    logger.info(f"读写后连接池状态: {stats_after}")
    assert stats_after["created"] >= 1, "读写后应有连接被创建"
    logger.info("✅ 连接创建确认通过")

    # --- 测试 5: 健康检查 ---
    health = await check_redis_health()
    logger.info(f"健康检查: {health}")
    assert health["ok"] is True, f"健康检查失败: {health}"
    assert health["ping_ms"] > 0, f"PING 响应时间异常: {health['ping_ms']}"
    logger.info(f"✅ 健康检查通过，PING={health['ping_ms']}ms")

    # --- 清理测试数据 ---
    await client.delete(test_key)
    logger.info("✅ 清理测试数据完成")

    # --- 测试 6: 关闭连接池 ---
    await close_pool()
    stats_closed = get_pool_stats()
    assert stats_closed["status"] == "not_initialized", "关闭后状态应为 not_initialized"
    logger.info("✅ 连接池关闭成功")

    print("\n✅ 所有 Redis 连接池测试通过")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_redis_pool())
