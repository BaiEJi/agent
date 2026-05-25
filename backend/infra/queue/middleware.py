"""
arq 任务中间件

提供任务生命周期钩子，在任务执行前、后、异常时触发。
用于记录耗时、统计成功/失败、统一错误处理。

使用方式:
    在 WorkerSettings.middleware 中注册:
        middleware = [JobMiddleware]
"""

from config import logger


class JobMiddleware:
    """
    任务执行中间件

    实现 arq 的三个生命周期钩子:
    - before_job_execution: 任务开始前，记录开始时间
    - after_job_execution: 任务完成后，记录耗时
    - on_job_exception: 任务异常时，记录错误详情

    arq 会自动在每个任务执行时调用这些钩子。
    """

    async def before_job_execution(self, ctx):
        """
        任务执行前钩子

        记录任务开始时间到 ctx 中，供 after_job_execution 计算耗时。

        参数:
            ctx (dict): arq 上下文，可写入自定义数据
        """
        import time
        ctx["start_time"] = time.monotonic()
        ctx["job_id"] = ctx.get("job_id", "unknown")

        logger.debug(
            f"[中间件] 任务开始 | job_id={ctx['job_id']} "
            f"function={ctx.get('function', 'unknown')}"
        )

    async def after_job_execution(self, ctx):
        """
        任务完成后钩子

        计算任务耗时并记录日志。

        参数:
            ctx (dict): arq 上下文，包含 before_job_execution 写入的 start_time
        """
        import time

        start_time = ctx.get("start_time", 0)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.info(
            f"[中间件] 任务完成 | job_id={ctx['job_id']} "
            f"duration={duration_ms}ms"
        )

    async def on_job_exception(self, ctx, exc):
        """
        任务异常钩子

        记录异常详情，便于排查问题。

        参数:
            ctx (dict): arq 上下文
            exc (Exception): 捕获的异常对象
        """
        import time

        start_time = ctx.get("start_time", 0)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        logger.error(
            f"[中间件] 任务异常 | job_id={ctx['job_id']} "
            f"duration={duration_ms}ms "
            f"exception={type(exc).__name__}: {exc}"
        )
