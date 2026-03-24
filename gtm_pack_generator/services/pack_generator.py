import uuid
from sqlalchemy.orm import Session

from emiva_core.core.logger import setup_logger
from emiva_core.db.schema import GtmPack
from gtm_pack_generator.agent.gtm_agent import GtmGenerationAgent

logger = setup_logger(__name__)


def generate_gtm_pack(db: Session, candidate_id: uuid.UUID) -> GtmPack:
    """
    Entry point for GTM generation.
    Hands off orchestration to the GtmGenerationAgent.
    """
    agent = GtmGenerationAgent(db, candidate_id)
    return agent.execute()
