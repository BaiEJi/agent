"""
聊天接口模块

提供一问一答的 REST API 接口。
接收用户消息，调用 Agent，返回回复。

接口:
    POST /api/v1/chat
    Body: {"message": "你好"}
    Response: {"reply": "你好！有什么可以帮你的吗？"}
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent import chat
from config import logger

# ============================================================
# API 路由实例
# prefix 和 tags 在 main.py 中挂载时指定
# ============================================================
router = APIRouter()


# ============================================================
# 请求/响应模型
# 使用 Pydantic 做请求体校验和响应体序列化
# ============================================================
class ChatRequest(BaseModel):
    """
    聊天请求体

    属性:
        message (str): 用户输入的消息，不能为空
    """
    message: str = Field(..., min_length=1, description="用户消息")


class ChatResponse(BaseModel):
    """
    聊天响应体

    属性:
        reply (str): LLM 的回复文本
    """
    reply: str


@router.post("/chat", response_model=ChatResponse, summary="一问一答聊天")
async def chat_endpoint(req: ChatRequest):
    """
    一问一答聊天接口

    接收用户消息，调用 Agent 获取 LLM 回复，返回结果。

    参数:
        req (ChatRequest): 请求体，包含 message 字段

    返回:
        ChatResponse: 响应体，包含 reply 字段

    异常:
        HTTPException: LLM 调用失败时返回 500
    """
    logger.info(f"[API] 收到聊天请求: {req.message}")

    try:
        reply = await chat(req.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        logger.error(f"[API] 聊天接口异常: {e}")
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")
