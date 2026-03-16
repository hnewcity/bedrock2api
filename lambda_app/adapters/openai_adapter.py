"""OpenAI Chat Completions API adapter for Bedrock Converse API."""

import json
import time
import uuid


def to_bedrock_params(api_request: dict) -> dict:
    """Convert OpenAI Chat Completions request to Bedrock Converse parameters.

    Returns dict with keys: messages, system (optional), inference_config (optional).
    """
    raw_messages = api_request.get("messages", [])
    system_parts = []
    messages = []

    for msg in raw_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            text = content if isinstance(content, str) else str(content)
            system_parts.append({"text": text})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": _to_converse_content(content)})
        else:
            messages.append({"role": "user", "content": _to_converse_content(content)})

    result = {"messages": messages}
    if system_parts:
        result["system"] = system_parts

    # --- inferenceConfig ---
    config = {}
    max_tokens = (
        api_request.get("max_tokens")
        or api_request.get("max_completion_tokens")
        or 4096
    )
    config["maxTokens"] = max_tokens

    if "temperature" in api_request:
        config["temperature"] = api_request["temperature"]
    if "top_p" in api_request:
        config["topP"] = api_request["top_p"]
    if "stop" in api_request:
        stop = api_request["stop"]
        if isinstance(stop, str):
            config["stopSequences"] = [stop]
        elif isinstance(stop, list):
            config["stopSequences"] = stop
    if config:
        result["inference_config"] = config

    return result


def to_api_response(converse_resp: dict, model_name: str) -> dict:
    """Convert Bedrock Converse response to OpenAI Chat Completions format."""
    output_message = converse_resp.get("output", {}).get("message", {})
    converse_content = output_message.get("content", [])

    text = "".join(block.get("text", "") for block in converse_content if "text" in block)

    stop_reason = converse_resp.get("stopReason", "end_turn")
    finish_reason = _map_stop_reason(stop_reason)

    usage = converse_resp.get("usage", {})

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": usage.get("inputTokens", 0),
            "completion_tokens": usage.get("outputTokens", 0),
            "total_tokens": usage.get("inputTokens", 0) + usage.get("outputTokens", 0),
        },
    }


def to_stream_events(event_key: str, event_data: dict, model_name: str) -> list[str]:
    """Convert Converse stream event to OpenAI SSE chunks."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"

    if event_key == "messageStart":
        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }
        return [f"data: {json.dumps(chunk)}\n\n"]

    if event_key == "contentBlockDelta":
        delta = event_data.get("delta", {})
        if "text" in delta:
            chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": delta["text"]},
                        "finish_reason": None,
                    }
                ],
            }
            return [f"data: {json.dumps(chunk)}\n\n"]

    if event_key == "messageStop":
        stop_reason = event_data.get("stopReason", "end_turn")
        finish_reason = _map_stop_reason(stop_reason)
        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": finish_reason,
                }
            ],
        }
        return [f"data: {json.dumps(chunk)}\n\n", "data: [DONE]\n\n"]

    return []


def _to_converse_content(content) -> list[dict]:
    """Normalize message content to Converse content block format."""
    if isinstance(content, str):
        return [{"text": content}]
    if isinstance(content, list):
        blocks = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                blocks.append({"text": part.get("text", "")})
            elif isinstance(part, str):
                blocks.append({"text": part})
        return blocks or [{"text": ""}]
    return [{"text": str(content)}]


def _map_stop_reason(stop_reason: str) -> str:
    mapping = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
        "content_filtered": "stop",
    }
    return mapping.get(stop_reason, "stop")
