# 听书平台智能客服（glm-audiobooks）

面向在线听书平台的智能客服后端，基于老师电商客服架构改造而来。支持意图识别、信息检索、多轮任务对话、流程切换/恢复、会话持久化、闲聊兜底与意图澄清。

## 架构

```
用户消息 → DialogueEngine
            ├─ 文本消息 → TurnPlanner(LLM 路由) → 校验
            │     ├─ task 轨道   → TaskHandler → FlowExecutor(YAML 流程) → Action(调 audio-data)
            │     ├─ knowledge 轨道 → KnowledgeHandler → Provider(调 audio-data/FAQ) → LLM 作答
            │     └─ chitchat 轨道 → ChitChatHandler → LLM
            └─ 对象消息 → 槽位填充 / 澄清
状态持久化 → MySQL customer_service.dialogue_states (JSON)
业务数据   → HTTP 调用 audio-data 服务（本地 8000）
```

## 目录结构

```
glm-audiobooks/
├── atguigu/                # 客服后端（改自老师电商客服）
│   ├── api/                # FastAPI 路由、schemas
│   ├── engine/             # DialogueEngine、builder
│   ├── plan/               # TurnPlanner、TurnPlan、Validator
│   ├── domain/             # state(聚合根)/contexts/messages
│   ├── task/               # flow(YAML 引擎)/action(customer 业务动作)/command
│   ├── knowledge/          # intents + providers(调 audio-data)
│   ├── chitchat/ clarify/  # 闲聊、澄清
│   ├── infrastructure/     # llm_client/http_client/db
│   ├── prompts/jinja2/     # 4 个 prompt 模板
│   ├── repository/ model/  # 状态持久化
│   └── static/index.html   # 调试页
├── audio-data/             # 听书业务数据中台（数据+REST API，本地 8000）
├── flow_config/            # system_flows.yml + user_flows.yml（听书流程定义）
├── .env                    # 配置
├── pyproject.toml
└── main 入口：uv run python -m atguigu.main
```

## 听书流程（flow_config/user_flows.yml）

- `order_query` 订单查询：收订单号 → 查 audio-data 订单 → 回复
- `playback_query` 播放记录查询：收书名 → 查收听进度 → 回复
- `refund_request` 退款申请：收订单号 → 收退款原因 → 收退款类型 → 调 POST /refunds → 回复
- `ticket_submit` 工单提交：收工单类型 → 收问题描述 → 调 POST /support-tickets → 回复
- `onboarding` 欢迎引导、`human_handoff` 转人工

## 启动步骤

### 1. 准备 MySQL（本地 3306）
听书业务库 `audio` 已建好并灌好数据；客服状态库需建表：
```sql
CREATE DATABASE IF NOT EXISTS customer_service CHARACTER SET utf8mb4;
USE customer_service;
CREATE TABLE IF NOT EXISTS dialogue_states (
  sender_id VARCHAR(255) NOT NULL PRIMARY KEY,
  state_json TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. 启动 audio-data 业务中台（端口 8000）
```bash
cd audio-data
uv sync
uv run python -m app.main   # 监听 8000，Swagger: http://127.0.0.1:8000/docs
```

### 3. 启动客服后端（端口 8002）
```bash
cd glm-audiobooks
uv sync
uv run python -m atguigu.main   # 监听 8002
```
- 调试页：http://127.0.0.1:8002/
- Swagger：http://127.0.0.1:8002/docs

### 4. 配置 .env
```
LLM_MODEL=qwen-plus
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_API_KEY=<你的通义 key>
AUDIO_API_BASE_URL=http://127.0.0.1:8000
DATABASE_URL=mysql+aiomysql://root:<密码>@127.0.0.1:3306/customer_service?charset=utf8mb4
APP_PORT=8002
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/chat | 对话（非流式），body: `{sender_id, text, object?}` |
| POST | /api/chat/stream | 对话（SSE 流式），body 同上；逐 token / 逐消息推送 |
| GET  | /api/chat/history?sender_id= | 会话历史 |
| GET  | /hello | 健康检查 |

`sender_id` 同时作为 audio-data 的 `X-User-Id`，需为 `audio.user_account.id` 中存在的用户。

### SSE 流式协议（`POST /api/chat/stream`）
响应为 `text/event-stream`，每条事件 `data: {json}\n\n`，事件类型：
- `{"type":"token","text":"..."}` —— LLM 回复的 token 流（知识/闲聊/澄清）
- `{"type":"message","text":"...","object":{...}}` —— 完整静态消息（流程回复、订单卡片）
- `{"type":"error","text":"..."}` —— 异常
- `{"type":"done"}` —— 本轮结束，状态已持久化

## 测试账号（audio 库现有数据）

- 用户 2：已支付订单 `ORD000000000001`（¥49，VIP 季度会员）→ 可测订单查询、退款申请
- 用户 1：有 9 条播放进度 → 可测播放记录查询
- 任意用户：可测有声书咨询、工单提交、闲聊

## 验证闭环

`uv run python test_smoke.py`（注意 Windows 控制台需 `PYTHONIOENCODING=utf-8`）。覆盖：闲聊、有声书咨询、订单查询、播放记录查询、退款申请、工单提交、会话历史。

## 已知限制（本期范围）

- 数字人（avatar）未接入，已从启动流程剥离。
- FAQ/平台规则为静态语料（`knowledge/providers/knowledge.py` 中 `FAQ_KNOWLEDGE`），未接外部 RAG。
- 有声书咨询按书名精确查询需用户发送有声书对象卡片；无对象时返回高评分推荐列表。
