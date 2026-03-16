"""Management Lambda — API key CRUD and usage queries."""

import json
import os
import time
import uuid
from datetime import datetime, timezone

import boto3

_dynamodb = boto3.resource("dynamodb")
_keys_table = _dynamodb.Table(os.environ.get("KEYS_TABLE", "bedrock2api-api-keys"))
_usage_table = _dynamodb.Table(os.environ.get("USAGE_TABLE", "bedrock2api-usage"))
_ADMIN_KEY = os.environ.get("ADMIN_API_KEY", "")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, x-api-key, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
}


def handler(event, context):
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    headers = event.get("headers", {}) or {}

    if method == "OPTIONS":
        return _response(200, {"message": "ok"})

    # Admin auth
    if not _check_admin(headers):
        return _response(403, {"error": "Invalid or missing admin API key."})

    # Route
    if path == "/admin/keys" and method == "POST":
        return _create_key(event)
    elif path == "/admin/keys" and method == "GET":
        return _list_keys(event)
    elif path.startswith("/admin/keys/") and method == "DELETE":
        key = path.split("/admin/keys/", 1)[1]
        return _disable_key(key)
    elif path == "/admin/usage" and method == "GET":
        return _query_usage(event)
    else:
        return _response(404, {"error": f"Unknown route: {method} {path}"})


def _check_admin(headers: dict) -> bool:
    if not _ADMIN_KEY:
        return True  # No admin key configured = open access
    lower = {k.lower(): v for k, v in headers.items()}
    key = lower.get("x-api-key", "")
    if not key:
        auth = lower.get("authorization", "")
        if auth.startswith("Bearer "):
            key = auth[7:].strip()
    return key == _ADMIN_KEY


def _create_key(event):
    body = json.loads(event.get("body", "{}") or "{}")
    tenant_id = body.get("tenant_id")
    tenant_name = body.get("tenant_name", "")
    rate_limit = body.get("rate_limit", 0)
    allowed_models = body.get("allowed_models", [])

    if not tenant_id:
        return _response(400, {"error": "tenant_id is required."})

    api_key = f"sk-{uuid.uuid4().hex}"
    item = {
        "api_key": api_key,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "rate_limit": rate_limit,
        "allowed_models": allowed_models,
    }
    _keys_table.put_item(Item=item)

    return _response(201, {"api_key": api_key, **item})


def _list_keys(event):
    params = event.get("queryStringParameters", {}) or {}
    tenant_id = params.get("tenant_id")

    if not tenant_id:
        return _response(400, {"error": "tenant_id query parameter is required."})

    resp = _keys_table.query(
        IndexName="tenant_id-index",
        KeyConditionExpression="tenant_id = :tid",
        ExpressionAttributeValues={":tid": tenant_id},
    )
    items = resp.get("Items", [])
    # Mask full key in listing
    for item in items:
        key = item.get("api_key", "")
        if len(key) > 8:
            item["api_key"] = key[:7] + "..." + key[-4:]

    return _response(200, {"keys": items})


def _disable_key(api_key: str):
    _keys_table.update_item(
        Key={"api_key": api_key},
        UpdateExpression="SET is_active = :val",
        ExpressionAttributeValues={":val": False},
    )
    return _response(200, {"message": f"Key disabled.", "api_key": api_key})


def _query_usage(event):
    params = event.get("queryStringParameters", {}) or {}
    tenant_id = params.get("tenant_id")
    start_date = params.get("start_date", "2000-01-01")
    end_date = params.get("end_date", "2099-12-31")

    if not tenant_id:
        return _response(400, {"error": "tenant_id query parameter is required."})

    resp = _usage_table.query(
        KeyConditionExpression=(
            "tenant_id = :tid AND date_model BETWEEN :start AND :end"
        ),
        ExpressionAttributeValues={
            ":tid": tenant_id,
            ":start": start_date,
            ":end": end_date + "~",  # ~ sorts after all printable chars
        },
    )

    return _response(200, {"usage": resp.get("Items", [])})


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {**CORS_HEADERS, "Content-Type": "application/json"},
        "body": json.dumps(body, default=str),
    }
