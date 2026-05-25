"""
FastAPI 应用入口

负责创建 FastAPI 实例、配置生命周期事件（Redis 初始化/关闭）、挂载路由。
整个后端服务从这里启动。

启动方式:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import logger
from config.env import settings
from infra.redis import close_pool, init_pool


# ============================================================
# 应用生命周期管理
# 使用 asynccontextmanager 定义 startup 和 shutdown 事件
# FastAPI 的 lifespan 机制会自动在启动时进入、关闭时退出
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期上下文管理器

    yield 之前 = startup 阶段，执行初始化操作
    yield 之后 = shutdown 阶段，执行清理操作

    被管理的资源:
    - Redis 连接池（startup 初始化，shutdown 关闭）
    """
    # ---- startup ----
    logger.info("服务启动中...")
    init_pool()
    logger.info("服务启动完成")

    yield  # 应用运行期间

    # ---- shutdown ----
    logger.info("服务关闭中...")
    await close_pool()
    logger.info("服务已关闭")


# ============================================================
# 创建 FastAPI 实例
# lifespan 参数绑定生命周期管理器
# ============================================================
app = FastAPI(
    title="Agent API",
    description="LangGraph Agent 学习项目",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """
    健康检查接口

    返回服务状态和 Redis 连接池指标，用于监控和问题排查。
    """
    from infra.redis import check_redis_health

    redis_health = await check_redis_health()

    return {
        "status": "ok" if redis_health["ok"] else "degraded",
        "env": settings.APP_ENV,
        "redis": redis_health,
    }
