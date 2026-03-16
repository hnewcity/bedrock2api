# bedrock2api

🇨🇳 [中文](docs/README_CN.md) • 🇯🇵 [日本語](docs/README_JA.md) • 🇰🇷 [한국어](docs/README_KO.md) • 🇷🇺 [Русский](docs/README_RU.md) • 🇪🇸 [Español](docs/README_ES.md) • 🇧🇷 [Português](docs/README_PT.md) • 🇮🇩 [Indonesia](docs/README_ID.md)

---

Turn AWS Bedrock into a drop-in replacement for Anthropic / OpenAI APIs. Deploy with one CDK command, authenticate with API keys, and track per-tenant usage automatically.

```
Client (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API keys + usage tracking)
```

## Supported Models

| Alias | Bedrock Model |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

OpenAI model names are also mapped automatically: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5, etc.

## Quick Start

### Prerequisites

- AWS CLI configured with Bedrock access
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### Deploy

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

The output prints your API Gateway URL — that's your base URL for all requests.

### Create an API Key

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

Response:

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## Usage

### Anthropic API Format

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

With the Anthropic Python SDK:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}],
)
print(message.content[0].text)
```

### OpenAI API Format

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

With the OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(resp.choices[0].message.content)
```

### Streaming

Both endpoints support streaming — just add `"stream": true` to the request body. SSE events follow the respective API format (Anthropic or OpenAI).

### Authentication

API keys can be passed via either header:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## Admin API

All admin endpoints require the admin API key.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/keys` | Create API key |
| `GET` | `/admin/keys?tenant_id=xxx` | List keys for tenant |
| `DELETE` | `/admin/keys/{key}` | Disable API key |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | Query usage |

### CLI Key Management

You can also manage keys directly via the CLI script (requires AWS credentials):

```bash
# Create
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# List
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# Disable
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## Configuration

| CDK Context | Default | Description |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | Admin API key for management endpoints |
| `bedrockRegion` | Stack region | AWS region for Bedrock API calls |

Pass via `-c` flag:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## Architecture

| Component | Tech |
|---|---|
| Infrastructure | AWS CDK (TypeScript) |
| Inference Lambda | Python 3.12, ARM64, 256 MB, 5 min timeout |
| Management Lambda | Python 3.14, ARM64, 256 MB, 30 s timeout |
| API Keys Table | DynamoDB (pay-per-request) |
| Usage Table | DynamoDB (pay-per-request, 90-day TTL) |
| API Gateway | REST API with CORS |

## Project Structure

```
├── cdk/                    # CDK infrastructure
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # Inference Lambda
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # Admin Lambda
│   └── handler.py
└── scripts/
    └── manage_keys.py      # CLI key management
```

## License

AGPL-3.0
