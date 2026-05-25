"""
日志模块测试

验证 logger 初始化是否正常，各级别日志是否正确输出到控制台和文件。

运行方式:
    cd backend
    python -m tests.test_logger
"""

import sys
from pathlib import Path

# 将 backend 目录加入 Python 路径，确保 config 包可被 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import logger


def test_logger():
    """
    测试 logger 各级别输出

    验证点:
    1. DEBUG/INFO/WARNING/ERROR/CRITICAL 五个级别都能正常输出
    2. 控制台输出带颜色格式
    3. 文件输出到 logs/app.log 和 logs/error.log
    """
    logger.debug("这是一条 DEBUG 日志 —— 仅控制台可见（文件级别 >= INFO）")
    logger.info("这是一条 INFO 日志 —— 控制台 + logs/app.log")
    logger.warning("这是一条 WARNING 日志 —— 控制台 + logs/app.log")
    logger.error("这是一条 ERROR 日志 —— 控制台 + logs/app.log + logs/error.log")
    logger.critical("这是一条 CRITICAL 日志 —— 控制台 + logs/app.log + logs/error.log")

    # 验证日志文件是否生成
    log_dir = Path(__file__).parent.parent / "logs"
    app_log = log_dir / "app.log"
    error_log = log_dir / "error.log"

    assert app_log.exists(), "logs/app.log 未生成"
    assert error_log.exists(), "logs/error.log 未生成"

    # 验证 error.log 中确实包含 ERROR 级别日志
    error_content = error_log.read_text(encoding="utf-8")
    assert "ERROR" in error_content, "error.log 中未找到 ERROR 级别日志"
    assert "CRITICAL" in error_content, "error.log 中未找到 CRITICAL 级别日志"

    print("\n✅ 所有日志测试通过")


if __name__ == "__main__":
    test_logger()
