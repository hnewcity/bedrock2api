"""Inference Lambda handler for API Gateway integration."""

import base64
import json
import logging

from auth import authenticate_request
from bedrock_client import BedrockClient
from models import resolve_model
from usage import UsageTracker
from adapters import anthropic_adapter, openai_adapter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = BedrockClient()
usage_tracker = UsageTracker()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": (
        "Content-Type, x-api-key, Authorization, anthropic-version"
    ),
    "Access-Control-Allow-Methods": "POST, OPTIONS",
}


def handler(event, context):
    """API Gateway Lambda proxy handler."""
    method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    if method == "OPTIONS":
        return _response(200, {"message": "ok"})

    headers = event.get("headers", {}) or {}

    # Strip API Gateway stage prefix (e.g. /prod/v1/messages -> /v1/messages)
    resource = event.get("resource", path)

    if method == "POST" and resource == "/v1/messages":
        return _handle_messages(event, headers, "anthropic")
    elif method == "POST" and resource == "/v1/chat/completions":
        return _handle_messages(event, headers, "openai")
    else:
        return _response(
            404,
            {
                "error": {
                    "type": "not_found",
                    "message": f"Unknown route: {method} {path}",
                }
            },
        )


def _handle_messages(event, headers, api_format):
    """Handle inference request for both Anthropic and OpenAI formats."""
    tenant, auth_error = authenticate_request(headers)
    if auth_error:
        return _response(401, auth_error)

    try:
        body = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        if not body:
            body = "{}"
        request_data = json.loads(body)
    except Exception as e:
        return _response(
            400,
            {
                "error": {
                    "type": "invalid_request_error",
                    "message": f"Invalid JSON: {e}",
                }
            },
        )

    model_name = request_data.get("model", "")
    bedrock_model_id, friendly_name = resolve_model(model_name)

    adapter = (
        anthropic_adapter if api_format == "anthropic" else openai_adapter
    )
    params = adapter.to_bedrock_params(request_data)
    is_stream = request_data.get("stream", False)

    if is_stream:
        return _handle_stream(
            adapter, bedrock_model_id, friendly_name,
            params, tenant, api_format,
        )
    else:
        return _handle_sync(
            adapter, bedrock_model_id, friendly_name,
            params, tenant,
        )


def _handle_sync(adapter, bedrock_model_id, friendly_name, params, tenant):
    """Handle synchronous (non-streaming) request."""
    try:
        converse_resp = bedrock.converse(
            bedrock_model_id,
            messages=params["messages"],
            system=params.get("system"),
            inference_config=params.get("inference_config"),
        )
    except Exception as e:
        logger.exception("Bedrock converse failed")
        return _response(
            502, {"error": {"type": "api_error", "message": str(e)}},
        )

    usage = converse_resp.get("usage", {})
    usage_tracker.record_tokens(
        tenant_id=tenant["tenant_id"],
        model_name=friendly_name,
        input_tokens=usage.get("inputTokens", 0),
        output_tokens=usage.get("outputTokens", 0),
    )

    api_response = adapter.to_api_response(converse_resp, friendly_name)
    return _response(200, api_response)


def _handle_stream(adapter, bedrock_model_id, friendly_name, params,
                    tenant, api_format):
    """Handle streaming request.

    Collects the full SSE body and returns it. API Gateway does not
    support true server-push streaming, but clients that buffer the
    full response and then parse SSE events will still work correctly.
    """
    input_tokens = 0
    output_tokens = 0
    chunks = []

    try:
        for event_key, event_data in bedrock.converse_stream(
            bedrock_model_id,
            messages=params["messages"],
            system=params.get("system"),
            inference_config=params.get("inference_config"),
        ):
            if event_key == "metadata":
                usage = event_data.get("usage", {})
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)

            sse_events = adapter.to_stream_events(
                event_key, event_data, friendly_name,
            )
            chunks.extend(sse_events)

    except Exception as e:
        logger.exception("Bedrock stream error")
        error_data = json.dumps(
            {"error": {"type": "api_error", "message": str(e)}},
        )
        if api_format == "anthropic":
            chunks.append(f"event: error\ndata: {error_data}\n\n")
        else:
            chunks.append(f"data: {error_data}\n\n")
    finally:
        usage_tracker.record_tokens(
            tenant_id=tenant["tenant_id"],
            model_name=friendly_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    return {
        "statusCode": 200,
        "headers": {
            **CORS_HEADERS,
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
        },
        "body": "".join(chunks),
    }


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            **CORS_HEADERS,
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }
