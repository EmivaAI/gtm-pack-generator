import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.schema import (
    LaunchCandidate, BrandProfile, ChangeEvent, AudienceSegment,
    GtmPack, GtmAsset, AssetType, PackStatus, AssetStatus, LaunchStatus
)
from app.agent.context import build_candidate_context
from app.agent.prompts import (
    internal_brief_prompt, sales_snippet_prompt, support_snippet_prompt,
    external_asset_prompt, changelog_prompt
)
from app.agent.llm import get_llm_instance

logger = logging.getLogger(__name__)

def generate_gtm_pack(db: Session, candidate_id: uuid.UUID) -> GtmPack:
    """
    Main orchestration logic for GTM generation.
    1. Extracts Database Context
    2. Constructs standard Prompt contexts
    3. Triggers LangChain inference for various asset types
    4. Records Dual Variants (RL-Lite) and standard drafts into the db
    """
    # 1. Fetch Candidate and Hierarchy
    candidate = db.scalar(select(LaunchCandidate).where(LaunchCandidate.id == candidate_id))
    if not candidate:
        raise ValueError(f"LaunchCandidate {candidate_id} not found")
        
    change_event = candidate.change_event
    workspace_id = candidate.workspace_id
    
    brand_profile = db.scalar(select(BrandProfile).where(BrandProfile.workspace_id == workspace_id))
    audiences = db.scalars(select(AudienceSegment).where(AudienceSegment.workspace_id == workspace_id)).all()

    # 2. Fetch History (Pillars and Launch History)
    approved_assets = db.scalars(
        select(GtmAsset)
        .join(GtmPack)
        .where(GtmPack.workspace_id == workspace_id)
        .where(GtmAsset.status == AssetStatus.APPROVED)
        .order_by(GtmAsset.updated_at.desc())
        .limit(5)
    ).all()
    approved_pillars = [a.content_final or a.content_draft for a in approved_assets if a.content_final or a.content_draft]

    approved_candidates = db.scalars(
        select(LaunchCandidate)
        .where(LaunchCandidate.workspace_id == workspace_id)
        .where(LaunchCandidate.status == LaunchStatus.APPROVED)
        .order_by(LaunchCandidate.updated_at.desc())
        .limit(3)
    ).all()
    launch_history = [f"{c.change_event.title} (Tier {c.tier.value})" for c in approved_candidates]

    # 3. Context Assembly
    context_str = build_candidate_context(
        candidate, 
        change_event, 
        brand_profile, 
        audiences,
        approved_pillars=approved_pillars,
        launch_history=launch_history
    )
    
    # 3. Create Overarching Pack
    pack = GtmPack(
        workspace_id=workspace_id,
        launch_candidate_id=candidate.id,
        status=PackStatus.DRAFT
    )
    db.add(pack)
    db.flush() # Yield pack.id for asset references
    
    # 4. Generate Internal Assets
    _generate_internal_assets(db, pack.id, context_str)
    
    # 5. Generate External Assets (Dual Variants)
    _generate_external_assets(db, pack.id, context_str)
            
    db.commit()
    logger.info(f"Successfully generated GTM Pack {pack.id} for candidate {candidate_id}")
    return pack

def _generate_internal_assets(db: Session, pack_id: uuid.UUID, context_str: str):
    """Generates standard Internal Briefs and Sales Snippets"""
    # INTERNAL_BRIEF
    try:
        brief_chain = internal_brief_prompt | get_llm_instance()
        res = brief_chain.invoke({"context": context_str})
        db.add(GtmAsset(
            gtm_pack_id=pack_id,
            asset_type=AssetType.INTERNAL_BRIEF,
            content_draft=res.content,
            status=AssetStatus.DRAFT
        ))
    except Exception as e:
        logger.error(f"Failed to generate Internal Brief: {e}")
        
    # SALES_SNIPPET
    try:
        snippet_chain = sales_snippet_prompt | get_llm_instance()
        res = snippet_chain.invoke({"context": context_str})
        db.add(GtmAsset(
            gtm_pack_id=pack_id,
            asset_type=AssetType.SALES_SNIPPET,
            content_draft=res.content,
            status=AssetStatus.DRAFT
        ))
    except Exception as e:
        logger.error(f"Failed to generate Sales Snippet: {e}")

    # SUPPORT_SNIPPET
    try:
        support_chain = support_snippet_prompt | get_llm_instance()
        res = support_chain.invoke({"context": context_str})
        db.add(GtmAsset(
            gtm_pack_id=pack_id,
            asset_type=AssetType.SUPPORT_SNIPPET,
            content_draft=res.content,
            status=AssetStatus.DRAFT
        ))
    except Exception as e:
        logger.error(f"Failed to generate Support Snippet: {e}")

def _generate_external_assets(db: Session, pack_id: uuid.UUID, context_str: str):
    """Generates external assets containing the dual JSON variants (RL-lite)"""
    external_types = [AssetType.EMAIL, AssetType.LINKEDIN, AssetType.CHANGELOG]
    external_chain = external_asset_prompt | get_llm_instance()
    
    for ext_type in external_types:
        try:
            res = external_chain.invoke({
                "context": context_str,
                "asset_type": ext_type.value
            })
            
            # The prompt strict JSON formatter should return a JSON string block
            # like {"variant_a": "...", "variant_b": "..."}.
            db.add(GtmAsset(
                gtm_pack_id=pack_id,
                asset_type=ext_type,
                content_draft=res.content,
                status=AssetStatus.DRAFT
            ))
        except Exception as e:
            logger.error(f"Failed to generate {ext_type.value}: {e}")
