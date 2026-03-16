#!/usr/bin/env bash
set -euo pipefail

ADMIN_API_KEY="${ADMIN_API_KEY:-}"
BEDROCK_REGION="${BEDROCK_REGION:-}"

if [ -z "$ADMIN_API_KEY" ]; then
  read -rp "Enter admin API key: " ADMIN_API_KEY
fi

if [ -z "$ADMIN_API_KEY" ] || [ "$ADMIN_API_KEY" = "change-me-admin-key" ]; then
  echo "Error: Please set a valid ADMIN_API_KEY"
  exit 1
fi

CDK_DIR="$(cd "$(dirname "$0")/../cdk" && pwd)"

cd "$CDK_DIR"
npm install --silent

CONTEXT="-c adminApiKey=$ADMIN_API_KEY"
[ -n "$BEDROCK_REGION" ] && CONTEXT="$CONTEXT -c bedrockRegion=$BEDROCK_REGION"

npx cdk bootstrap $CONTEXT
npx cdk deploy $CONTEXT --require-approval never
