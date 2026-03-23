import uuid
import json
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.schema import GtmAsset, AssetStatus, AssetType
from app.core.logger import setup_logger

logger = setup_logger(__name__)

def get_workspace_preferences(db: Session, workspace_id: uuid.UUID, asset_type: AssetType) -> str:
    """
    Analyzes past approvals for a specific workspace and asset type to determine
    if the user prefers 'Short/Direct' (Variant A) or 'Detailed/Narrative' (Variant B).
    
    Returns a preference hint string for the LLM.
    """
    # Query approved assets for this workspace and asset type
    # Note: We need to join with GtmPack to filter by workspace_id
    from app.db.schema import GtmPack
    
    stmt = (
        select(GtmAsset)
        .join(GtmPack)
        .where(GtmPack.workspace_id == workspace_id)
        .where(GtmAsset.asset_type == asset_type)
        .where(GtmAsset.status == AssetStatus.APPROVED)
        .where(GtmAsset.content_final.is_not(None))
    )
    
    approved_assets = db.scalars(stmt).all()
    
    if not approved_assets:
        return "No specific preference found. Provide two balanced variants."

    a_picks = 0
    b_picks = 0
    
    for asset in approved_assets:
        try:
            draft = json.loads(asset.content_draft)
            v_a = draft.get("variant_a", "").strip()
            v_b = draft.get("variant_b", "").strip()
            final = asset.content_final.strip()
            
            # Simple heuristic: which variant is closer to the final approved version?
            # In a real system, we'd use edit distance, but for V1 simple inclusion or equality works.
            if v_a and v_a in final:
                a_picks += 1
            elif v_b and v_b in final:
                b_picks += 1
        except (json.JSONDecodeError, AttributeError):
            continue

    if a_picks > b_picks:
        return "The user strongly prefers 'Short and Direct' content (Variant A). Lean towards punchy, concise messaging."
    elif b_picks > a_picks:
        return "The user strongly prefers 'Detailed and Narrative' content (Variant B). Lean towards story-driven, explanatory messaging."
    
    return "The user has shown mixed preferences. Continue providing two distinct, balanced variants."
