"""
Agent 核心循环模块

实现最简单的一问一答对话：
1. 接收用户消息
2. 构建消息列表（system + user）
3. 调用 LLM 获取回复
4. 返回回复文本

使用方式:
    from agent import chat
    reply = await chat("你好")
"""

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import llm
from config import logger

# ============================================================
# System Prompt
# 定义 Agent 的角色和行为规范
# 后续可扩展为从数据库或配置文件读取
# ============================================================
SYSTEM_PROMPT = "你是一个有用的 AI 助手，用中文回复用户的问题。简洁明了，不要废话。"


async def chat(message: str) -> str:
    """
    一问一答对话函数

    接收用户消息，调用 LLM，返回回复文本。
    这是最简单的 Agent 实现，不包含记忆、工具调用等复杂功能。

    参数:
        message (str): 用户输入的消息

    返回:
        str: LLM 的回复文本

    异常:
        Exception: LLM 调用失败时抛出
    """
    logger.info(f"[Agent] 用户消息: {message}")

    # 构建消息列表
    # SystemMessage: 定义 Agent 的角色和行为
    # HumanMessage: 用户的输入
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]

    # 调用 LLM
    # ainvoke 是异步调用，不会阻塞事件循环
    try:
        response = await llm.ainvoke(messages)
        reply = response.content
        logger.info(f"[Agent] 回复: {reply}")
        return reply

    except Exception as e:
        logger.error(f"[Agent] LLM 调用失败: {e}")
        raise
