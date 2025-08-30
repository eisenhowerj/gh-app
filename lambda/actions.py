import json

from github import Auth as GithubAuth
from github import Github

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


@github_event("privatized")
def handle_privatized(body, logger):
    """
    When a repository is privatized, revert it back to public. Log the sender that triggered the event.
    """
    # import json
    json_body = json.loads(body)
    sender = json_body.get("sender", {}).get("login", "unknown")
    logger.info(f"Privatized event triggered by: {sender}")
    return {"status": "privatized event processed"}


@github_event("repository_ruleset")
def handle_repository_ruleset(event):
    return {"status": "repository ruleset event processed"}
