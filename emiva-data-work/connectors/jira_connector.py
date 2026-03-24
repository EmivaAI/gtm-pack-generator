def handle_jira_webhook(data, headers):
    from services.webhook_service import webhook_service
    event_type = data.get('webhookEvent', 'unknown')
    return webhook_service.process_webhook_data('jira', data)
