from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel

from emiva_core.db.schema import (
    Workspace, BrandProfile, AudienceSegment, ChangeEvent, LaunchCandidate,
    GtmPack, GtmAsset, ApprovalEvent
)
from emiva_core.db.database import get_db

router = APIRouter(prefix="/v1")

# Pydantic models for shared core entities
class WorkspaceCreate(BaseModel):
    name: str

class BrandProfileCreate(BaseModel):
    workspace_id: uuid.UUID
    product_summary: str
    tone_rules: Optional[Any] = None
    allowed_claims: Optional[Any] = None
    disallowed_claims: Optional[Any] = None

class AudienceSegmentCreate(BaseModel):
    workspace_id: uuid.UUID
    persona_name: str
    pain_points: Optional[Any] = None
    desired_outcomes: Optional[Any] = None

class ChangeEventCreate(BaseModel):
    workspace_id: uuid.UUID
    source_event_id: Optional[uuid.UUID] = None
    external_ticket_id: Optional[str] = None
    title: str
    description: str
    ticket_url: Optional[str] = None
    created_at: Optional[datetime] = None

class LaunchCandidateCreate(BaseModel):
    id: Optional[uuid.UUID] = None
    workspace_id: uuid.UUID
    change_event_id: uuid.UUID
    tier: str
    score: float
    reasons: Optional[Any] = None
    is_external_safe: bool = True
    status: str = "PENDING"
    created_at: Optional[datetime] = None

class GtmPackCreate(BaseModel):
    workspace_id: uuid.UUID
    launch_candidate_id: uuid.UUID
    status: str = "DRAFT"
    created_at: Optional[datetime] = None

class GtmAssetCreate(BaseModel):
    gtm_pack_id: uuid.UUID
    asset_type: str
    audience_id: Optional[uuid.UUID] = None
    content_draft: str
    status: str = "DRAFT"
    updated_at: Optional[datetime] = None

class ApprovalEventCreate(BaseModel):
    gtm_asset_id: uuid.UUID
    user_id: uuid.UUID
    action: str
    comments: Optional[str] = None
    edit_diff: Optional[Any] = None
    created_at: Optional[datetime] = None

@router.post("/workspaces")
def create_workspace(data: WorkspaceCreate, db: Session = Depends(get_db)):
    obj = Workspace(name=data.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/brand-profiles")
def create_brand_profile(data: BrandProfileCreate, db: Session = Depends(get_db)):
    obj = BrandProfile(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/audience-segments")
def create_audience_segment(data: AudienceSegmentCreate, db: Session = Depends(get_db)):
    obj = AudienceSegment(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/change-events")
def create_change_event(data: ChangeEventCreate, db: Session = Depends(get_db)):
    obj = ChangeEvent(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/launch-candidates")
def create_launch_candidate(data: LaunchCandidateCreate, db: Session = Depends(get_db)):
    obj = LaunchCandidate(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/gtm-packs")
def create_gtm_pack(data: GtmPackCreate, db: Session = Depends(get_db)):
    obj = GtmPack(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/gtm-assets")
def create_gtm_asset(data: GtmAssetCreate, db: Session = Depends(get_db)):
    obj = GtmAsset(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/approval-events")
def create_approval_event(data: ApprovalEventCreate, db: Session = Depends(get_db)):
    obj = ApprovalEvent(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.post("/reset-db")
def reset_db(db: Session = Depends(get_db)):
    """Drops and recreates all tables. Dangerous - for dev/test seeding only."""
    from emiva_core.db.schema import Base
    from emiva_core.db import engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return {"message": "Database reset successful"}
