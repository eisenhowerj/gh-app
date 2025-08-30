#!/usr/bin/env python3
import aws_cdk as cdk

from gh_app.gh_app_stack import GhAppStack


app = cdk.App()
dev = GhAppStack(
    app,
    "GhAppStackDev",
    env=cdk.Environment(account="871520026406", region="us-east-1"),
    hosted_zone="synthesis.run",
)

app.synth()
