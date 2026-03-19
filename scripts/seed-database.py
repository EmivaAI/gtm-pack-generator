import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import sys
import os

# Ensure the app module can be found in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.core.settings import settings
from app.db.schema import (
    Base, Workspace, BrandProfile, AudienceSegment, SourceEvent, ChangeEvent,
    LaunchCandidate, GtmPack, GtmAsset, ApprovalEvent,
    SourceType, LaunchTier, LaunchStatus, PackStatus, AssetType, AssetStatus, ApprovalAction
)

# 1. Setup Database Connection & Faker
engine = create_engine(settings.database_url)
fake = Faker()

# 2. Domain-Specific Mock Data (The 90% Realism Engine)
# Instead of random latin, we use highly realistic B2B SaaS data.
SAAS_COMPANIES = ["Acme Analytics", "CloudSync Hub", "DevFlow Pipelines"]

PRODUCT_SUMMARIES = [
    "A real-time data visualization platform for enterprise data teams.",
    "An automated file synchronization tool for distributed remote teams.",
    "A CI/CD pipeline visualizer that helps engineering managers track deployment health."
]

PERSONAS = [
    {"name": "VP of Engineering", "pains": ["Deployments are too slow", "Lack of visibility"], "outcomes": ["Faster ship velocity", "Fewer rollbacks"]},
    {"name": "Head of Sales", "pains": ["Competitors are winning on features", "Reps don't know what to pitch"], "outcomes": ["Higher win rates", "Confident reps"]},
    {"name": "Product Manager", "pains": ["Roadmap is disconnected from GTM", "Too many Slack messages"], "outcomes": ["Automated alignment", "Clear launch tiers"]}
]

REALISTIC_FEATURES = [
    ("Stripe Billing Integration", "Added webhooks and UI for connecting Stripe accounts to automate monthly invoicing.", LaunchTier.TIER_1),
    ("Dark Mode", "Implemented system-wide dark theme using CSS variables.", LaunchTier.TIER_3),
    ("SOC2 Compliance Audit Logs", "Created immutable ledger for all admin actions to satisfy SOC2 requirements.", LaunchTier.TIER_2),
    ("Kanban Board View", "Added drag-and-drop Kanban view for the tasks module.", LaunchTier.TIER_2),
    ("Role-Based Access Control (RBAC)", "Granular permissions for enterprise tier users.", LaunchTier.TIER_1),
    ("Fix UI typo in settings", "Corrected spelling of 'Preferences' in the nav bar.", LaunchTier.TIER_3),
    ("Slack Notification App", "Native integration to push alerts directly to Slack channels.", LaunchTier.TIER_1)
]

def generate_realistic_content(asset_type, feature_name):
    if asset_type == AssetType.EMAIL:
        return f"Subject: Announcing {feature_name}!\n\nHi team, we are thrilled to roll out our latest update. You can now use {feature_name} to streamline your workflow."
    elif asset_type == AssetType.LINKEDIN:
        return f"🚀 BIG NEWS! Today we are launching {feature_name}. Say goodbye to manual work and hello to efficiency. Check out our latest blog post to learn more! #SaaS #ProductLaunch"
    elif asset_type == AssetType.INTERNAL_BRIEF:
        return f"INTERNAL ONLY: {feature_name} is launching tomorrow. Sales: focus on time-savings. Support: check Confluence for the new FAQ."
    else:
        return f"Sales Snippet: 'Unlike our competitors, we now offer full {feature_name}.'"

