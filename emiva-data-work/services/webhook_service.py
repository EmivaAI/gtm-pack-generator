from database.db import save_raw_data
from services.change_event_processor import process_unprocessed_events

class WebhookService:
    @staticmethod
    def process_webhook_data(source_type, raw_payload, workspace_id="default-workspace"):
        """
        Process incoming webhook data and persist it to the database.
        Then, immediately trigger the consolidation processor.
        """
        # 1. Save raw data
        save_raw_data(source_type, raw_payload, workspace_id=workspace_id)
        
        # 2. Automatically trigger processing
        try:
            process_unprocessed_events()
        except Exception as e:
            print(f"Automatic processing failed: {e}")
            
        return {"status": "success"}, 200

webhook_service = WebhookService()
