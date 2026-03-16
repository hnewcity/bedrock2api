import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class Bedrock2ApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // ── DynamoDB Tables ──

    const keysTable = new dynamodb.Table(this, "ApiKeysTable", {
      tableName: "bedrock2api-api-keys",
      partitionKey: { name: "api_key", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    keysTable.addGlobalSecondaryIndex({
      indexName: "tenant_id-index",
      partitionKey: {
        name: "tenant_id",
        type: dynamodb.AttributeType.STRING,
      },
    });

    const usageTable = new dynamodb.Table(this, "UsageTable", {
      tableName: "bedrock2api-usage",
      partitionKey: {
        name: "tenant_id",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: { name: "date_model", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl",
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── Inference Lambda ──

    const inferenceLambda = new lambda.Function(this, "InferenceLambda", {
      functionName: "bedrock2api-inference",
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../lambda_app")),
      memorySize: 256,
      timeout: cdk.Duration.minutes(5),
      environment: {
        KEYS_TABLE: keysTable.tableName,
        USAGE_TABLE: usageTable.tableName,
        AWS_BEDROCK_REGION:
          this.node.tryGetContext("bedrockRegion") || this.region,
      },
    });

    // Bedrock permissions
    inferenceLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:Converse",
          "bedrock:ConverseStream",
        ],
        resources: ["*"],
      }),
    );

    keysTable.grantReadData(inferenceLambda);
    usageTable.grantReadWriteData(inferenceLambda);

    // ── Management Lambda ──

    const adminApiKey =
      this.node.tryGetContext("adminApiKey") || "change-me-admin-key";

    const managementLambda = new lambda.Function(this, "ManagementLambda", {
      functionName: "bedrock2api-management",
      runtime: lambda.Runtime.PYTHON_3_14,
      architecture: lambda.Architecture.ARM_64,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(
        path.join(__dirname, "../../lambda_management"),
      ),
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      environment: {
        KEYS_TABLE: keysTable.tableName,
        USAGE_TABLE: usageTable.tableName,
        ADMIN_API_KEY: adminApiKey,
      },
    });

    keysTable.grantReadWriteData(managementLambda);
    usageTable.grantReadData(managementLambda);

    // ── API Gateway ──

    const api = new apigateway.RestApi(this, "Api", {
      restApiName: "bedrock2api",
      deployOptions: { stageName: "prod" },
    });

    // Inference routes
    const v1 = api.root.addResource("v1");
    const messagesResource = v1.addResource("messages");
    const chatResource = v1.addResource("chat");
    const completionsResource = chatResource.addResource("completions");

    const inferenceIntegration = new apigateway.LambdaIntegration(
      inferenceLambda,
    );

    messagesResource.addMethod("POST", inferenceIntegration);
    completionsResource.addMethod("POST", inferenceIntegration);

    messagesResource.addCorsPreflight({
      allowOrigins: ["*"],
      allowHeaders: [
        "Content-Type",
        "x-api-key",
        "Authorization",
        "anthropic-version",
      ],
      allowMethods: ["POST", "OPTIONS"],
    });
    completionsResource.addCorsPreflight({
      allowOrigins: ["*"],
      allowHeaders: [
        "Content-Type",
        "x-api-key",
        "Authorization",
        "anthropic-version",
      ],
      allowMethods: ["POST", "OPTIONS"],
    });

    // Management routes
    const adminResource = api.root.addResource("admin");
    const keysResource = adminResource.addResource("keys");
    const keyResource = keysResource.addResource("{key}");
    const usageResource = adminResource.addResource("usage");

    const mgmtIntegration = new apigateway.LambdaIntegration(managementLambda);

    keysResource.addMethod("POST", mgmtIntegration);
    keysResource.addMethod("GET", mgmtIntegration);
    keyResource.addMethod("DELETE", mgmtIntegration);
    usageResource.addMethod("GET", mgmtIntegration);

    keysResource.addCorsPreflight({
      allowOrigins: ["*"],
      allowMethods: ["GET", "POST", "OPTIONS"],
    });
    keyResource.addCorsPreflight({
      allowOrigins: ["*"],
      allowMethods: ["DELETE", "OPTIONS"],
    });
    usageResource.addCorsPreflight({
      allowOrigins: ["*"],
      allowMethods: ["GET", "OPTIONS"],
    });

    // ── Outputs ──

    new cdk.CfnOutput(this, "ApiUrl", {
      value: api.url,
      description: "API Gateway URL (inference + management)",
    });
  }
}
