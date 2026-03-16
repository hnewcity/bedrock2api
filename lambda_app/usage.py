"""Usage tracking via DynamoDB atomic counters."""

import logging
import os
import time
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)

_table_name = os.environ.get("USAGE_TABLE", "bedrock2api-usage")
_dynamodb = boto3.resource("dynamodb")
_table = _dynamodb.Table(_table_name)

_TTL_DAYS = 90


class UsageTracker:
    @staticmethod
    def record_tokens(
        tenant_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record token usage with atomic counters. Never blocks response."""
        try:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sort_key = f"{date_str}#{model_name}"
            ttl_epoch = int(time.time()) + (_TTL_DAYS * 86400)

            _table.update_item(
                Key={
                    "tenant_id": tenant_id,
                    "date_model": sort_key,
                },
                UpdateExpression=(
                    "ADD request_count :one, "
                    "input_tokens :inp, "
                    "output_tokens :out, "
                    "total_tokens :total "
                    "SET #ttl = :ttl"
                ),
                ExpressionAttributeNames={"#ttl": "ttl"},
                ExpressionAttributeValues={
                    ":one": 1,
                    ":inp": input_tokens,
                    ":out": output_tokens,
                    ":total": input_tokens + output_tokens,
                    ":ttl": ttl_epoch,
                },
            )
        except Exception:
            logger.exception("Failed to record usage")
