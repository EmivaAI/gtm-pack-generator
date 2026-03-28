"""
connectors/jira_connector.py
-----------------------------
Handles incoming webhook events from Jira (Atlassian).

Webhook integration
~~~~~~~~~~~~~~~~~~~
Register this endpoint in Jira:
    Jira Settings → System → WebHooks → Create a WebHook
    URL   : https://<your-host>/webhooks/jira
    Events: Issue created, Issue updated, Issue deleted (at minimum)

Expected headers
~~~~~~~~~~~~~~~~
    Content-Type: application/json
    (Jira does not send a custom event-type header; the event name is
    embedded in the payload as `webhookEvent`.)

Payload fields (key ones)
~~~~~~~~~~~~~~~~~~~~~~~~~
    webhookEvent   : e.g. "jira:issue_created", "jira:issue_updated"
    issue.key      : Jira issue key, e.g. "EMIVA-42"
    issue.fields   : All issue metadata (summary, description, priority, …)
    user           : Actor who triggered the event

Payload flow
~~~~~~~~~~~~
Incoming payload → WebhookService.process_webhook_data()
    → saved as SourceEvent(source_type='jira') → ChangeEventProcessor reads
      and converts to a ChangeEvent (with Jira key, severity, change_type, etc.).
"""

from emiva_core.core.logger import setup_logger

logger = setup_logger("ingestion.connectors.jira")


def handle_jira_webhook(data: dict, headers) -> tuple:
    """
    Entry point for POST /webhooks/jira.

    Reads the event type from the payload (Jira embeds it as 'webhookEvent'),
    logs it for observability, and delegates to WebhookService for persistence
    and downstream processing.

    Args:
        data:    Parsed JSON body of the Jira webhook payload.
        headers: HTTP request headers.

    Returns:
        A (response_dict, status_code) tuple.
    """
    from services.webhook_service import webhook_service

    event_type = data.get('webhookEvent', 'unknown')
    logger.info("[Jira] Received event type: %s", event_type)
    return webhook_service.process_webhook_data('jira', data)
