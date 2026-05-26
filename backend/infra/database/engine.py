"""
SQLAlchemy 异步数据库引擎模块

负责创建和管理全局数据库引擎与会话工厂。
所有数据库操作通过此模块获取引擎和会话。

核心组件:
- engine: SQLAlchemy 异步引擎（连接池）
- AsyncSessionLocal: 会话工厂
- init_db(): 初始化数据库（创建表）
- get_session(): 获取数据库会话
- close_db(): 关闭引擎

使用方式:
    from infra.database import engine, get_session, init_db
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import logger
from config.env import settings


# ============================================================
# SQLAlchemy ORM 基类
# 所有数据库模型继承此类，create_all 时自动发现并创建对应表
# ============================================================
class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有模型继承此类"""
    pass


# ============================================================
# 异步引擎配置
# create_async_engine 参数说明:
# - echo=False: 不打印 SQL（生产环境关闭，调试时可开）
# - pool_size=15: 连接池大小（常驻连接数）
# - max_overflow=10: 超出 pool_size 后最多临时增加的连接数
# - pool_timeout=30: 从池中获取连接的等待超时（秒）
# - pool_recycle=1800: 30 分钟回收空闲连接，防止 PG 断开
# - pool_pre_ping=True: 每次取连接前先 PING，剔除死连接
# ============================================================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=15,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

# ============================================================
# 会话工厂
# sessionmaker 创建异步会话，每次调用 AsyncSessionLocal() 返回新会话
# expire_on_commit=False: 事务提交后不自动过期对象属性，避免 lazy load 报错
# ============================================================
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """
    初始化数据库表

    创建所有继承 Base 的模型对应的表（如果不存在）。
    使用 create_all 在异步引擎上创建表结构。
    FastAPI startup 时调用。
    """
    async with engine.begin() as conn:
        # run_sync 将同步的 create_all 包装为异步执行
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")


async def get_session() -> AsyncSession:
    """
    获取数据库会话

    返回一个异步会话实例，用于执行数据库操作。
    调用方需要手动关闭会话（async with 或 finally close）。

    返回:
        AsyncSession: 异步数据库会话
    """
    return AsyncSessionLocal()


async def close_db():
    """
    关闭数据库引擎

    释放所有连接池资源，清理全局引擎实例。
    FastAPI shutdown 时调用。
    """
    await engine.dispose()
    logger.info("数据库引擎已关闭")
