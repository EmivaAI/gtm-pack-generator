import uuid
from sqlalchemy import create_engine, Column, String, JSON, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

Base = declarative_base()

class SourceEvent(Base):
    __tablename__ = 'source_event'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=False)
    source_type = Column(String(50), nullable=False) # github, slack, jira
    raw_payload = Column(JSON, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ChangeEvent(Base):
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
    change_type = Column(String(50)) # bug_fix, feature, chore, docs, unknown
    component = Column(String(100))
    severity = Column(String(50)) # low, medium, high, critical
    linked_issues = Column(JSON) # List of Jira keys (historical context)
    linked_prs = Column(JSON) # List of PR numbers
    linked_threads = Column(JSON) # List of Slack thread IDs
    actors = Column(JSON) # List of unique actor names/IDs
    raw_signals = Column(JSON) # Consistently structured flags
    processed = Column(Boolean, default=False) # For Stage 3 analysis

from config import config

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    # Ensure directory exists for SQLite
    if config.DATABASE_URL.startswith('sqlite:///'):
        db_path = config.DATABASE_URL.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
    Base.metadata.create_all(engine)

def save_raw_data(source_type, raw_payload, workspace_id="default-workspace"):
    session = Session()
    new_event = SourceEvent(
        source_type=source_type, 
        raw_payload=raw_payload, 
        workspace_id=workspace_id
    )
    session.add(new_event)
    session.commit()
    session.close()
