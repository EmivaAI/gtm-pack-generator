def handle_github_webhook(data, headers):
    from services.webhook_service import webhook_service
    event_type = headers.get('X-GitHub-Event', 'unknown')
    return webhook_service.process_webhook_data('github', data)
