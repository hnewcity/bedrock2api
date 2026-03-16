"""Anthropic Messages API adapter for Bedrock Converse API."""

import json


def to_bedrock_params(api_request: dict) -> dict:
    """Convert Anthropic API request to Bedrock Converse parameters.

    Returns dict with keys: messages, system (optional), inference_config (optional).
    """
    # --- messages ---
    raw_messages = api_request.get("messages", [])
    messages = []
    for msg in raw_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        messages.append({"role": role, "content": _to_converse_content(content)})

    result = {"messages": messages}

    # --- system ---
    system = api_request.get("system")
    if system:
        if isinstance(system, str):
            result["system"] = [{"text": system}]
        elif isinstance(system, list):
            result["system"] = [
                {"text": item["text"]} if isinstance(item, dict) else {"text": str(item)}
                for item in system
            ]

    # --- inferenceConfig ---
    config = {}
    if "max_tokens" in api_request:
        config["maxTokens"] = api_request["max_tokens"]
    if "temperature" in api_request:
        config["temperature"] = api_request["temperature"]
    if "top_p" in api_request:
        config["topP"] = api_request["top_p"]
    if "stop_sequences" in api_request:
        config["stopSequences"] = api_request["stop_sequences"]
    if config:
        result["inference_config"] = config

    return result


def to_api_response(converse_resp: dict, model_name: str) -> dict:
    """Convert Bedrock Converse response to Anthropic Messages API response."""
    output_message = converse_resp.get("output", {}).get("message", {})
    converse_content = output_message.get("content", [])

    # Map Converse content blocks back to Anthropic format
    content = []
    for block in converse_content:
        if "text" in block:
            content.append({"type": "text", "text": block["text"]})

    usage = converse_resp.get("usage", {})
    stop_reason = _map_stop_reason(converse_resp.get("stopReason", "end_turn"))

    return {
        "id": f"msg_{id(converse_resp)}",
        "type": "message",
        "role": "assistant",
        "model": model_name,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": usage.get("inputTokens", 0),
            "output_tokens": usage.get("outputTokens", 0),
        },
    }


def to_stream_events(event_key: str, event_data: dict, model_name: str) -> list[str]:
    """Convert a Converse stream event to Anthropic SSE-formatted strings."""
    events = []

    if event_key == "messageStart":
        # Synthesize message_start envelope
        msg_envelope = {
            "type": "message_start",
            "message": {
                "id": f"msg_{id(event_data)}",
                "type": "message",
                "role": event_data.get("role", "assistant"),
                "model": model_name,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }
        events.append(_sse("message_start", msg_envelope))

    elif event_key == "contentBlockStart":
        idx = event_data.get("contentBlockIndex", 0)
        start_block = event_data.get("start", {})
        if "text" in start_block or not start_block:
            block = {"type": "text", "text": start_block.get("text", "")}
        else:
            block = start_block
        events.append(_sse("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": block,
        }))

    elif event_key == "contentBlockDelta":
        idx = event_data.get("contentBlockIndex", 0)
        delta = event_data.get("delta", {})
        if "text" in delta:
            events.append(_sse("content_block_delta", {
                "type": "content_block_delta",
                "index": idx,
                "delta": {"type": "text_delta", "text": delta["text"]},
            }))

    elif event_key == "contentBlockStop":
        idx = event_data.get("contentBlockIndex", 0)
        events.append(_sse("content_block_stop", {
            "type": "content_block_stop",
            "index": idx,
        }))

    elif event_key == "messageStop":
        stop_reason = _map_stop_reason(event_data.get("stopReason", "end_turn"))
        events.append(_sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": stop_reason, "stop_sequence": None},
            "usage": {"output_tokens": 0},
        }))
        events.append(_sse("message_stop", {"type": "message_stop"}))

    elif event_key == "metadata":
        usage = event_data.get("usage", {})
        events.append(_sse("message_delta", {
            "type": "message_delta",
            "delta": {"stop_reason": None, "stop_sequence": None},
            "usage": {"output_tokens": usage.get("outputTokens", 0)},
        }))

    return events


def _to_converse_content(content) -> list[dict]:
    """Normalize Anthropic content to Converse content block format."""
    if isinstance(content, str):
        return [{"text": content}]
    if isinstance(content, list):
        blocks = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    blocks.append({"text": item["text"]})
                else:
                    # Pass through other block types as-is for future extensibility
                    blocks.append(item)
            elif isinstance(item, str):
                blocks.append({"text": item})
        return blocks
    return [{"text": str(content)}]


def _map_stop_reason(converse_reason: str) -> str:
    """Map Converse stopReason to Anthropic stop_reason."""
    mapping = {
        "end_turn": "end_turn",
        "tool_use": "tool_use",
        "max_tokens": "max_tokens",
        "stop_sequence": "stop_sequence",
        "content_filtered": "end_turn",
    }
    return mapping.get(converse_reason, "end_turn")


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
