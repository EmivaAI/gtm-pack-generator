"""
Integration tests for generate_gtm_pack (app.services.pack_generator) with call caching.
"""

import uuid
import vcr
import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from app.db.schema import (
    ChangeEvent,
    LaunchCandidate,
    BrandProfile,
    AudienceSegment,
    GtmPack,
    GtmAsset,
    LaunchTier,
    PackStatus,
    AssetType,
    AssetStatus,
)
from app.services.pack_generator import generate_gtm_pack

# Configure VCR to record LLM calls to a local cassette.
# This prevents expensive repeated API calls.
my_vcr = vcr.VCR(
    serializer="yaml",
    cassette_library_dir="tests/integration/cassettes",
    record_mode="once",
    match_on=["method", "scheme", "host", "port", "path", "query"],
    filter_headers=["authorization", "x-api-key"],
)

RESULTS_FILE = "tests/integration/test_gtm_pack_generation_results.md"


# ---------------------------------------------------------------------------
# Narrative fixtures
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid.uuid4()
CANDIDATE_ID = uuid.uuid4()


@pytest.fixture()
def change_event():
    e = MagicMock(spec=ChangeEvent)
    e.id = uuid.uuid4()
    e.title = "Smart Alerts: AI-powered anomaly detection"
    e.description = (
        "Automatically surfaces statistically significant metric drops "
        "and spikes to analysts, cutting manual investigation time by ~60%."
    )
    return e


@pytest.fixture()
def candidate(change_event):
    c = MagicMock(spec=LaunchCandidate)
    c.id = CANDIDATE_ID
    c.workspace_id = WORKSPACE_ID
    c.tier = LaunchTier.TIER_1
    c.reasons = [
        "High customer impact — affects all dashboard users",
        "Addresses #1 support ticket theme: missed anomalies",
    ]
    c.safety_warnings = None
    c.change_event = change_event
    return c


@pytest.fixture()
def brand_profile():
    b = MagicMock(spec=BrandProfile)
    b.workspace_id = WORKSPACE_ID
    b.product_summary = (
        "Acme Analytics is a B2B SaaS platform helping data teams "
        "monitor business KPIs in real time."
    )
    b.tone_rules = {"voice": "confident but approachable", "avoid": ["hype", "jargon"]}
    b.allowed_claims = [
        "60% reduction in investigation time",
        "SOC 2 Type II certified",
    ]
    b.disallowed_claims = ["best in class", "industry leading", "guaranteed ROI"]
    return b


@pytest.fixture()
def audiences():
    analyst = MagicMock(spec=AudienceSegment)
    analyst.persona_name = "Data Analyst"
    analyst.pain_points = [
        "Too many false-positive alerts",
        "Alert fatigue from manual monitoring",
    ]
    analyst.desired_outcomes = [
        "Catch real anomalies faster",
        "Less time on dashboards",
    ]
    analyst.objections = ["Will it trigger too often?"]

    manager = MagicMock(spec=AudienceSegment)
    manager.persona_name = "Engineering Manager"
    manager.pain_points = ["Team spends hours on manual metric review"]
    manager.desired_outcomes = ["Reduce on-call burden", "Confidence in data quality"]
    manager.objections = ["Integration complexity", "Cost overhead"]

    return [analyst, manager]


# ---------------------------------------------------------------------------
# DB mock
# ---------------------------------------------------------------------------


