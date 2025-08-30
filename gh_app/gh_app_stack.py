from aws_cdk import (
    CfnOutput,
    Duration,
    Stack,
    aws_apigateway as apigw,
    aws_certificatemanager as acm,
    aws_cloudwatch as cloudwatch,
    aws_lambda as _lambda,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_secretsmanager as secretsmanager,
    aws_wafv2 as wafv2,
)
from constructs import Construct
from aws_cdk.aws_lambda_python_alpha import PythonFunction, BundlingOptions


class GhAppStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, hosted_zone: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Secrets Manager
        secrets = secretsmanager.Secret(
            self,
            "GitHubAppSecret",
            description="GitHub App secrets in toml format",
        )

        # Lambda function
        lambda_fn = PythonFunction(
            self,
            "GhAppLambda",
            bundling=BundlingOptions(
                asset_excludes=[".venv", "venv", ".vscode"],
                # build_args={
                #     "PIP_INDEX_URL": "https://edge.artifactory.ouroath.com:4443/artifactory/api/pypi/pypi-mirror/simple",
                # },
                # Set poetry version inside the container
                # build_args={
                #     "POETRY_VERSION": "1.8.4",
                # },
            ),
            entry="lambda",
            environment={
                "SECRETS": secrets.secret_name,
                "POWERTOOLS_LOG_LEVEL": "debug",
            },
            runtime=_lambda.Runtime.PYTHON_3_13,
            timeout=Duration.minutes(1),
        )

        secrets.grant_read(lambda_fn)

        # API Gateway
        api = apigw.LambdaRestApi(
            self,
            "GhAppApi",
            handler=lambda_fn,
            description="API Gateway for GitHub App Webhooks",
            disable_execute_api_endpoint=True,
        )

        # Route53 hosted zone (assumes hosted zone exists)
        zone = route53.HostedZone.from_lookup(
            self,
            "GhAppHostedZone",
            domain_name=hosted_zone,
        )

        # TLS Certificate for the custom domain
        certificate = acm.Certificate(
            self,
            "GhAppCertificate",
            domain_name=f"scmaestro.{hosted_zone}",
            validation=acm.CertificateValidation.from_dns(zone),
        )

        # Custom domain for API Gateway
        domain = apigw.DomainName(
            self,
            "GhAppDomain",
            domain_name=f"scmaestro.{hosted_zone}",
            certificate=certificate,
        )
        domain.add_base_path_mapping(api)

        # Route53 record pointing to the custom domain
        route53.ARecord(
            self,
            "GhAppApiRecord",
            record_name=f"scmaestro.{hosted_zone}",
            target=route53.RecordTarget.from_alias(targets.ApiGatewayDomain(domain)),
            zone=zone,
        )

        # WAF setup, cut down on the door knockers
        # curl https://api.github.com/meta -s  | jq '.hooks' to get the list of IPs
        ipv4_ip_set = wafv2.CfnIPSet(
            self,
            "IPv4IPSet",
            addresses=[
                "192.30.252.0/22",
                "185.199.108.0/22",
                "140.82.112.0/20",
                "143.55.64.0/20",
                "96.241.177.63/32",  #### REMOVE
            ],
            ip_address_version="IPV4",
            scope="REGIONAL",
            name="AllowedIPv4IPs",
        )

        ipv6_ip_set = wafv2.CfnIPSet(
            self,
            "IPv6IPSet",
            addresses=["2a0a:a440::/29", "2606:50c0::/32"],
            ip_address_version="IPV6",
            scope="REGIONAL",
            name="AllowedIPv6IPs",
        )
        web_acl = wafv2.CfnWebACL(
            self,
            "WebACL",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
            scope="REGIONAL",
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="webACL",
                sampled_requests_enabled=True,
            ),
            rules=[
                wafv2.CfnWebACL.RuleProperty(
                    name="IPv4AllowRule",
                    priority=1,
                    action=wafv2.CfnWebACL.RuleActionProperty(allow={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="IPv4AllowRule",
                        sampled_requests_enabled=True,
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        ip_set_reference_statement=wafv2.CfnWebACL.IPSetReferenceStatementProperty(
                            arn=ipv4_ip_set.attr_arn
                        )
                    ),
                ),
                wafv2.CfnWebACL.RuleProperty(
                    name="IPv6AllowRule",
                    priority=2,
                    action=wafv2.CfnWebACL.RuleActionProperty(allow={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="IPv6AllowRule",
                        sampled_requests_enabled=True,
                    ),
                    statement=wafv2.CfnWebACL.StatementProperty(
                        ip_set_reference_statement=wafv2.CfnWebACL.IPSetReferenceStatementProperty(
                            arn=ipv6_ip_set.attr_arn
                        )
                    ),
                ),
            ],
        )

        # Associate WAF with API Gateway
        wafv2.CfnWebACLAssociation(
            self,
            "WebACLAssociation",
            resource_arn=api.deployment_stage.stage_arn,
            web_acl_arn=web_acl.attr_arn,
        )

        # Create CloudWatch Dashboard to view Lambda Function Metrics
        cw_dashboard = cloudwatch.Dashboard(
            self,
            "Lambda Dashboard",
            dashboard_name="GhecWebhookProcessor",
        )
        # CloudWatch Dashboard Title
        title_widget = cloudwatch.TextWidget(
            markdown=f"# Dashboard: {lambda_fn.function_name}",
            height=1,
            width=24,
        )

        # Create Widgets for CloudWatch Dashboard based on Lambda Function's CloudWatch Metrics
        invocations_widget = cloudwatch.GraphWidget(
            title="Invocations", left=[lambda_fn.metric_invocations()], width=12
        )

        errors_widget = cloudwatch.GraphWidget(
            title="Errors", left=[lambda_fn.metric_errors()], width=12
        )

        duration_widget = cloudwatch.GraphWidget(
            title="Duration", left=[lambda_fn.metric_duration()], width=12
        )

        throttles_widget = cloudwatch.GraphWidget(
            title="Throttles", left=[lambda_fn.metric_throttles()], width=12
        )

        # Create Widget to show last 20 Log Entries
        log_widget = cloudwatch.LogQueryWidget(
            log_group_names=[lambda_fn.log_group.log_group_name],
            query_lines=[
                "fields @timestamp, @message",
                "sort @timestamp desc",
                "limit 20",
            ],
            width=24,
        )

        # Add Widgets to CloudWatch Dashboard
        cw_dashboard.add_widgets(
            title_widget,
            invocations_widget,
            errors_widget,
            duration_widget,
            throttles_widget,
            log_widget,
        )

        # CfnOutput a bootstrapping command for updating the secrets found in secrets.toml
        CfnOutput(
            self,
            "UpdateSecretsCommand",
            value=(
                f"aws secretsmanager update-secret --secret-id {secrets.secret_name} "
                f"--secret-string file://secrets.json --region {self.region}"
            ),
            description="Command to update the secrets in Secrets Manager",
        )
