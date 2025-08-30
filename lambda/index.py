import os
import utilities

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext

SECRETS = os.environ.get("SECRETS")

app = APIGatewayRestResolver()
logger = Logger()

@app.get("/ping")
def ping():
    return {"status": "pong"}

@app.post("/webhooks")
def webhooks():
    # Retrieve secrets
    logger.debug("SECRETS")
    secrets = parameters.get_secret(SECRETS, transform="json", max_age=300)
    # Verify signature
    logger.debug(app.current_event["body"])
    logger.debug(app.current_event["headers"].get("X-Hub-Signature-256", ""))
    logger.debug(secrets)
    if not utilities.verify_signature(
        payload_body=app.current_event["body"],
        secret_token=secrets["GITHUB_WEBHOOK_SECRET"],
        signature_header=app.current_event["headers"].get("X-Hub-Signature-256", ""),
    ):
        return {"status": "invalid signature"}, 403

    # Route based on event
    gh_event = app.current_event["headers"].get("X-GitHub-Event", "")
    logger.info(f"GitHub event received: {gh_event}")
    if gh_event == "ping":
        logger.info("Ping event received")
    elif gh_event == "privatized":
        logger.info("Privatized event received")
    elif gh_event == "push":
        # Handle push event
        pass
    elif gh_event == "pull_request":
        # Handle pull request event
        pass
    elif gh_event == "repository_ruleset":
        logger.info("Repository ruleset event received")
        pass

    return {"status": "success"}

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
def handler(event: dict, context: LambdaContext) -> dict:
    logger.info("Handler started")
    return app.resolve(event, context)
