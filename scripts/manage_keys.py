#!/usr/bin/env python3
"""CLI tool for managing API keys directly via DynamoDB."""

import argparse
import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.environ.get("KEYS_TABLE", "bedrock2api-api-keys")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


def create_key(args):
    api_key = f"sk-{uuid.uuid4().hex}"
    item = {
        "api_key": api_key,
        "tenant_id": args.tenant_id,
        "tenant_name": args.tenant_name or args.tenant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "rate_limit": args.rate_limit,
        "allowed_models": [],
    }
    table.put_item(Item=item)
    print(f"Created API key: {api_key}")
    print(f"  Tenant: {args.tenant_id}")
    print(f"  Name:   {item['tenant_name']}")


def list_keys(args):
    resp = table.query(
        IndexName="tenant_id-index",
        KeyConditionExpression="tenant_id = :tid",
        ExpressionAttributeValues={":tid": args.tenant_id},
    )
    items = resp.get("Items", [])
    if not items:
        print(f"No keys found for tenant: {args.tenant_id}")
        return
    for item in items:
        status = "active" if item.get("is_active") else "inactive"
        print(f"  {item['api_key']}  [{status}]  created={item.get('created_at', '?')}")


def disable_key(args):
    table.update_item(
        Key={"api_key": args.key},
        UpdateExpression="SET is_active = :val",
        ExpressionAttributeValues={":val": False},
    )
    print(f"Disabled key: {args.key}")


def main():
    parser = argparse.ArgumentParser(description="Manage bedrock2api API keys")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-key", help="Create a new API key")
    create.add_argument("--tenant-id", required=True)
    create.add_argument("--tenant-name", default=None)
    create.add_argument("--rate-limit", type=int, default=0)
    create.set_defaults(func=create_key)

    ls = sub.add_parser("list-keys", help="List keys for a tenant")
    ls.add_argument("--tenant-id", required=True)
    ls.set_defaults(func=list_keys)

    disable = sub.add_parser("disable-key", help="Disable an API key")
    disable.add_argument("--key", required=True)
    disable.set_defaults(func=disable_key)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
