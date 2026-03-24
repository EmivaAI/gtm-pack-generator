import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys
import os

# Ensure the app module can be found in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from gtm_core.core.settings import settings
from gtm_core.db.schema import (
    Base,
    Workspace,
    BrandProfile,
    AudienceSegment,
    SourceEvent,
    ChangeEvent,
    LaunchCandidate,
    GtmPack,
    GtmAsset,
    ApprovalEvent,
    SourceType,
    LaunchTier,
    LaunchStatus,
    PackStatus,
    AssetType,
    AssetStatus,
    ApprovalAction,
)

engine = create_engine(settings.database_url)


def load_narrative_json():
    json_path = os.path.join(os.path.dirname(__file__), "seed-narrative.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_narrative():
    print("Recreating database schema...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    data = load_narrative_json()

    with Session(engine) as session:
        workspace_name = data["workspace"]["name"]
        print(f"Seeding Narrative for '{workspace_name}'...")

        # 1. Workspace
        workspace = Workspace(name=workspace_name)
        session.add(workspace)
        session.flush()

        # 2. Brand Profile
        bp_data = data["brand_profile"]
        brand_profile = BrandProfile(
            workspace_id=workspace.id,
            product_summary=bp_data["product_summary"],
            tone_rules=bp_data["tone_rules"],
            allowed_claims=bp_data["allowed_claims"],
            disallowed_claims=bp_data["disallowed_claims"],
        )
        session.add(brand_profile)

        # 3. Audience Segments
        audiences = {}
        for seg_data in data["audience_segments"]:
            seg = AudienceSegment(
                workspace_id=workspace.id,
                persona_name=seg_data["persona_name"],
                pain_points=seg_data["pain_points"],
                desired_outcomes=seg_data["desired_outcomes"],
            )
            session.add(seg)
            audiences[seg_data["persona_name"]] = seg

        session.flush()

        # --- NARRATIVE: Historical completed launches ---
        for entry in data.get("history_launches", []):
            launch_date = datetime.utcnow() - timedelta(days=entry["days_ago"])

            # Source Event
            source_event = SourceEvent(
                workspace_id=workspace.id,
                source_type=SourceType.JIRA,
                raw_payload={
                    "issue": {
                        "key": entry["jira_key"],
                        "fields": {
                            "summary": entry["feature_title"],
                            "status": {"name": "Done"},
                        },
                    }
                },
                processed=True,
                created_at=launch_date - timedelta(days=5),
            )
            session.add(source_event)
            session.flush()

            # Change Event
            change_event = ChangeEvent(
                workspace_id=workspace.id,
                source_event_id=source_event.id,
                external_ticket_id=entry["jira_key"],
                title=entry["feature_title"],
                description=entry["description"],
                ticket_url=f"https://acme.atlassian.net/browse/{entry['jira_key']}",
                created_at=launch_date - timedelta(days=5),
            )
            session.add(change_event)
            session.flush()

            # Launch Candidate
            candidate = LaunchCandidate(
                workspace_id=workspace.id,
                change_event_id=change_event.id,
                tier=LaunchTier(entry["tier"]),
                score=entry["score"],
                reasons=entry["reasons"],
                is_external_safe=entry["is_external_safe"],
                status=LaunchStatus(entry["status"]),
                created_at=launch_date - timedelta(days=4),
            )
            session.add(candidate)
            session.flush()

            # GTM Pack
            pack = GtmPack(
                workspace_id=workspace.id,
                launch_candidate_id=candidate.id,
                status=PackStatus.FINALIZED,
                created_at=launch_date - timedelta(days=3),
            )
            session.add(pack)
            session.flush()

            # Assets
            asset_map = {}
            for asset_type_str, asset_content in entry["assets"].items():
                is_json = isinstance(asset_content, dict)
                asset = GtmAsset(
                    gtm_pack_id=pack.id,
                    asset_type=AssetType(asset_type_str),
                    # Associate emails to VP audience logic for the dummy data
                    audience_id=list(audiences.values())[0].id
                    if asset_type_str == "EMAIL"
                    else None,
                    content_draft=json.dumps(asset_content, indent=2)
                    if is_json
                    else asset_content,
                    status=AssetStatus.APPROVED,
                    updated_at=launch_date - timedelta(days=2),
                )
                session.add(asset)
                asset_map[asset_type_str] = asset

            session.flush()

            # Approval Events log
            if "approval" in entry and "EMAIL" in asset_map:
                app_data = entry["approval"]
                approval_event = ApprovalEvent(
                    gtm_asset_id=asset_map["EMAIL"].id,
                    user_id=uuid.uuid4(),
                    action=ApprovalAction(app_data["action"]),
                    comments=app_data.get("comments"),
                    edit_diff=app_data.get("edit_diff"),
                    created_at=launch_date - timedelta(days=1),
                )
                session.add(approval_event)

        # --- NARRATIVE: Pending Launches ---
        pending_ids = []
        for entry in data.get("pending_launches", []):
            base_date = datetime.utcnow() - timedelta(hours=entry.get("hours_ago", 1))
            pending_candidate_id = uuid.uuid4()
            pending_ids.append((entry["feature_title"], pending_candidate_id))

            source_event = SourceEvent(
                workspace_id=workspace.id,
                source_type=SourceType.JIRA,
                raw_payload={
                    "issue": {
                        "key": entry["jira_key"],
                        "fields": {"summary": entry["feature_title"]},
                    }
                },
                processed=True,
                created_at=base_date - timedelta(hours=3),
            )
            session.add(source_event)
            session.flush()

            change_event = ChangeEvent(
                workspace_id=workspace.id,
                source_event_id=source_event.id,
                external_ticket_id=entry["jira_key"],
                title=entry["feature_title"],
                description=entry["description"],
                ticket_url=f"https://acme.atlassian.net/browse/{entry['jira_key']}",
                created_at=base_date - timedelta(hours=2),
            )
            session.add(change_event)
            session.flush()

            candidate = LaunchCandidate(
                id=pending_candidate_id,
                workspace_id=workspace.id,
                change_event_id=change_event.id,
                tier=LaunchTier(entry["tier"]),
                score=entry["score"],
                reasons=entry["reasons"],
                is_external_safe=entry["is_external_safe"],
                status=LaunchStatus(entry["status"]),
                created_at=base_date - timedelta(hours=1),
            )
            session.add(candidate)
            session.flush()

        session.commit()

        print("\n[SUCCESS] Narrative Seeding Complete!")
        if pending_ids:
            print("-" * 60)
            print("Ready to Generate:")
            for title, cid in pending_ids:
                print(f"Workspace     : {workspace_name}")
                print(f"Feature       : {title}")
                print(f"Candidate ID  : {cid}")
                print(f"Test CURL     : curl -X POST http://localhost:8000/{cid}")
                print("-" * 60)


if __name__ == "__main__":
    seed_narrative()
