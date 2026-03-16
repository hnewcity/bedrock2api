"""Model name to Bedrock inference profile ID mapping."""

# Explicit mapping — each entry is the full inference profile ID.
# Use `apac.` for models available in APAC, `global.` or `jp.` otherwise.
MODEL_MAP = {
    "claude-3-7-sonnet-20250219": "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "claude-3-7-sonnet-latest": "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    # Claude 4
    "claude-sonnet-4-20250514": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
    "claude-sonnet-4-0": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
    # Claude 4.5
    "claude-sonnet-4-5-20250929": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude-sonnet-4-5-latest": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "claude-haiku-4-5-20251001": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "claude-haiku-4-5-latest": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "claude-opus-4-5-20251101": "global.anthropic.claude-opus-4-5-20251101-v1:0",
    "claude-opus-4-5-latest": "global.anthropic.claude-opus-4-5-20251101-v1:0",
    # Claude 4.6
    "claude-sonnet-4-6": "global.anthropic.claude-sonnet-4-6",
    "claude-opus-4-6": "global.anthropic.claude-opus-4-6-v1",
    # Amazon Nova
    "nova-pro": "apac.amazon.nova-pro-v1:0",
    "nova-lite": "apac.amazon.nova-lite-v1:0",
    "nova-micro": "apac.amazon.nova-micro-v1:0",
}

# Default for OpenAI model names
DEFAULT_MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"

OPENAI_MODEL_MAP = {
    "gpt-4o": DEFAULT_MODEL_ID,
    "gpt-4o-mini": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "gpt-4-turbo": DEFAULT_MODEL_ID,
    "gpt-4": DEFAULT_MODEL_ID,
    "gpt-3.5-turbo": "apac.anthropic.claude-3-5-haiku-20241022-v1:0",
}


def resolve_model(name: str) -> tuple[str, str]:
    """Resolve a model name to a Bedrock inference profile ID.

    Returns (inference_profile_id, friendly_name).
    Falls through to raw ID if not found in mapping.
    """
    if name in MODEL_MAP:
        return MODEL_MAP[name], name

    if name in OPENAI_MODEL_MAP:
        return OPENAI_MODEL_MAP[name], name

    # Assume it's already a full inference profile ID
    return name, name
