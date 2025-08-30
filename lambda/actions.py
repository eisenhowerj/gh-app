def handle_ping(event):
    return {"status": "pong"}


def handle_privatized(event):
    return {"status": "privatized event processed"}


def handle_repository_ruleset(event):
    return {"status": "repository ruleset event processed"}
