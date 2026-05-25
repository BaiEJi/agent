"""
定时任务数据库模型

定义 scheduler_tasks 表结构，存储所有动态定时任务的配置。
APScheduler 启动时从此表恢复任务，增删改操作同时更新数据库和调度器。

使用方式:
    from infra.scheduler.models import SchedulerTask
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import logger
from config.env import settings


# ============================================================
# SQLAlchemy 异步引擎和会话工厂
# 使用 SQLite + aiosqlite 作为后端
# create_async_engine 的参数说明:
# - echo=False: 不打印每条 SQL（生产环境关闭）
# - connect_args: SQLite 专用参数，check_same_thread=False 允许多线程访问
# ============================================================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

# sessionmaker 创建会话工厂，每次调用 SessionLocal() 返回一个新的数据库会话
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy ORM 基类，所有模型继承此类"""
    pass


class SchedulerTask(Base):
    """
    定时任务表

    存储动态定时任务的完整配置，支持：
    - interval: 固定间隔执行（如每 30 分钟）
    - cron: cron 表达式触发（如每天 9 点）
    - date: 指定时间执行一次
    """
    __tablename__ = "scheduler_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="任务 ID")
    name = Column(String(100), unique=True, nullable=False, comment="任务名称（唯一）")
    job_func = Column(String(500), nullable=False, comment="执行的函数路径")
    trigger = Column(String(20), nullable=False, comment="触发类型：interval / cron / date")
    trigger_args = Column(Text, nullable=False, default="{}", comment="触发参数（JSON 字符串）")
    kwargs = Column(Text, nullable=False, default="{}", comment="函数参数（JSON 字符串）")
    enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self) -> str:
        return f"<SchedulerTask(id={self.id}, name={self.name}, trigger={self.trigger}, enabled={self.enabled})>"


async def init_db():
    """
    初始化数据库表

    创建 scheduler_tasks 表（如果不存在）。
    使用 create_all 在异步引擎上创建所有表结构。
    """
    async with engine.begin() as conn:
        # 创建所有继承 Base 的表
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库初始化完成")


async def get_session() -> AsyncSession:
    """
    获取数据库会话

    返回一个异步会话实例，用于执行数据库操作。
    调用方需要手动关闭会话。

    返回:
        AsyncSession: 异步数据库会话
    """
    return AsyncSessionLocal()
