"""
日志配置模块

负责初始化 loguru 日志系统。
提供统一的日志格式、输出目标（控制台 + 文件）、日志轮转等配置。

使用方式:
    from config.logger import logger
    logger.info("xxx")
"""

import sys
from pathlib import Path

from loguru import logger

# ============================================================
# 日志目录：backend/logs/
# 所有日志文件统一存放在此目录下
# ============================================================
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ============================================================
# 移除 loguru 默认的 stderr handler
# loguru 默认会往 stderr 输出，我们需要替换为自定义配置
# ============================================================
logger.remove()

# ============================================================
# 控制台输出 handler
# - level: DEBUG 及以上级别输出到控制台
# - format: 包含时间、日志级别、模块名、行号、消息
# - colorize: 控制台输出带颜色，便于区分日志级别
# ============================================================
logger.add(
    sys.stderr,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
           "<level>{level: <8}</level> | "
           "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
           "<level>{message}</level>",
    colorize=True,
)

# ============================================================
# 文件输出 handler - 通用日志
# - level: INFO 及以上，记录所有业务日志
# - rotation: 日志文件达到 10MB 自动轮转
# - retention: 保留最近 7 天的日志文件
# - encoding: UTF-8 编码，支持中文
# ============================================================
logger.add(
    LOG_DIR / "app.log",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} | {message}",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)

# ============================================================
# 文件输出 handler - 错误日志
# - level: ERROR 及以上，单独记录错误便于排查
# - rotation: 每天轮转一次
# - retention: 保留最近 30 天的错误日志
# ============================================================
logger.add(
    LOG_DIR / "error.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} | {message}",
    rotation="1 day",
    retention="30 days",
    encoding="utf-8",
)
