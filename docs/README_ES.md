# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

Convierte AWS Bedrock en un reemplazo directo de las APIs de Anthropic / OpenAI. Despliega con un solo comando CDK, autentica con claves API y rastrea el uso por tenant automáticamente.

```
Cliente (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (Claves API + seguimiento de uso)
```

## Modelos soportados

| Alias | Modelo Bedrock |
|---|---|
| `claude-sonnet-4-5-latest` | Claude Sonnet 4.5 |
| `claude-opus-4-5-latest` | Claude Opus 4.5 |
| `claude-haiku-4-5-latest` | Claude Haiku 4.5 |
| `claude-sonnet-4-6` | Claude Sonnet 4.6 |
| `claude-opus-4-6` | Claude Opus 4.6 |
| `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| `claude-3-7-sonnet-latest` | Claude 3.7 Sonnet |
| `nova-pro` / `nova-lite` / `nova-micro` | Amazon Nova |

Los nombres de modelos de OpenAI también se mapean automáticamente: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5, etc.

## Inicio rápido

### Requisitos previos

- AWS CLI configurado con acceso a Bedrock
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### Despliegue

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

La salida muestra la URL del API Gateway — esa es la URL base para todas las solicitudes.

### Crear una clave API

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

Respuesta:

```json
{
  "api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "tenant_id": "team-alpha",
  "tenant_name": "Team Alpha"
}
```

## Uso

### Formato Anthropic API

```bash
curl https://<api-url>/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-latest",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "¡Hola!"}]
  }'
```

Con el SDK de Python de Anthropic:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "¡Hola!"}],
)
print(message.content[0].text)
```

### Formato OpenAI API

```bash
curl https://<api-url>/v1/chat/completions \
  -H "Authorization: Bearer sk-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "¡Hola!"}]
  }'
```

Con el SDK de Python de OpenAI:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "¡Hola!"}],
)
print(resp.choices[0].message.content)
```

### Streaming

Ambos endpoints soportan streaming — solo agrega `"stream": true` al cuerpo de la solicitud. Los eventos SSE siguen el formato de API correspondiente (Anthropic u OpenAI).

### Autenticación

Las claves API se pueden pasar mediante cualquiera de estos headers:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## API de administración

Todos los endpoints de administración requieren la clave API de admin.

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/admin/keys` | Crear clave API |
| `GET` | `/admin/keys?tenant_id=xxx` | Listar claves del tenant |
| `DELETE` | `/admin/keys/{key}` | Deshabilitar clave API |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | Consultar uso |

### Gestión de claves por CLI

También puedes gestionar claves directamente con el script CLI (requiere credenciales AWS):

```bash
# Crear
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# Listar
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# Deshabilitar
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## Configuración

| CDK Context | Por defecto | Descripción |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | Clave API de admin para endpoints de gestión |
| `bedrockRegion` | Región del stack | Región AWS para llamadas a Bedrock API |

Pasar mediante el flag `-c`:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## Arquitectura

| Componente | Tecnología |
|---|---|
| Infraestructura | AWS CDK (TypeScript) |
| Lambda de inferencia | Python 3.12, ARM64, 256 MB, timeout 5 min |
| Lambda de gestión | Python 3.14, ARM64, 256 MB, timeout 30 s |
| Tabla de claves API | DynamoDB (bajo demanda) |
| Tabla de uso | DynamoDB (bajo demanda, TTL 90 días) |
| API Gateway | REST API con CORS |

## Estructura del proyecto

```
├── cdk/                    # Infraestructura CDK
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # Lambda de inferencia
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # Lambda de gestión
│   └── handler.py
└── scripts/
    └── manage_keys.py      # Gestión de claves por CLI
```

## Licencia

AGPL-3.0
