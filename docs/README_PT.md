# bedrock2api

🇺🇸 [English](../README.md) • 🇨🇳 [中文](README_CN.md) • 🇯🇵 [日本語](README_JA.md) • 🇰🇷 [한국어](README_KO.md) • 🇷🇺 [Русский](README_RU.md) • 🇪🇸 [Español](README_ES.md) • 🇧🇷 [Português](README_PT.md) • 🇮🇩 [Indonesia](README_ID.md)

---

Transforme o AWS Bedrock em um substituto direto das APIs da Anthropic / OpenAI. Implante com um único comando CDK, autentique com chaves de API e rastreie o uso por tenant automaticamente.

```
Cliente (Anthropic SDK / OpenAI SDK / curl)
  │
  ▼
API Gateway  ──►  Lambda  ──►  AWS Bedrock (Converse API)
  │
  ▼
DynamoDB (Chaves de API + rastreamento de uso)
```

## Modelos suportados

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

Nomes de modelos OpenAI também são mapeados automaticamente: `gpt-4o` → Claude Sonnet 4, `gpt-4o-mini` → Claude Haiku 4.5, etc.

## Início rápido

### Pré-requisitos

- AWS CLI configurado com acesso ao Bedrock
- Node.js >= 18, Python >= 3.12
- AWS CDK CLI (`npm install -g aws-cdk`)

### Implantação

```bash
cd cdk
npm install
npx cdk deploy -c adminApiKey="your-admin-secret"
```

A saída exibe a URL do API Gateway — essa é a URL base para todas as requisições.

### Criar uma chave de API

```bash
curl -X POST https://<api-url>/admin/keys \
  -H "x-api-key: your-admin-secret" \
  -H "Content-Type: application/json" \
  -d '{"tenant_id": "team-alpha", "tenant_name": "Team Alpha"}'
```

Resposta:

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
    "messages": [{"role": "user", "content": "Olá!"}]
  }'
```

Com o SDK Python da Anthropic:

```python
import anthropic

client = anthropic.Anthropic(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

message = client.messages.create(
    model="claude-sonnet-4-5-latest",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Olá!"}],
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
    "messages": [{"role": "user", "content": "Olá!"}]
  }'
```

Com o SDK Python da OpenAI:

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-your-key",
    base_url="https://<api-url>/v1",
)

resp = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Olá!"}],
)
print(resp.choices[0].message.content)
```

### Streaming

Ambos os endpoints suportam streaming — basta adicionar `"stream": true` ao corpo da requisição. Os eventos SSE seguem o formato de API correspondente (Anthropic ou OpenAI).

### Autenticação

Chaves de API podem ser passadas por qualquer um dos headers:

- `x-api-key: sk-your-key`
- `Authorization: Bearer sk-your-key`

## API de administração

Todos os endpoints de administração requerem a chave de API admin.

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/admin/keys` | Criar chave de API |
| `GET` | `/admin/keys?tenant_id=xxx` | Listar chaves do tenant |
| `DELETE` | `/admin/keys/{key}` | Desabilitar chave de API |
| `GET` | `/admin/usage?tenant_id=xxx&start_date=2025-01-01&end_date=2025-01-31` | Consultar uso |

### Gerenciamento de chaves por CLI

Você também pode gerenciar chaves diretamente pelo script CLI (requer credenciais AWS):

```bash
# Criar
python scripts/manage_keys.py create-key --tenant-id team-alpha --tenant-name "Team Alpha"

# Listar
python scripts/manage_keys.py list-keys --tenant-id team-alpha

# Desabilitar
python scripts/manage_keys.py disable-key --key sk-xxxxxxxx
```

## Configuração

| CDK Context | Padrão | Descrição |
|---|---|---|
| `adminApiKey` | `change-me-admin-key` | Chave de API admin para endpoints de gerenciamento |
| `bedrockRegion` | Região da stack | Região AWS para chamadas à API do Bedrock |

Passar via flag `-c`:

```bash
npx cdk deploy -c adminApiKey="my-secret" -c bedrockRegion="us-west-2"
```

## Arquitetura

| Componente | Tecnologia |
|---|---|
| Infraestrutura | AWS CDK (TypeScript) |
| Lambda de inferência | Python 3.12, ARM64, 256 MB, timeout 5 min |
| Lambda de gerenciamento | Python 3.14, ARM64, 256 MB, timeout 30 s |
| Tabela de chaves API | DynamoDB (sob demanda) |
| Tabela de uso | DynamoDB (sob demanda, TTL 90 dias) |
| API Gateway | REST API com CORS |

## Estrutura do projeto

```
├── cdk/                    # Infraestrutura CDK
│   └── lib/bedrock2api-stack.ts
├── lambda_app/             # Lambda de inferência
│   ├── handler.py
│   ├── bedrock_client.py
│   ├── auth.py
│   ├── models.py
│   ├── usage.py
│   └── adapters/
│       ├── anthropic_adapter.py
│       └── openai_adapter.py
├── lambda_management/      # Lambda de gerenciamento
│   └── handler.py
└── scripts/
    └── manage_keys.py      # Gerenciamento de chaves por CLI
```

## Licença

AGPL-3.0
