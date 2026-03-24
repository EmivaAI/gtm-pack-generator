import uuid
import enum
from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

# ==========================================
# ENUMS
# ==========================================


class SourceType(enum.Enum):
    JIRA = "JIRA"
    GITHUB = "GITHUB"
    SLACK = "SLACK"


class LaunchTier(enum.Enum):
    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"


class LaunchStatus(enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PackStatus(enum.Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    FINALIZED = "FINALIZED"


class AssetType(enum.Enum):
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    SALES_SNIPPET = "SALES_SNIPPET"
    INTERNAL_BRIEF = "INTERNAL_BRIEF"
    CHANGELOG = "CHANGELOG"
    SUPPORT_SNIPPET = "SUPPORT_SNIPPET"


class AssetStatus(enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class ApprovalAction(enum.Enum):
    APPROVED_AS_IS = "APPROVED_AS_IS"
    APPROVED_WITH_EDITS = "APPROVED_WITH_EDITS"
    REJECTED = "REJECTED"


# ==========================================
# BASE & MODELS
# ==========================================


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    brand_profile: Mapped["BrandProfile"] = relationship(
        back_populates="workspace", uselist=False
    )
    audience_segments: Mapped[List["AudienceSegment"]] = relationship(
        back_populates="workspace"
    )


class BrandProfile(Base):
    __tablename__ = "brand_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id"), unique=True
    )
    product_summary: Mapped[Optional[str]] = mapped_column(Text)
    tone_rules: Mapped[Optional[Any]] = mapped_column(JSONB)
    allowed_claims: Mapped[Optional[Any]] = mapped_column(JSONB)
    disallowed_claims: Mapped[Optional[Any]] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="brand_profile")


class AudienceSegment(Base):
    __tablename__ = "audience_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    persona_name: Mapped[str] = mapped_column(String)
    pain_points: Mapped[Optional[Any]] = mapped_column(JSONB)
    desired_outcomes: Mapped[Optional[Any]] = mapped_column(JSONB)
    objections: Mapped[Optional[Any]] = mapped_column(JSONB)

    workspace: Mapped["Workspace"] = relationship(back_populates="audience_segments")


class SourceEvent(Base):
    __tablename__ = "source_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    raw_payload: Mapped[Any] = mapped_column(JSONB)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_events.id"), unique=True
    )
    external_ticket_id: Mapped[Optional[str]] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    ticket_url: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    launch_candidate: Mapped["LaunchCandidate"] = relationship(
        back_populates="change_event", uselist=False
    )


class LaunchCandidate(Base):
    __tablename__ = "launch_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    change_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("change_events.id"), unique=True
    )
    tier: Mapped[LaunchTier] = mapped_column(Enum(LaunchTier))
    score: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[Optional[Any]] = mapped_column(JSONB)
    is_external_safe: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_warnings: Mapped[Optional[Any]] = mapped_column(JSONB)
    status: Mapped[LaunchStatus] = mapped_column(
        Enum(LaunchStatus), default=LaunchStatus.PENDING_REVIEW
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    change_event: Mapped["ChangeEvent"] = relationship(
        back_populates="launch_candidate"
    )
    gtm_pack: Mapped["GtmPack"] = relationship(
        back_populates="launch_candidate", uselist=False
    )


class GtmPack(Base):
    __tablename__ = "gtm_packs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"))
    launch_candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("launch_candidates.id"), unique=True
    )
    status: Mapped[PackStatus] = mapped_column(
        Enum(PackStatus), default=PackStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    launch_candidate: Mapped["LaunchCandidate"] = relationship(
        back_populates="gtm_pack"
    )
    assets: Mapped[List["GtmAsset"]] = relationship(back_populates="pack")


class GtmAsset(Base):
    __tablename__ = "gtm_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gtm_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gtm_packs.id"))
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    audience_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("audience_segments.id"), nullable=True
    )
    content_draft: Mapped[Optional[str]] = mapped_column(Text)
    content_final: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus), default=AssetStatus.DRAFT
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pack: Mapped["GtmPack"] = relationship(back_populates="assets")
    approval_events: Mapped[List["ApprovalEvent"]] = relationship(
        back_populates="asset"
    )


class ApprovalEvent(Base):
    __tablename__ = "approval_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gtm_asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("gtm_assets.id"))
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True)
    )  # Points to your Auth/User table
    action: Mapped[ApprovalAction] = mapped_column(Enum(ApprovalAction))
    edit_diff: Mapped[Optional[Any]] = mapped_column(JSONB)
    comments: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    asset: Mapped["GtmAsset"] = relationship(back_populates="approval_events")