def make_mock_db(
    candidate, brand_profile, audiences, approved_assets=None, approved_candidates=None
):
    """
    Wire a mock Session:
      - scalar() returns LaunchCandidate then BrandProfile
      - scalars().all() returns:
          1. audiences
          2. approved_assets (history)
          3. approved_candidates (history)
    """
    db = MagicMock(spec=Session)
    db.scalar.side_effect = [candidate, brand_profile]

    # scalars().all() returns a list of items for each call in sequence
    db.scalars.return_value.all.side_effect = [
        audiences,
        approved_assets or [],
        approved_candidates or [],
        [], # for EMAIL preference hint
        [], # for LINKEDIN preference hint
        [], # for CHANGELOG preference hint
    ]

    added: list = []

    def on_add(obj):
        added.append(obj)

    def on_flush():
        # Give the GtmPack its primary key
        for obj in added:
            if isinstance(obj, GtmPack) and obj.id is None:
                obj.id = uuid.uuid4()

    db.add.side_effect = on_add
    db.flush.side_effect = on_flush
    db._added = added  # expose for assertions
    return db


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateGtmPack:
    @pytest.fixture(autouse=True)
    def setup(self, candidate, brand_profile, audiences):
        self.db = make_mock_db(candidate, brand_profile, audiences)
        with my_vcr.use_cassette("gtm_pack_generation.yaml"):
            self.pack = generate_gtm_pack(self.db, CANDIDATE_ID)

    def test_returns_gtm_pack_in_draft(self):
        assert self.pack is not None
        assert self.pack.status == PackStatus.DRAFT

    def test_db_flush_called_once(self):
        """flush() must be called after adding the pack to yield pack.id."""
        self.db.flush.assert_called_once()

    def test_db_commit_called_once(self):
        self.db.commit.assert_called_once()

    def test_seven_objects_added_to_db(self):
        """1 GtmPack + 6 GtmAssets (brief, snippet, support, email, linkedin, changelog)."""
        assert self.db.add.call_count == 7

    def test_all_six_asset_types_generated(self):
        assets = [obj for obj in self.db._added if isinstance(obj, GtmAsset)]
        asset_types = {a.asset_type for a in assets}
        assert asset_types == {
            AssetType.INTERNAL_BRIEF,
            AssetType.SALES_SNIPPET,
            AssetType.SUPPORT_SNIPPET,
            AssetType.EMAIL,
            AssetType.LINKEDIN,
            AssetType.CHANGELOG,
        }

    def test_all_assets_have_non_empty_content(self):
        """The real LLM must return non-empty content for every asset."""
        assets = [obj for obj in self.db._added if isinstance(obj, GtmAsset)]
        for asset in assets:
            assert asset.content_draft, f"{asset.asset_type} has empty content_draft"

    def test_external_assets_are_valid_json_without_fences(self):
        import json

        external_types = {AssetType.EMAIL, AssetType.LINKEDIN, AssetType.CHANGELOG}
        assets = [
            obj
            for obj in self.db._added
            if isinstance(obj, GtmAsset) and obj.asset_type in external_types
        ]

        for asset in assets:
            content = asset.content_draft
            assert not content.startswith("```"), (
                f"{asset.asset_type.value} starts with markdown fence"
            )
            assert not content.endswith("```"), (
                f"{asset.asset_type.value} ends with markdown fence"
            )

            try:
                parsed = json.loads(content)
                assert "variant_a" in parsed
                assert "variant_b" in parsed
            except json.JSONDecodeError:
                pytest.fail(
                    f"{asset.asset_type.value} content is not valid JSON:\\n{content}"
                )

    def test_all_assets_are_in_draft_status(self):
        assets = [obj for obj in self.db._added if isinstance(obj, GtmAsset)]
        for asset in assets:
            assert asset.status == AssetStatus.DRAFT

    def test_write_results_to_markdown(self):
        """Write all LLM-generated asset content to a markdown file for review."""
        assets = [obj for obj in self.db._added if isinstance(obj, GtmAsset)]

        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            f.write("# GTM Pack Generation Results\n\n")
            f.write(f"**Candidate ID:** `{CANDIDATE_ID}`\n")
            f.write("**Status:** `SUCCESS`\n\n")

            for asset in assets:
                f.write(f"## {asset.asset_type.value}\n")
                f.write(f"```markdown\n{asset.content_draft}\n```\n\n")

        print(f"\nResults written to {RESULTS_FILE}")


class TestGenerateGtmPackCandidateNotFound:
    def test_raises_when_candidate_missing(self):
        db = MagicMock(spec=Session)
        db.scalar.return_value = None

        with pytest.raises(ValueError, match=str(CANDIDATE_ID)):
            generate_gtm_pack(db, CANDIDATE_ID)
