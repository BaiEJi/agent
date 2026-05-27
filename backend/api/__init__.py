"""
api 包的初始化模块

统一导出 API 路由:
    from api import router
"""

from api.chat import router

__all__ = ["router"]
