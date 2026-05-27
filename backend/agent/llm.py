"""
LLM 客户端模块

初始化 ChatOpenAI 客户端，通过 OpenAI 兼容接口调用 MiniMax 模型。
LangChain 的 ChatOpenAI 支持任何 OpenAI 兼容的 API 端点。

使用方式:
    from agent.llm import llm
    response = await llm.ainvoke([HumanMessage(content="你好")])
"""

from langchain_openai import ChatOpenAI

from config.env import settings

# ============================================================
# ChatOpenAI 客户端初始化
# ChatOpenAI 是 LangChain 对 OpenAI Chat API 的封装
# 支持任何 OpenAI 兼容端点（如 MiniMax、DeepSeek 等）
#
# 参数说明:
# - api_key: API 密钥，从 .env 读取
# - base_url: API 端点地址，MiniMax 使用 /anthropic 路径
# - model: 模型名称，MiniMax-M2.7
# - temperature: 生成温度，0-1，越高越随机（0.7 适中）
# - max_tokens: 单次回复最大 token 数
# ============================================================
llm = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    model=settings.OPENAI_MODEL,
    temperature=0.7,
    max_tokens=2048,
)
