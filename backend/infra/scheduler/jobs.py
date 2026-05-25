"""
定时任务函数定义

每个要执行的定时任务在此定义为一个普通函数。
APScheduler 通过函数路径字符串找到并执行这些函数。

命名规范：
- 函数名即任务标识，命名清晰表示用途
- 函数签名固定接收 job_id 和 **kwargs 两个参数
- kwargs 由数据库中的 trigger_args 字段传入

使用方式:
    # 在数据库中记录
    job_func = "infra.scheduler.jobs.example_job"
    # APScheduler 会自动找到这个函数并执行
"""

import json

from config import logger


def example_job(job_id: int = 0, **kwargs):
    """
    示例定时任务

    演示定时任务的基本结构，实际项目中替换为业务逻辑。

    参数:
        job_id (int): 任务 ID，用于日志追踪
        **kwargs: 从数据库 trigger_args 解析的额外参数
    """
    logger.info(f"[定时任务] 执行 example_job | job_id={job_id} | kwargs={kwargs}")


def health_check_job(job_id: int = 0, **kwargs):
    """
    系统健康检查任务

    定期检查关键服务（Redis、数据库）是否正常，
    异常时记录日志，后续可扩展为告警通知。

    参数:
        job_id (int): 任务 ID
        **kwargs: 额外参数
    """
    logger.info(f"[定时任务] 执行 health_check_job | job_id={job_id}")


def cleanup_job(job_id: int = 0, **kwargs):
    """
    数据清理任务

    清理过期数据，如过期会话、临时文件等。

    参数:
        job_id (int): 任务 ID
        **kwargs: 额外参数，可包含 retention_days 等配置
    """
    logger.info(f"[定时任务] 执行 cleanup_job | job_id={job_id} | kwargs={kwargs}")


# ============================================================
# 任务函数注册表
# key: 函数名（与数据库中 job_func 字段匹配）
# value: 函数对象
# 新增任务时在此注册，确保 manager 能通过路径找到函数
# ============================================================
JOB_REGISTRY = {
    "example_job": example_job,
    "health_check_job": health_check_job,
    "cleanup_job": cleanup_job,
}


def get_job_func(func_name: str):
    """
    根据函数名获取任务函数

    参数:
        func_name (str): 函数名，如 "example_job"

    返回:
        callable: 对应的函数对象，找不到返回 None
    """
    return JOB_REGISTRY.get(func_name)
