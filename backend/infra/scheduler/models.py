"""
定时任务数据库模型

定义 scheduler_tasks 表结构，存储所有动态定时任务的配置。
APScheduler 启动时从此表恢复任务，增删改操作同时更新数据库和调度器。

使用方式:
    from infra.scheduler.models import SchedulerTask
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

# 从 infra.database 导入 Base，确保模型注册到同一个元数据
# init_db() 时会自动创建 scheduler_tasks 表
from infra.database import Base


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
