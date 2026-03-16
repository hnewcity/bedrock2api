# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

AWS Bedrock を Anthropic / OpenAI API のドロップイン代替として利用できます。CDK コマンド一つでデプロイし、API キーで認証、テナントごとの使用量を自動追跡します。

```
クライアント (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API キー + 使用量追跡)
```

## 対応モデル

| エイリアス | Bedrock モデル |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

OpenAI のモデル名も自動的にマッピングされます：`gpt-4o` → Claude Sonnet 4、`gpt-4o-mini` → Claude Haiku 4.5 など。

## クイックスタート

### 前提条件

- Bedrock アクセス権限を持つ AWS CLI の設定
- Node.js >= 18、Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### デプロイ

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

出力に API Gateway URL が表示されます。これがすべてのリクエストのベース URL です。

### API キーの作成

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

レスポンス：

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## 使い方

### Anthropic API 形式

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "こんにちは！"}]
  }'
```

Anthropic Python SDK を使用：

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "こんにちは！"}],
)
print(message.content[0].text)
```

### OpenAI API 形式

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "こんにちは！"}]
  }'
```

OpenAI Python SDK を使用：

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "こんにちは！"}],
)
print(resp.choices[0].message.content)
```

### ストリーミング

両方のエンドポイントでストリーミングをサポートしています。リクエストボディに `"stream": true` を追加するだけです。SSE イベントはそれぞれの API 形式（Anthropic または OpenAI）に従います。

### 認証

API キーは以下のいずれかのヘッダーで渡せます：

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## 管理 API

すべての管理エンドポイントには admin API キーが必要です。

| メソッド | エンドポイント | 説明 |
|---|---|---|
| `POST` | `/admin/keys` | API キーの作成 |
| `GET` | `/admin/keys?tenant_id=xxx` | テナントのキー一覧 |
| `DELETE` | `/admin/keys/{key}` | API キーの無効化 |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | 使用量の照会 |

### CLI キー管理

CLI スクリプトで直接キーを管理することもできます（AWS 認証情報が必要）：

```bash
# 作成
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# 一覧
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# 無効化
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## 設定

| CDK Context | デフォルト | 説明 |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | 管理エンドポイント用の admin API キー |
| `bedrockRegion` | スタックのリージョン | Bedrock API 呼び出し用の AWS リージョン |

`-c` フラグで指定：

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## アーキテクチャ

| コンポーネント | 技術 |
|---|---|
| インフラ | AWS CDK (TypeScript) |
| 推論 Lambda | Python 3.12, ARM64, 256 MB, 5 分タイムアウト |
| 管理 Lambda | Python 3.14, ARM64, 256 MB, 30 秒タイムアウト |
| API キーテーブル | DynamoDB (オンデマンド) |
| 使用量テーブル | DynamoDB (オンデマンド, 90 日 TTL) |
| API Gateway | REST API、CORS 対応 |

## プロジェクト構成

```
├── cdk/                    # CDK インフラ
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # 推論 Lambda
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
    └── manage_keys.py      # CLI キー管理
```

## ライセンス

AGPL-3.0
