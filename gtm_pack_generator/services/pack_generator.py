import uuid
import json
from sqlalchemy.orm import Session

from gtm_core.core.logger import setup_logger
from gtm_core.db.schema import (
    GtmPack,
    AssetType,
    AssetStatus,
)
from gtm_pack_generator.agent import context, generators
from gtm_core.db import crud

from gtm_pack_generator.services.learning import get_workspace_preferences

logger = setup_logger(__name__)



def generate_gtm_pack(db: Session, candidate_id: uuid.UUID) -> GtmPack:
    """
    Main orchestration logic for GTM generation.
    1. Extracts Database Context
    2. Constructs standard Prompt contexts
    3. Triggers LangChain inference for various asset types
    4. Records Dual Variants (RL-Lite) and standard drafts into the db
    """
    # 1. Fetch Candidate and Hierarchy
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise ValueError(f"LaunchCandidate {candidate_id} not found")

    change_event = candidate.change_event
    workspace_id = candidate.workspace_id

    brand_profile = crud.get_brand_profile(db, workspace_id)
    audiences = crud.get_audience_segments(db, workspace_id)

    # 2. Fetch History (Pillars and Launch History)
    approved_assets = crud.get_recent_approved_assets(db, workspace_id, limit=5)
    approved_pillars = [
        asset.content_final or asset.content_draft
        for asset in approved_assets
        if asset.content_final or asset.content_draft
    ]

    approved_candidates = crud.get_recent_approved_candidates(db, workspace_id, limit=3)
    launch_history = [
        f"{candidate.change_event.title} (Tier {candidate.tier.value})" for candidate in approved_candidates
    ]

    # 3. Context Assembly
    context_str = context.build_candidate_context(
        candidate,
        change_event,
        brand_profile,
        audiences,
        approved_pillars,
        launch_history,
    )

    # 3. Create Overarching Pack
    pack = crud.create_gtm_pack(db, workspace_id, candidate.id)

    # 4. Generate Internal Assets
    _generate_internal_assets(db, pack.id, context_str)

    # 5. Generate External Assets (Dual Variants with RL-lite preference)
    _generate_external_assets(db, workspace_id, pack.id, context_str)

    db.commit()
    logger.info(
        f"Successfully generated GTM Pack {pack.id} for candidate {candidate_id}"
    )
    return pack


def _generate_internal_assets(db: Session, pack_id: uuid.UUID, context_str: str):
    """Orchestrates generation of all standard Internal assets"""
    _generate_internal_brief(db, pack_id, context_str)
    _generate_sales_snippet(db, pack_id, context_str)
    _generate_support_snippet(db, pack_id, context_str)


def _generate_internal_brief(db: Session, pack_id: uuid.UUID, context_str: str):
    try:
        content = generators.generate_internal_brief(context_str)
        crud.create_gtm_asset(
            db,
            pack_id=pack_id,
            asset_type=AssetType.INTERNAL_BRIEF,
            content=content,
            status=AssetStatus.DRAFT,
        )
    except Exception as e:
        logger.error(f"Failed to generate Internal Brief: {e}")


def _generate_sales_snippet(db: Session, pack_id: uuid.UUID, context_str: str):
    try:
        content = generators.generate_sales_snippet(context_str)
        crud.create_gtm_asset(
            db,
            pack_id=pack_id,
            asset_type=AssetType.SALES_SNIPPET,
            content=content,
            status=AssetStatus.DRAFT,
        )
    except Exception as e:
        logger.error(f"Failed to generate Sales Snippet: {e}")


def _generate_support_snippet(db: Session, pack_id: uuid.UUID, context_str: str):
    try:
        content = generators.generate_support_snippet(context_str)
        crud.create_gtm_asset(
            db,
            pack_id=pack_id,
            asset_type=AssetType.SUPPORT_SNIPPET,
            content=content,
            status=AssetStatus.DRAFT,
        )
    except Exception as e:
        logger.error(f"Failed to generate Support Snippet: {e}")


def _generate_external_assets(
    db: Session, workspace_id: uuid.UUID, pack_id: uuid.UUID, context_str: str
):
    """Generates external assets containing the dual JSON variants (RL-lite)"""
    external_types = [
        AssetType.EMAIL,
        AssetType.LINKEDIN,
        AssetType.CHANGELOG,
    ]

    for ext_type in external_types:
        try:
            # RL-lite: Get workspace preferences for this asset type
            preference_hint = get_workspace_preferences(db, workspace_id, ext_type)
            logger.info(
                f"RL-lite Preference Hint for {ext_type.value}: {preference_hint}"
            )

            res_dict = generators.generate_external_asset_variants(
                context_str, ext_type, preference_hint
            )

            # The JsonOutputParser returns a dict, so we convert it back to string
            content = json.dumps(res_dict, indent=2)

            crud.create_gtm_asset(
                db,
                pack_id=pack_id,
                asset_type=ext_type,
                content=content,
                status=AssetStatus.DRAFT,
            )
        except Exception as e:
            logger.error(f"Failed to generate {ext_type.value}: {e}")
