import hashlib
import hmac


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    Returns:
        bool: True if signature is valid, False otherwise.
    """
    if isinstance(payload_body, str):
        payload_body = payload_body.encode("utf-8")
    hash_object = hmac.new(
        secret_token.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
    )
    expected_signature = "sha256=" + hash_object.hexdigest()
    return hmac.compare_digest(expected_signature, signature_header)

def slack_notify_user(user_id, message, slack_client):
    """Send a notification to a Slack user.

    Args:
        user_id: The ID of the user to notify.
        message: The message to send.
        slack_client: An authenticated Slack client instance.
    """
    try:
        slack_client.chat_postMessage(channel=user_id, text=message)
    except Exception as e:
        print(f"Error sending Slack notification: {e}")


def revert_repository_privatization(repo_id, github_client):
    """Revert a repository to public visibility.

    Args:
        repo_id: The ID of the repository to modify.
        github_client: An authenticated GitHub client instance.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    try:
        github_client.repos.update(
            owner=repo_id.owner,
            repo=repo_id.name,
            private=False
        )
        return True
    except Exception as e:
        print(f"Error reverting repository privatization: {e}")
        return False
