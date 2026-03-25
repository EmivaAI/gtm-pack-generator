def handle_github_webhook(data, headers):
    from services.webhook_service import webhook_service
    event_type = headers.get('X-GitHub-Event', 'unknown')
    print(f"[GitHub] Received event type: {event_type}")
    # Inject event type so the processor can differentiate push vs PR events
    enriched = {**data, "_github_event": event_type}
    return webhook_service.process_webhook_data('github', enriched)
