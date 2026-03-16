# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

AWS Bedrock을 Anthropic / OpenAI API의 드롭인 대체로 전환합니다. CDK 명령 하나로 배포하고, API 키로 인증하며, 테넌트별 사용량을 자동으로 추적합니다.

```
클라이언트 (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API 키 + 사용량 추적)
```

## 지원 모델

| 별칭 | Bedrock 모델 |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

OpenAI 모델명도 자동으로 매핑됩니다: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5 등.

## 빠른 시작

### 사전 요구사항

- Bedrock 접근 권한이 설정된 AWS CLI
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### 배포

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

출력에 API Gateway URL이 표시됩니다. 이것이 모든 요청의 기본 URL입니다.

### API 키 생성

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

응답:

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## 사용법

### Anthropic API 형식

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "안녕하세요!"}]
  }'
```

Anthropic Python SDK 사용:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "안녕하세요!"}],
)
print(message.content[0].text)
```

### OpenAI API 형식

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "안녕하세요!"}]
  }'
```

OpenAI Python SDK 사용:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "안녕하세요!"}],
)
print(resp.choices[0].message.content)
```

### 스트리밍

두 엔드포인트 모두 스트리밍을 지원합니다. 요청 본문에 `"stream": true`를 추가하면 됩니다. SSE 이벤트는 각 API 형식(Anthropic 또는 OpenAI)을 따릅니다.

### 인증

API 키는 다음 헤더 중 하나로 전달할 수 있습니다:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## 관리 API

모든 관리 엔드포인트에는 admin API 키가 필요합니다.

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| `POST` | `/admin/keys` | API 키 생성 |
| `GET` | `/admin/keys?tenant_id=xxx` | 테넌트의 키 목록 |
| `DELETE` | `/admin/keys/{key}` | API 키 비활성화 |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | 사용량 조회 |

### CLI 키 관리

CLI 스크립트로 직접 키를 관리할 수도 있습니다 (AWS 자격 증명 필요):

```bash
# 생성
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# 목록
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# 비활성화
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## 설정

| CDK Context | 기본값 | 설명 |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | 관리 엔드포인트용 admin API 키 |
| `bedrockRegion` | 스택 리전 | Bedrock API 호출용 AWS 리전 |

`-c` 플래그로 전달:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## 아키텍처

| 구성 요소 | 기술 |
|---|---|
| 인프라 | AWS CDK (TypeScript) |
| 추론 Lambda | Python 3.12, ARM64, 256 MB, 5분 타임아웃 |
| 관리 Lambda | Python 3.14, ARM64, 256 MB, 30초 타임아웃 |
| API 키 테이블 | DynamoDB (온디맨드) |
| 사용량 테이블 | DynamoDB (온디맨드, 90일 TTL) |
| API Gateway | REST API, CORS 지원 |

## 프로젝트 구조

```
├── cdk/                    # CDK 인프라
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # 추론 Lambda
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # 관리 Lambda
│   └── handler.py
└── scripts/
    └── manage_keys.py      # CLI 키 관리
```

## 라이선스

AGPL-3.0
