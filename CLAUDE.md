# CLAUDE.md

## 代码注释规范

本项目为 LangGraph 学习项目，所有代码必须写好注释。

### 方法注释
- 每个方法/函数必须有 docstring，说明：
  - 方法用途
  - 参数含义及类型
  - 返回值说明
  - 关键逻辑简述

### 代码段注释
- 关键代码段必须有行内注释，解释"为什么这样做"而非"做了什么"
- 复杂逻辑、条件判断、算法步骤需要逐段解释
- 第三方库的特殊用法需注明原因

### 文件注释
- 每个 `.py` 文件顶部需说明该文件的职责和在整体架构中的位置

### 目标
- 任何代码段都能让学习者快速理解其意图和实现方式

## 配置项规范

### 核心原则
- **所有配置项必须从 .env 文件读取，不设置默认值**
- 配置项必须在 `config/env.py` 中显式声明类型，缺少即启动报错
- 配置项命名全大写，用下划线分隔（如 `POSTGRES_HOST`）
- 不同环境（dev/test/prod）使用不同的 .env 文件

### 配置项分类
| 分类 | 前缀 | 示例 |
|------|------|------|
| OpenAI | `OPENAI_` | OPENAI_API_KEY, OPENAI_BASE_URL |
| PostgreSQL | `POSTGRES_` | POSTGRES_HOST, POSTGRES_PORT, POSTGRES_PASSWORD |
| Redis | `REDIS_` | REDIS_HOST, REDIS_PORT, REDIS_PASSWORD |
| 服务 | `APP_` | APP_HOST, APP_PORT, APP_ENV |
| 日志 | `LOG_` | LOG_LEVEL, LOG_ROTATION, LOG_RETENTION |

### 使用方式
```python
# 正确：从 settings 读取
from config.env import settings
host = settings.POSTGRES_HOST

# 错误：直接读取环境变量（绕过类型校验）
import os
host = os.getenv("POSTGRES_HOST", "localhost")  # 禁止
```

### 新增配置项流程
1. 在 `.env` 中添加配置项
2. 在 `config/env.py` 的 `Settings` 类中声明字段（不设默认值）
3. 在需要的地方通过 `settings.XXX` 使用
