"""
database/db.py
--------------
Defines the SQLAlchemy ORM models for the ingestion service:
  - SourceEvent: raw webhook payloads from GitHub, Jira, and Slack
  - ChangeEvent: consolidated change records produced by the processor

The engine and session factory are imported from emiva_core.
Table creation is handled outside of runtime startup (e.g. via a
migration script).
"""

import uuid
from sqlalchemy import Column, String, JSON, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class SourceEvent(Base):
    """Raw, unprocessed webhook payload from an external source."""
    __tablename__ = 'source_event'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=False)
    source_type = Column(String(50), nullable=False)  # github, slack, jira
    raw_payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChangeEvent(Base):
    """Consolidated change record derived from one or more SourceEvents."""
    __tablename__ = 'change_event'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=False)
    source_event_id = Column(String(36), ForeignKey('source_event.id'), nullable=True)
    external_ticket_id = Column(String(100))
    title = Column(String(255))
    description = Column(Text)
    ticket_url = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Metadata for internal tracking
    change_type = Column(String(50))   # bug_fix, feature, chore, docs, unknown
    component = Column(String(100))
    severity = Column(String(50))      # low, medium, high, critical
    linked_issues = Column(JSON)       # List of Jira keys (historical context)
    linked_prs = Column(JSON)          # List of PR numbers
    linked_threads = Column(JSON)      # List of Slack thread IDs
    actors = Column(JSON)              # List of unique actor names/IDs
    raw_signals = Column(JSON)         # Consistently structured flags
    processed = Column(Boolean, default=False)  # For Stage 3 analysis


from emiva_core.db.database import SessionLocal as Session


def save_raw_data(source_type: str, raw_payload: dict, workspace_id: str = "default-workspace") -> None:
    """Persist a raw webhook payload as a new SourceEvent row."""
    session = Session()
    new_event = SourceEvent(
        source_type=source_type,
        raw_payload=raw_payload,
        workspace_id=workspace_id,
    )
    session.add(new_event)
    session.commit()
    session.close()
