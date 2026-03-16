# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

将 AWS Bedrock 转换为 Anthropic / OpenAI API 的直接替代。一条 CDK 命令部署，API Key 认证，自动按租户追踪用量。

```
客户端 (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API Key + 用量追踪)
```

## 支持的模型

| 别名 | Bedrock 模型 |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

OpenAI 模型名称也会自动映射：`gpt-4o` → Claude Sonnet 4，`gpt-4o-mini` → Claude Haiku 4.5，等等。

## 快速开始

### 前置条件

- 已配置 AWS CLI 且有 Bedrock 访问权限
- Node.js >= 18，Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### 部署

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

输出会打印 API Gateway URL，这就是所有请求的 base URL。

### 创建 API Key

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

返回：

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## 使用方式

### Anthropic API 格式

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

使用 Anthropic Python SDK：

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "你好！"}],
)
print(message.content[0].text)
```

### OpenAI API 格式

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

使用 OpenAI Python SDK：

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "你好！"}],
)
print(resp.choices[0].message.content)
```

### 流式输出

两个端点都支持流式输出 — 在请求体中添加 `"stream": true` 即可。SSE 事件遵循对应的 API 格式（Anthropic 或 OpenAI）。

### 认证方式

API Key 可以通过以下任一 header 传递：

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## 管理接口

所有管理端点需要 admin API key。

| 方法 | 端点 | 说明 |
|---|---|---|
| `POST` | `/admin/keys` | 创建 API Key |
| `GET` | `/admin/keys?tenant_id=xxx` | 列出租户的 Key |
| `DELETE` | `/admin/keys/{key}` | 禁用 API Key |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | 查询用量 |

### CLI 管理工具

也可以通过 CLI 脚本直接管理 Key（需要 AWS 凭证）：

```bash
# 创建
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# 列出
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# 禁用
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## 配置项

| CDK Context 参数 | 默认值 | 说明 |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | 管理端点的 admin API key |
| `bedrockRegion` | 栈所在区域 | Bedrock API 调用的 AWS 区域 |

通过 `-c` 参数传递：

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## 架构

| 组件 | 技术 |
|---|---|
| 基础设施 | AWS CDK (TypeScript) |
| 推理 Lambda | Python 3.12, ARM64, 256 MB, 5 分钟超时 |
| 管理 Lambda | Python 3.14, ARM64, 256 MB, 30 秒超时 |
| API Key 表 | DynamoDB (按需计费) |
| 用量表 | DynamoDB (按需计费, 90 天 TTL) |
| API 网关 | REST API，支持 CORS |

## 项目结构

```
├── cdk/                    # CDK 基础设施
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # 推理 Lambda
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # 管理 Lambda
│   └── handler.py
└── scripts/
    └── manage_keys.py      # CLI Key 管理工具
```

## 许可证

AGPL-3.0
