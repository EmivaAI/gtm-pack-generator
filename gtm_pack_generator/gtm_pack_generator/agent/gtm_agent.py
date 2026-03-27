import uuid
import json
from sqlalchemy.orm import Session
from emiva_core.core.logger import setup_logger
from emiva_core.db.schema import (
    GtmPack,
    AssetType,
    AssetStatus,
)
from emiva_core.db import crud
from gtm_pack_generator.agent import context, generators
from gtm_pack_generator.services.learning import get_workspace_preferences

logger = setup_logger(__name__)

class GtmGenerationAgent:
    """
    Agentic orchestrator for GTM Pack generation.
    Handles context retrieval, asset sequencing, and persistence.
    """
    
    def __init__(self, db: Session, candidate_id: uuid.UUID):
        self.db = db
        self.candidate_id = candidate_id
        self.candidate = None
        self.workspace_id = None
        self.context_str = None
        self.pack = None

    def execute(self) -> GtmPack:
        """Main execution loop for the agent."""
        logger.info(f"Agent starting execution for candidate {self.candidate_id}")
        
        # 1. Prepare Environment & Context
        self._prepare_context()
        
        # 2. Create the Pack record
        self.pack = crud.create_gtm_pack(self.db, self.workspace_id, self.candidate.id)
        
        # 3. Generate internal assets
        self._generate_internal_assets()
        
        # 4. Generate external assets (RL-lite variants)
        self._generate_external_assets()
        
        self.db.commit()
        logger.info(f"Agent successfully completed GTM Pack {self.pack.id}")
        return self.pack

    def _prepare_context(self):
        """Fetches all necessary data from the DB and builds the prompt context."""
        self.candidate = crud.get_candidate(self.db, self.candidate_id)
        if not self.candidate:
            raise ValueError(f"LaunchCandidate {self.candidate_id} not found")

        self.workspace_id = self.candidate.workspace_id
        change_event = self.candidate.change_event
        
        brand_profile = crud.get_brand_profile(self.db, self.workspace_id)
        audiences = crud.get_audience_segments(self.db, self.workspace_id)

        # Fetch History
        approved_assets = crud.get_recent_approved_assets(self.db, self.workspace_id, limit=5)
        approved_pillars = [
            asset.content_final or asset.content_draft
            for asset in approved_assets
            if asset.content_final or asset.content_draft
        ]

        approved_candidates = crud.get_recent_approved_candidates(self.db, self.workspace_id, limit=3)
        launch_history = [
            f"{c.change_event.title} (Tier {c.tier.value})" for c in approved_candidates
        ]

        # Assembly
        self.context_str = context.build_candidate_context(
            self.candidate,
            change_event,
            brand_profile,
            audiences,
            approved_pillars,
            launch_history,
        )

    def _generate_internal_assets(self):
        """Orchestrates internal-facing assets."""
        internal_tasks = [
            (AssetType.INTERNAL_BRIEF, generators.generate_internal_brief),
            (AssetType.SALES_SNIPPET, generators.generate_sales_snippet),
            (AssetType.SUPPORT_SNIPPET, generators.generate_support_snippet),
        ]
        
        for asset_type, generator_func in internal_tasks:
            try:
                content = generator_func(self.context_str)
                crud.create_gtm_asset(
                    self.db,
                    pack_id=self.pack.id,
                    asset_type=asset_type,
                    content=content,
                    status=AssetStatus.DRAFT,
                )
            except Exception as e:
                logger.error(f"Agent failed to generate {asset_type.value}: {e}")

    def _generate_external_assets(self):
        """Orchestrates external-facing assets with RL-lite variants."""
        external_types = [
            AssetType.EMAIL,
            AssetType.LINKEDIN,
            AssetType.CHANGELOG,
        ]

        for ext_type in external_types:
            try:
                # RL-lite preference hint
                preference_hint = get_workspace_preferences(self.db, self.workspace_id, ext_type)
                
                res_dict = generators.generate_external_asset_variants(
                    self.context_str, ext_type, preference_hint
                )

                crud.create_gtm_asset(
                    self.db,
                    pack_id=self.pack.id,
                    asset_type=ext_type,
                    content=json.dumps(res_dict, indent=2),
                    status=AssetStatus.DRAFT,
                )
            except Exception as e:
                logger.error(f"Agent failed to generate {ext_type.value}: {e}")
