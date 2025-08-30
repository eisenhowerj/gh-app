import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext

import actions
import utilities

SECRETS = os.environ.get("SECRETS")

app = APIGatewayRestResolver()
logger = Logger()


@app.get("/ping")
def ping():
    return {"status": "pong"}


@app.post("/webhooks")
def webhooks():
    # Retrieve secrets from AWS Parameter Store
    secrets = parameters.get_secret(SECRETS, transform="json", max_age=300)
    if not secrets or "GITHUB_WEBHOOK_SECRET" not in secrets:
        logger.error("GITHUB_WEBHOOK_SECRET not found in secrets")
        return {"status": "server error"}, 500

    # Verify GitHub webhook signature
    if not utilities.verify_signature(
        payload_body=app.current_event["body"],
        secret_token=secrets["GITHUB_WEBHOOK_SECRET"],
        signature_header=app.current_event["headers"].get("X-Hub-Signature-256", ""),
    ):
        logger.error("Invalid signature")
        return {"status": "invalid signature"}, 403

    # Get GitHub event type from headers
    gh_event = app.current_event["headers"].get("X-GitHub-Event", "")
    logger.info(f"GitHub event received: {gh_event}")

    # Map supported GitHub events to their handlers (alphabetized)
    events = {
        "ping": actions.handle_ping,
        "privatized": actions.handle_privatized,
        "repository_ruleset": actions.handle_repository_ruleset,
    }

    # Check if event is supported and call handler
    if gh_event in events:
        return events[gh_event](app.current_event["body"])
    else:
        return {"status": "unsupported event"}


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Handler started")
    return app.resolve(event, context)
