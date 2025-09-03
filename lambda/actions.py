import json

from github import Auth as GithubAuth
from github import Github

import slack_notify as notify
import utilities as u

# Event handler registry
EVENT_HANDLERS = {}


def github_event(event_name):
    """Decorator to register a function as a GitHub event handler."""

    def decorator(fn):
        EVENT_HANDLERS[event_name] = fn
        return fn

    return decorator


@github_event("ping")
def ping(event):
    return {"status": "pong"}


@github_event("repository.privatized")
def handle_privatized(json_body, logger, secrets):
    """
    When a repository is privatized, revert it back to public. Log the sender that triggered the event.
    """
    sender = json_body.get("sender", {}).get("login", "unknown")
    logger.info(f"Privatized event triggered by: {sender}")

    # Revert the repository privatization
    repo_id = json_body.get("repository", {}).get("id")
    if not repo_id:
        logger.error("Repository ID not found")
        return {"status": "error", "message": "Repository ID not found"}, 400

    github_client = Github(auth=GithubAuth.Token(secrets["GITHUB_TOKEN"]))
    if not u.revert_repository_privatization(repo_id, github_client):
        logger.error("Failed to revert repository privatization")
        return {"status": "error", "message": "Failed to revert repository privatization"}, 500

    return {"status": "privatized event processed"}


@github_event("repository_ruleset")
def handle_repository_ruleset(event):
    return {"status": "repository ruleset event processed"}
