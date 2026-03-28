"""
connectors/github_connector.py
-------------------------------
Handles incoming webhook events from GitHub.

Webhook integration
~~~~~~~~~~~~~~~~~~~
Register this endpoint in your GitHub repository (or organisation) settings:
    Payload URL : https://<your-host>/webhooks/github
    Content-type: application/json
    Secret      : (optional — add HMAC signature verification if required)
    Events      : Push events, Pull requests (at minimum)

Expected headers
~~~~~~~~~~~~~~~~
    X-GitHub-Event  : The event type, e.g. "push", "pull_request"
    X-GitHub-Delivery: A unique UUID for each delivery (useful for dedup)
    X-Hub-Signature-256: HMAC-SHA256 signature of the payload (if a secret is set)

Payload flow
~~~~~~~~~~~~
Incoming payload → enrich with _github_event header → WebhookService.process_webhook_data()
    → saved as SourceEvent(source_type='github') → ChangeEventProcessor reads and converts
      to a ChangeEvent (PR or push record, with optional Jira key linkage).
"""

from emiva_core.core.logger import setup_logger

logger = setup_logger("ingestion.connectors.github")


def handle_github_webhook(data: dict, headers) -> tuple:
    """
    Entry point for POST /webhooks/github.

    Extracts the GitHub event type from the X-GitHub-Event header, enriches
    the payload with a '_github_event' key so downstream processors can
    differentiate push events from pull-request events, then delegates to
    WebhookService for persistence and processing.

    Args:
        data:    Parsed JSON body of the webhook payload.
        headers: HTTP request headers (must include X-GitHub-Event).

    Returns:
        A (response_dict, status_code) tuple.
    """
    from services.webhook_service import webhook_service

    event_type = headers.get('X-GitHub-Event', 'unknown')
    logger.info("[GitHub] Received event type: %s", event_type)

    # Inject event type so the processor can differentiate push vs PR events
    enriched = {**data, "_github_event": event_type}
    return webhook_service.process_webhook_data('github', enriched)
