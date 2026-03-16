"""API key authentication via DynamoDB."""

import os
import time

import boto3

_cache: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 60  # seconds

_table_name = os.environ.get("KEYS_TABLE", "bedrock2api-api-keys")
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_table_name)


def authenticate_request(headers: dict) -> tuple[dict | None, dict | None]:
    """Authenticate a request by API key.

    Returns (tenant_info, None) on success or (None, error_response) on failure.
    """
    api_key = _extract_api_key(headers)
    if not api_key:
        return None, {
            "error": {
                "type": "authentication_error",
                "message": "Missing API key. Provide via x-api-key header or Authorization: Bearer <key>.",
            }
        }

    # Check cache
    now = time.time()
    if api_key in _cache:
        cached, ts = _cache[api_key]
        if now - ts < _CACHE_TTL:
            if not cached.get("is_active", False):
                return None, {
                    "error": {
                        "type": "authentication_error",
                        "message": "API key is inactive.",
                    }
                }
            return cached, None

    # Lookup in DynamoDB
    try:
        resp = _table.get_item(Key={"api_key": api_key})
    except Exception as e:
        return None, {
            "error": {
                "type": "api_error",
                "message": f"Auth lookup failed: {e}",
            }
        }

    item = resp.get("Item")
    if not item:
        return None, {
            "error": {
                "type": "authentication_error",
                "message": "Invalid API key.",
            }
        }

    # Cache the result
    _cache[api_key] = (item, now)

    if not item.get("is_active", False):
        return None, {
            "error": {
                "type": "authentication_error",
                "message": "API key is inactive.",
            }
        }

    return item, None


def _extract_api_key(headers: dict) -> str | None:
    """Extract API key from headers (case-insensitive)."""
    lower = {k.lower(): v for k, v in headers.items()}

    # x-api-key header takes priority
    if "x-api-key" in lower:
        return lower["x-api-key"]

    # Authorization: Bearer <key>
    auth = lower.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    return None
