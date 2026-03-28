"""
connectors/slack_connector.py
------------------------------
Handles incoming webhook events from Slack via the Slack Events API.

Webhook integration
~~~~~~~~~~~~~~~~~~~
1. Create a Slack App at https://api.slack.com/apps
2. Enable "Event Subscriptions" and set the Request URL to:
       https://<your-host>/webhooks/slack
3. Slack will first send a url_verification challenge — this connector
   responds automatically (no manual steps needed).
4. Subscribe to the bot events you need, e.g.:
       message.channels, message.groups (to receive messages)

Expected headers
~~~~~~~~~~~~~~~~
    Content-Type     : application/json
    X-Slack-Signature: Slack request signature for payload verification
    X-Slack-Request-Timestamp: Unix timestamp of the request

Payload structure
~~~~~~~~~~~~~~~~~
    type           : "url_verification" (challenge handshake) or "event_callback"
    challenge      : Present only during url_verification; must be echoed back.
    event.type     : e.g. "message", "app_mention"
    event.text     : Message body (may contain Jira keys like EMIVA-123)
    event.user     : Slack user ID of the sender
    event.channel  : Channel ID
    event.thread_ts: Set if the message is in a thread

Payload flow
~~~~~~~~~~~~
url_verification → immediate challenge response (Slack handshake).
event_callback   → WebhookService.process_webhook_data()
    → saved as SourceEvent(source_type='slack') → ChangeEventProcessor reads
      and converts to a ChangeEvent (linked to a Jira key if one is found,
      otherwise stored as a standalone/orphan signal).
"""

from emiva_core.core.logger import setup_logger

logger = setup_logger("ingestion.connectors.slack")


def handle_slack_webhook(data: dict, headers) -> tuple:
    """
    Entry point for POST /webhooks/slack.

    Handles the Slack URL verification handshake transparently, then routes
    event_callback payloads into WebhookService for persistence and processing.

    Args:
        data:    Parsed JSON body of the Slack event payload.
        headers: HTTP request headers (includes Slack signature for verification).

    Returns:
        A (response_dict, status_code) tuple.
        For url_verification: {"challenge": "<token>"}, 200
        For event payloads:   {"status": "success"}, 200
    """
    from services.webhook_service import webhook_service

    # Slack URL verification challenge — must be echoed back immediately
    if data.get('type') == 'url_verification':
        logger.info("[Slack] Responding to URL verification challenge")
        return {"challenge": data.get('challenge')}, 200

    event_type = data.get('type', 'event_callback')
    if event_type == 'event_callback':
        event_type = data.get('event', {}).get('type', 'unknown')

    logger.info("[Slack] Received event type: %s", event_type)
    return webhook_service.process_webhook_data('slack', data)
