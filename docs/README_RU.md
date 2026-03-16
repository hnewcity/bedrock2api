# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

Превратите AWS Bedrock в полноценную замену API Anthropic / OpenAI. Разверните одной командой CDK, аутентифицируйтесь с помощью API-ключей и автоматически отслеживайте использование по тенантам.

```
Клиент (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (API-ключи + отслеживание использования)
```

## Поддерживаемые модели

| Псевдоним | Модель Bedrock |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

Имена моделей OpenAI также автоматически маппятся: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5 и т.д.

## Быстрый старт

### Предварительные требования

- AWS CLI с настроенным доступом к Bedrock
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### Развёртывание

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

В выводе будет URL API Gateway — это базовый URL для всех запросов.

### Создание API-ключа

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

Ответ:

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## Использование

### Формат Anthropic API

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Привет!"}]
  }'
```

С использованием Anthropic Python SDK:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Привет!"}],
)
print(message.content[0].text)
```

### Формат OpenAI API

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Привет!"}]
  }'
```

С использованием OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Привет!"}],
)
print(resp.choices[0].message.content)
```

### Потоковая передача

Оба эндпоинта поддерживают потоковую передачу — просто добавьте `"stream": true` в тело запроса. SSE-события следуют соответствующему формату API (Anthropic или OpenAI).

### Аутентификация

API-ключ можно передать через любой из заголовков:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## API администрирования

Все административные эндпоинты требуют admin API-ключ.

| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/admin/keys` | Создать API-ключ |
| `GET` | `/admin/keys?tenant_id=xxx` | Список ключей тенанта |
| `DELETE` | `/admin/keys/{key}` | Отключить API-ключ |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | Запрос использования |

### Управление ключами через CLI

Ключами также можно управлять через CLI-скрипт (требуются AWS-учётные данные):

```bash
# Создать
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# Список
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# Отключить
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## Конфигурация

| CDK Context | По умолчанию | Описание |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | Admin API-ключ для управления |
| `bedrockRegion` | Регион стека | AWS-регион для вызовов Bedrock API |

Передача через флаг `-c`:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## Архитектура

| Компонент | Технология |
|---|---|
| Инфраструктура | AWS CDK (TypeScript) |
| Lambda вывода | Python 3.12, ARM64, 256 МБ, таймаут 5 мин |
| Lambda управления | Python 3.14, ARM64, 256 МБ, таймаут 30 сек |
| Таблица API-ключей | DynamoDB (по запросу) |
| Таблица использования | DynamoDB (по запросу, TTL 90 дней) |
| API Gateway | REST API с CORS |

## Структура проекта

```
├── cdk/                    # CDK-инфраструктура
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # Lambda вывода
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # Lambda управления
│   └── handler.py
└── scripts/
    └── manage_keys.py      # CLI-управление ключами
```

## Лицензия

AGPL-3.0
