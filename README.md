# Agent

基于 LangGraph 的 AI Agent 学习项目，前后端分离架构。

## 技术栈

- Python 3.13 + FastAPI
- LangGraph / LangChain
- PostgreSQL (asyncpg)
- Redis (redis.asyncio)
- arq (异步任务队列)
- APScheduler (定时任务)

## 项目结构

```
Agent/
├── frontend/                # 前端
├── backend/
│   ├── main.py              # FastAPI 入口 + 生命周期管理
│   ├── config.py            # (预留)
│   ├── requirements.txt
│   ├── .env                 # 环境变量（勿提交 git）
│   ├── config/              # 配置模块
│   │   ├── env.py           # pydantic BaseSettings，读取 .env
│   │   ├── logger.py        # loguru 日志初始化
│   │   └── settings.py      # 全局常量
│   ├── agent/               # LangGraph Agent 核心
│   ├── content/             # 内容管理
│   │   ├── context/         # 上下文
│   │   ├── session/         # 会话
│   │   └── memory/          # 记忆
│   ├── tools/               # Agent 可调用工具
│   ├── infra/               # 基础设施
│   │   ├── redis/           # Redis 连接池 + 监控
│   │   ├── scheduler/       # 定时任务
│   │   └── queue/           # 异步队列 (arq)
│   ├── api/                 # API 路由
│   └── utils/               # 通用工具
├── CLAUDE.md                # 代码注释规范
└── README.md
```

## 环境配置

### 1. 创建 conda 环境

```bash
conda create -n agent python=3.13 -y
conda activate agent
```

### 2. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env` 并填写实际值：

```bash
cp .env .env.local  # 可选，本地开发用
```

关键配置项：

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | `sk-xxx` |
| `OPENAI_BASE_URL` | API 地址（可换为兼容接口） | `https://api.openai.com/v1` |
| `POSTGRES_HOST` | PostgreSQL 地址 | `localhost` |
| `REDIS_HOST` | Redis 地址 | `localhost` |
| `REDIS_PORT` | Redis 端口 | `50001` |
| `REDIS_PASSWORD` | Redis 密码 | - |

### 4. 启动服务

```bash
conda activate agent
cd backend

# 开发模式（热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. 验证

```bash
# 健康检查
curl http://localhost:8000/health

# API 文档
open http://localhost:8000/docs
```

## 测试

```bash
cd backend

# 日志测试
python -m tests.test_logger

# Redis 连接池测试
python -m tests.test_redis

# 定时任务调度测试
python -m tests.test_scheduler

# 异步队列测试
python -m tests.test_queue
```
