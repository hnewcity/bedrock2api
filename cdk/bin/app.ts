#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { Bedrock2ApiStack } from "../lib/bedrock2api-stack";

const app = new cdk.App();
new Bedrock2ApiStack(app, "Bedrock2ApiStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