def seed_database(num_events_per_workspace=15):
    print("Recreating database schema...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        print("Seeding Workspaces & Core Config...")
        workspaces = []
        for i, company_name in enumerate(SAAS_COMPANIES):
            # Create Workspace
            workspace = Workspace(name=company_name)
            session.add(workspace)
            session.flush() # Flush to get the ID
            workspaces.append(workspace)

            # Create Brand Profile
            brand_profile = BrandProfile(
                workspace_id=workspace.id,
                product_summary=PRODUCT_SUMMARIES[i],
                tone_rules=["Professional", "Punchy", "No jargon", "Active voice"],
                allowed_claims=["10x faster than legacy tools", "Enterprise-grade security"],
                disallowed_claims=["Guaranteed ROI", "Cheapest on the market"]
            )
            session.add(brand_profile)

            # Create Audience Segments
            for p in PERSONAS:
                segment = AudienceSegment(
                    workspace_id=workspace.id,
                    persona_name=p["name"],
                    pain_points=p["pains"],
                    desired_outcomes=p["outcomes"]
                )
                session.add(segment)

        session.commit()
        print("Seeding Engineering & GTM Pipelines...")

        # For each workspace, generate a pipeline of tickets and launches
        for workspace in workspaces:
            audiences = session.query(AudienceSegment).filter_by(workspace_id=workspace.id).all()

            for _ in range(num_events_per_workspace):
                # Pick a random feature to simulate
                feature_title, feature_desc, expected_tier = random.choice(REALISTIC_FEATURES)
                created_date = fake.date_time_between(start_date="-60d", end_date="now")

                # 1. Source Event (The Raw Webhook)
                source_event = SourceEvent(
                    workspace_id=workspace.id,
                    source_type=SourceType.JIRA,
                    raw_payload={"issue": {"key": f"ENG-{random.randint(100, 999)}", "fields": {"summary": feature_title}}},
                    processed=True,
                    created_at=created_date
                )
                session.add(source_event)
                session.flush()

                # 2. Change Event (Normalized)
                change_event = ChangeEvent(
                    workspace_id=workspace.id,
                    source_event_id=source_event.id,
                    external_ticket_id=source_event.raw_payload["issue"]["key"],
                    title=feature_title,
                    description=feature_desc,
                    ticket_url=f"https://jira.com/{source_event.raw_payload['issue']['key']}",
                    created_at=created_date
                )
                session.add(change_event)
                session.flush()

                # 3. Launch Candidate
                # Not all features get launched (some get rejected/ignored)
                status = random.choices([LaunchStatus.APPROVED, LaunchStatus.PENDING_REVIEW, LaunchStatus.REJECTED], weights=[70, 20, 10])[0]
                
                candidate = LaunchCandidate(
                    workspace_id=workspace.id,
                    change_event_id=change_event.id,
                    tier=expected_tier,
                    score=random.randint(40, 95),
                    reasons=[f"Highly requested feature", f"Matches tier {expected_tier.value} criteria"],
                    is_external_safe=True if expected_tier != LaunchTier.TIER_3 else False,
                    status=status,
                    created_at=created_date + timedelta(hours=2)
                )
                session.add(candidate)
                session.flush()

                # 4. GtmPack & Assets (Only if approved)
                if status == LaunchStatus.APPROVED:
                    pack = GtmPack(
                        workspace_id=workspace.id,
                        launch_candidate_id=candidate.id,
                        status=random.choice(list(PackStatus)),
                        created_at=created_date + timedelta(hours=4)
                    )
                    session.add(pack)
                    session.flush()

                    # Generate assets for this pack
                    asset_types_to_create = [AssetType.INTERNAL_BRIEF, AssetType.LINKEDIN, AssetType.EMAIL]
                    for a_type in asset_types_to_create:
                        draft_text = generate_realistic_content(a_type, feature_title)
                        is_approved = random.choice([True, False])
                        
                        asset = GtmAsset(
                            gtm_pack_id=pack.id,
                            asset_type=a_type,
                            audience_id=random.choice(audiences).id if a_type == AssetType.EMAIL else None,
                            content_draft=draft_text,
                            content_final=draft_text + "\n(Final Polish)" if is_approved else None,
                            status=AssetStatus.APPROVED if is_approved else AssetStatus.DRAFT,
                            updated_at=created_date + timedelta(days=1)
                        )
                        session.add(asset)
                        session.flush()

                        # 5. Approval Events (Audit Log)
                        if is_approved:
                            approval = ApprovalEvent(
                                gtm_asset_id=asset.id,
                                user_id=fake.uuid4(), # Simulating an external Auth0/Clerk user ID
                                action=random.choice([ApprovalAction.APPROVED_AS_IS, ApprovalAction.APPROVED_WITH_EDITS]),
                                comments=fake.sentence() if random.random() > 0.5 else None,
                                created_at=created_date + timedelta(days=1, hours=2)
                            )
                            session.add(approval)

        session.commit()
        print(f"✅ Seeding complete! Generated rich test data for {len(SAAS_COMPANIES)} workspaces.")

if __name__ == "__main__":
    seed_database(num_events_per_workspace=20)