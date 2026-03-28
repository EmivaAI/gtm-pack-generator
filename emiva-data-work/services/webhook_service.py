"""
services/webhook_service.py
----------------------------
Orchestrates the ingestion pipeline for all incoming webhook events.

On each call to process_webhook_data():
  1. Persists the raw payload as a new SourceEvent via database.db.save_raw_data().
  2. Immediately triggers ChangeEventProcessor to convert unprocessed SourceEvents
     into consolidated ChangeEvent records.

This real-time trigger ensures that the change_event table is always up-to-date
after every webhook delivery, with no manual processing step required.
"""

from database.db import save_raw_data
from services.change_event_processor import process_unprocessed_events
from emiva_core.core.logger import setup_logger

logger = setup_logger("ingestion.services.webhook")


class WebhookService:
    @staticmethod
    def process_webhook_data(source_type: str, raw_payload: dict, workspace_id: str = "default-workspace") -> tuple:
        """
        Process an incoming webhook payload end-to-end.

        Saves the raw payload and immediately runs the change-event processor.
        Processing errors are logged but do not cause a 5xx response — the raw
        data is already safely stored and can be reprocessed later.

        Args:
            source_type:  One of 'github', 'slack', or 'jira'.
            raw_payload:  The parsed JSON body from the webhook request.
            workspace_id: Tenant identifier (default: 'default-workspace').

        Returns:
            A (response_dict, status_code) tuple.
        """
        # 1. Save raw data
        save_raw_data(source_type, raw_payload, workspace_id=workspace_id)

        # 2. Automatically trigger processing
        try:
            process_unprocessed_events()
        except Exception as e:
            logger.error("Automatic processing failed: %s", e)

        return {"status": "success"}, 200


webhook_service = WebhookService()
