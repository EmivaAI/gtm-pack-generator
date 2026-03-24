def handle_slack_webhook(data, headers):
    from services.webhook_service import webhook_service
    
    # Slack URL verification challenge
    if data.get('type') == 'url_verification':
        return {"challenge": data.get('challenge')}, 200
        
    event_type = data.get('type', 'event_callback')
    if event_type == 'event_callback':
        event_type = data.get('event', {}).get('type', 'unknown')
        
    return webhook_service.process_webhook_data('slack', data)
