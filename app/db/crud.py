import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.schema import (
    LaunchCandidate,
    BrandProfile,
    AudienceSegment,
    GtmAsset,
    GtmPack,
    AssetType,
    PackStatus,
    AssetStatus,
    LaunchStatus,
)

def get_candidate(db: Session, candidate_id: uuid.UUID) -> Optional[LaunchCandidate]:
    return db.scalar(
        select(LaunchCandidate).where(LaunchCandidate.id == candidate_id)
    )

def get_brand_profile(db: Session, workspace_id: uuid.UUID) -> Optional[BrandProfile]:
    return db.scalar(
        select(BrandProfile).where(BrandProfile.workspace_id == workspace_id)
    )

def get_audience_segments(db: Session, workspace_id: uuid.UUID) -> List[AudienceSegment]:
    return list(db.scalars(
        select(AudienceSegment).where(AudienceSegment.workspace_id == workspace_id)
    ).all())

def get_recent_approved_assets(db: Session, workspace_id: uuid.UUID, limit: int = 5) -> List[GtmAsset]:
    return list(db.scalars(
        select(GtmAsset)
        .join(GtmPack)
        .where(GtmPack.workspace_id == workspace_id)
        .where(GtmAsset.status == AssetStatus.APPROVED)
        .order_by(GtmAsset.updated_at.desc())
        .limit(limit)
    ).all())

def get_recent_approved_candidates(db: Session, workspace_id: uuid.UUID, limit: int = 3) -> List[LaunchCandidate]:
    return list(db.scalars(
        select(LaunchCandidate)
        .where(LaunchCandidate.workspace_id == workspace_id)
        .where(LaunchCandidate.status == LaunchStatus.APPROVED)
        .order_by(LaunchCandidate.updated_at.desc())
        .limit(limit)
    ).all())

def create_gtm_pack(db: Session, workspace_id: uuid.UUID, candidate_id: uuid.UUID, status: PackStatus = PackStatus.DRAFT) -> GtmPack:
    pack = GtmPack(
        workspace_id=workspace_id,
        launch_candidate_id=candidate_id,
        status=status,
    )
    db.add(pack)
    db.flush()
    return pack

def create_gtm_asset(
    db: Session, 
    pack_id: uuid.UUID, 
    asset_type: AssetType, 
    content: str, 
    status: AssetStatus = AssetStatus.DRAFT,
    audience_id: Optional[uuid.UUID] = None
) -> GtmAsset:
    asset = GtmAsset(
        gtm_pack_id=pack_id,
        asset_type=asset_type,
        content_draft=content,
        status=status,
        audience_id=audience_id
    )
    db.add(asset)
    return asset

def get_approved_assets_for_learning(db: Session, workspace_id: uuid.UUID, asset_type: AssetType) -> List[GtmAsset]:
    """Retrieves approved assets for a workspace and type for RL-lite analysis."""
    return list(db.scalars(
        select(GtmAsset)
        .join(GtmPack)
        .where(GtmPack.workspace_id == workspace_id)
        .where(GtmAsset.asset_type == asset_type)
        .where(GtmAsset.status == AssetStatus.APPROVED)
        .where(GtmAsset.content_final.is_not(None))
    ).all())
