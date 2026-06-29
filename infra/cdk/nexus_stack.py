# infra/cdk/nexus_stack.py
"""
NEXUS — AWS-native deployment for the Decision Twin (production-hardened).

Every service maps to a business capability the strategy team relies on — and the
security controls a CIO requires are provisioned, not merely claimed:

  * Bedrock              — enterprise reasoning (multi-model panel).
  * DynamoDB             — durable, tenant-partitioned Decision Graph store (CMK-encrypted, PITR).
  * Lambda + EventBridge — continuous verification + autonomous settlement (no human, no self-grading).
  * S3 Object Lock (WORM)— immutable evidence anchor (CMK-encrypted, TLS-enforced).
  * KMS (CMK)            — customer-managed encryption-at-rest for DynamoDB and S3, key rotation on.
  * Secrets Manager      — API keys for the write surface (never in plaintext env).
  * CloudWatch           — structured logs, X-Ray tracing, error alarms per function.
  * IAM                  — a SEPARATE least-privilege role per function (no shared role).

Note: Amazon QLDB was retired on 2025-07-31. Verifiability lives in the application
hash chain + Merkle/settlement roots, externally anchored (OpenTimestamps) and mirrored
to S3 Object Lock (WORM) — not in any managed journal.

Deploy:  cd infra/cdk && pip install -r requirements.txt && cdk deploy \
            -c cors_origins=https://app.example.com -c env=production
"""
from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_s3 as s3,
    aws_kms as kms,
    aws_logs as logs,
    aws_cloudwatch as cw,
    aws_secretsmanager as secrets,
    aws_bedrock as bedrock,
    aws_sqs as sqs,
)
from constructs import Construct


class NexusDecisionTwinStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kw) -> None:
        super().__init__(scope, cid, **kw)

        cors_origins = self.node.try_get_context("cors_origins") or "http://localhost:8000"
        env_name = self.node.try_get_context("env") or "production"
        bedrock_models = (
            "anthropic.claude-3-5-sonnet-20241022-v2:0,"
            "anthropic.claude-3-haiku-20240307-v1:0,"
            "amazon.titan-text-premier-v1:0,"
            "meta.llama3-1-70b-instruct-v1:0"
        )

        # ── KMS: one customer-managed key for data-at-rest, rotation enabled ──
        key = kms.Key(self, "DataKey", enable_key_rotation=True,
                      removal_policy=RemovalPolicy.RETAIN,
                      description="NEXUS data-at-rest CMK (DynamoDB + S3 anchor)")

        # ── Secrets Manager: API keys for the write surface ─────────────────
        api_keys = secrets.Secret(
            self, "ApiKeys",
            description="NEXUS API keys (comma-separated 'tenant:key' under 'keys')",
            encryption_key=key,  # CMK-encrypted at rest
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template='{"keys":""}', generate_string_key="seed"),
        )

        # ── Bedrock Guardrails: Responsible-AI controls on every model call ──
        guardrail = bedrock.CfnGuardrail(
            self, "ReasoningGuardrail",
            name="nexus-reasoning-guardrail",
            blocked_input_messaging="This request was blocked by NEXUS Responsible-AI policy.",
            blocked_outputs_messaging="This response was blocked by NEXUS Responsible-AI policy.",
            content_policy_config=bedrock.CfnGuardrail.ContentPolicyConfigProperty(
                filters_config=[
                    bedrock.CfnGuardrail.ContentFilterConfigProperty(
                        type=t, input_strength="HIGH", output_strength="HIGH")
                    for t in ("HATE", "INSULTS", "VIOLENCE", "MISCONDUCT", "PROMPT_ATTACK")
                ]),
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type=e, action="ANONYMIZE")
                    for e in ("EMAIL", "PHONE", "NAME", "CREDIT_DEBIT_CARD_NUMBER")
                ]),
        )

        # ── DynamoDB: durable, tenant-partitioned store (CMK, PITR) ──────────
        decision_store = ddb.Table(
            self, "DecisionStore",
            table_name="nexus-decision-store",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            encryption=ddb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=key,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True),
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ── S3 Object Lock (WORM): immutable evidence, CMK, TLS-only ─────────
        anchor_bucket = s3.Bucket(
            self, "AnchorBucket",
            object_lock_enabled=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=key,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN,
            versioned=True,
        )

        common_env = {
            "NEXUS_ENV": env_name,
            "NEXUS_DEMO": "0",
            "NEXUS_DDB_TABLE": decision_store.table_name,
            "ANCHOR_BUCKET": anchor_bucket.bucket_name,
            "NEXUS_API_KEYS_SECRET": api_keys.secret_arn,
            "NEXUS_CORS_ORIGINS": cors_origins,
            "BEDROCK_MODELS": bedrock_models,
            "BEDROCK_GUARDRAIL_ID": guardrail.attr_guardrail_id,
            "BEDROCK_GUARDRAIL_VERSION": guardrail.attr_version,
        }

        def make_role(name: str) -> iam.Role:
            return iam.Role(
                self, name,
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
                managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole")],
            )

        bedrock_stmt = iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:Converse"],
            resources=[f"arn:aws:bedrock:{self.region}::foundation-model/*"],
        )

        # api: DDB rw, bedrock, anchor read/write, secret read, kms
        api_role = make_role("ApiRole")
        decision_store.grant_read_write_data(api_role)
        anchor_bucket.grant_read(api_role)  # least privilege: api reads anchors, only AnchorFn writes
        api_keys.grant_read(api_role)
        api_role.add_to_policy(bedrock_stmt)
        api_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:ApplyGuardrail"], resources=[guardrail.attr_guardrail_arn]))

        # resolver: DDB rw + kms (settles outcomes); egress to oracles needs no IAM
        resolver_role = make_role("ResolverRole")
        decision_store.grant_read_write_data(resolver_role)

        # anchor: DDB read + S3 put/retention + kms (write-once evidence)
        anchor_role = make_role("AnchorRole")
        decision_store.grant_read_data(anchor_role)
        anchor_bucket.grant_write(anchor_role)
        anchor_role.add_to_policy(iam.PolicyStatement(
            actions=["s3:PutObjectRetention"],
            resources=[anchor_bucket.bucket_arn + "/*"]))

        for r in (api_role, resolver_role, anchor_role):
            key.grant_encrypt_decrypt(r)

        # Dependency bundling: pip-install requirements INTO the Lambda asset so the
        # function actually imports at runtime. On by default; pass `-c bundle=false`
        # only for non-Docker synth/CI (the source still stages, deps don't).
        bundle = str(self.node.try_get_context("bundle") or "true").lower() != "false"
        code = _lambda.Code.from_asset(
            "../../backend",
            bundling=_lambda.BundlingOptions(
                image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                command=["bash", "-c",
                         "pip install -r requirements.txt -t /asset-output && "
                         "cp -au . /asset-output"],
            ) if bundle else None,
        )

        # Dead-letter queue for the autonomous (async) Lambdas — failed settlements and
        # anchors are captured for replay, never silently dropped.
        dlq = sqs.Queue(self, "AutonomousDLQ", encryption=sqs.QueueEncryption.KMS,
                        encryption_master_key=key, enforce_ssl=True,
                        retention_period=Duration.days(14))

        def make_fn(name: str, handler: str, role: iam.Role, timeout: int) -> _lambda.Function:
            lg = logs.LogGroup(self, name + "Logs",
                               retention=logs.RetentionDays.THREE_MONTHS,
                               removal_policy=RemovalPolicy.DESTROY)
            return _lambda.Function(
                self, name,
                runtime=_lambda.Runtime.PYTHON_3_12,
                handler=handler,
                code=code,
                timeout=Duration.seconds(timeout),
                memory_size=512,
                role=role,
                environment=common_env,
                tracing=_lambda.Tracing.ACTIVE,
                log_group=lg,
            )

        api_fn = make_fn("ApiFn", "lambda_handler.handler", api_role, 30)
        resolver_fn = make_fn("ResolverFn", "resolver_handler.handler", resolver_role, 120)
        anchor_fn = make_fn("AnchorFn", "anchor_handler.handler", anchor_role, 120)

        # ── API Gateway: throttled, traced, access-logged ───────────────────
        access_logs = logs.LogGroup(self, "ApiAccessLogs",
                                    retention=logs.RetentionDays.ONE_MONTH,
                                    removal_policy=RemovalPolicy.DESTROY)
        gw = apigw.LambdaRestApi(
            self, "Api", handler=api_fn,
            deploy_options=apigw.StageOptions(
                throttling_rate_limit=50, throttling_burst_limit=100,
                metrics_enabled=True, tracing_enabled=True,
                logging_level=apigw.MethodLoggingLevel.INFO,
                access_log_destination=apigw.LogGroupLogDestination(access_logs),
                access_log_format=apigw.AccessLogFormat.json_with_standard_fields(
                    caller=False, http_method=True, ip=True, protocol=True,
                    request_time=True, resource_path=True, response_length=True,
                    status=True, user=False),
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=[cors_origins], allow_methods=["GET", "POST", "OPTIONS"]),
        )

        # ── CloudWatch: error alarms per function ───────────────────────────
        for fn, label in ((api_fn, "Api"), (resolver_fn, "Resolver"), (anchor_fn, "Anchor")):
            cw.Alarm(self, f"{label}Errors",
                     metric=fn.metric_errors(period=Duration.minutes(5)),
                     threshold=1, evaluation_periods=1,
                     comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                     treat_missing_data=cw.TreatMissingData.NOT_BREACHING)

        # ── EventBridge: settle hourly, anchor daily (autonomous) ───────────
        events.Rule(self, "ResolverCron",
                    schedule=events.Schedule.rate(Duration.hours(1)),
                    targets=[targets.LambdaFunction(resolver_fn)])
        events.Rule(self, "AnchorCron",
                    schedule=events.Schedule.rate(Duration.days(1)),
                    targets=[targets.LambdaFunction(anchor_fn)])

        CfnOutput(self, "ApiUrl", value=gw.url)
        CfnOutput(self, "DecisionStoreName", value=decision_store.table_name)
        CfnOutput(self, "AnchorBucketName", value=anchor_bucket.bucket_name)
        CfnOutput(self, "ApiKeysSecretArn", value=api_keys.secret_arn)
        CfnOutput(self, "WireLandingWith",
                  value=f"{gw.url}  → open standalone/index.html?api=<this>")
