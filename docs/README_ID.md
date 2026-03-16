# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

Ubah AWS Bedrock menjadi pengganti langsung untuk API Anthropic / OpenAI. Deploy dengan satu perintah CDK, autentikasi dengan API key, dan lacak penggunaan per tenant secara otomatis.

```
Klien (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API key + pelacakan penggunaan)
```

## Model yang Didukung

| Alias | Model Bedrock |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

Nama model OpenAI juga dipetakan secara otomatis: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5, dll.

## Mulai Cepat

### Prasyarat

- AWS CLI yang dikonfigurasi dengan akses Bedrock
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### Deploy

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

Output akan menampilkan URL API Gateway — itu adalah base URL untuk semua request.

### Membuat API Key

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

Respons:

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## Penggunaan

### Format Anthropic API

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Halo!"}]
  }'
```

Dengan Anthropic Python SDK:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Halo!"}],
)
print(message.content[0].text)
```

### Format OpenAI API

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Halo!"}]
  }'
```

Dengan OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Halo!"}],
)
print(resp.choices[0].message.content)
```

### Streaming

Kedua endpoint mendukung streaming — cukup tambahkan `"stream": true` ke body request. Event SSE mengikuti format API masing-masing (Anthropic atau OpenAI).

### Autentikasi

API key dapat dikirim melalui salah satu header berikut:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## API Admin

Semua endpoint admin memerlukan admin API key.

| Metode | Endpoint | Deskripsi |
|---|---|---|
| `POST` | `/admin/keys` | Membuat API key |
| `GET` | `/admin/keys?tenant_id=xxx` | Daftar key tenant |
| `DELETE` | `/admin/keys/{key}` | Menonaktifkan API key |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | Query penggunaan |

### Manajemen Key via CLI

Anda juga dapat mengelola key langsung melalui skrip CLI (memerlukan kredensial AWS):

```bash
# Membuat
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# Daftar
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# Menonaktifkan
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## Konfigurasi

| CDK Context | Default | Deskripsi |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | Admin API key untuk endpoint manajemen |
| `bedrockRegion` | Region stack | Region AWS untuk panggilan Bedrock API |

Kirim melalui flag `-c`:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## Arsitektur

| Komponen | Teknologi |
|---|---|
| Infrastruktur | AWS CDK (TypeScript) |
| Lambda Inferensi | Python 3.12, ARM64, 256 MB, timeout 5 menit |
| Lambda Manajemen | Python 3.14, ARM64, 256 MB, timeout 30 detik |
| Tabel API Key | DynamoDB (on-demand) |
| Tabel Penggunaan | DynamoDB (on-demand, TTL 90 hari) |
| API Gateway | REST API dengan CORS |

## Struktur Proyek

```
├── cdk/                    # Infrastruktur CDK
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # Lambda Inferensi
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # Lambda Manajemen
│   └── handler.py
└── scripts/
    └── manage_keys.py      # Manajemen key via CLI
```

## Lisensi

AGPL-3.0
