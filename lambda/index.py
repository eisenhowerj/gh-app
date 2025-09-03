import json
import os

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext

import actions
import utilities as u

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
    if not u.verify_signature(
        payload_body=app.current_event["body"],
        secret_token=secrets["GITHUB_WEBHOOK_SECRET"],
        signature_header=app.current_event["headers"].get("X-Hub-Signature-256", ""),
    ):
        logger.error("Invalid signature")
        return {"status": "invalid signature"}, 403

    # Get GitHub event type from headers and action from body
    gh_event = app.current_event["headers"].get("X-GitHub-Event", "")
    json_body = json.loads(app.current_event["body"])
    gh_action = json_body.get("action", "")
    logger.info(f"GitHub event received: {gh_event}, action: {gh_action}")
    event_action = f"{gh_event}.{gh_action}"

    # Use the event handler registry from actions.py
    if event_action in actions.EVENT_HANDLERS:
        return actions.EVENT_HANDLERS[event_action](
            json_body, logger=logger
        )
    else:
        return {"status": "unsupported event"}


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Handler started")
    return app.resolve(event, context)
