"""Boto3 Bedrock Runtime client wrapper using the Converse API."""

import os

import boto3


class BedrockClient:
    def __init__(self):
        region = os.environ.get("AWS_BEDROCK_REGION", os.environ.get("AWS_REGION", "us-east-1"))
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def converse(self, model_id: str, messages: list, system: list | None = None,
                 inference_config: dict | None = None) -> dict:
        """Synchronous model invocation via Converse API."""
        kwargs = {"modelId": model_id, "messages": messages}
        if system:
            kwargs["system"] = system
        if inference_config:
            kwargs["inferenceConfig"] = inference_config
        return self._client.converse(**kwargs)

    def converse_stream(self, model_id: str, messages: list, system: list | None = None,
                        inference_config: dict | None = None):
        """Streaming model invocation via Converse API.

        Yields (event_key, event_data) tuples from the response stream.
        Each stream event is a dict with one key, e.g. {"contentBlockDelta": {...}}.
        """
        kwargs = {"modelId": model_id, "messages": messages}
        if system:
            kwargs["system"] = system
        if inference_config:
            kwargs["inferenceConfig"] = inference_config
        response = self._client.converse_stream(**kwargs)
        for event in response["stream"]:
            for key, value in event.items():
                yield key, value
