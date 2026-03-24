import json
import uuid
import os
import time
import httpx
from emiva_core.core.logger import setup_logger

logger = setup_logger(__name__)

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"

def load_narrative_json():
    json_path = os.path.join(os.path.dirname(__file__), "seed-narrative.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def wait_for_server(url, timeout=30):
    """Wait for the server to be up before seeding."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = httpx.get(url.replace("/api/v1", "/health"))
            if response.status_code == 200:
                return True
        except httpx.RequestError:
            pass
        print(f"Waiting for server at {url}...")
        time.sleep(2)
    return False

def seed_narrative():
    if not wait_for_server(BASE_URL):
        print("Error: Server not reachable. Please run: uv run uvicorn gtm_pack_generator.main:app --reload")
        return

    data = load_narrative_json()

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        print("Recreating database schema via API...")
        client.post("/reset-db")

        workspace_name = data["workspace"]["name"]
        print(f"Seeding Narrative for '{workspace_name}'...")

        # 1. Workspace
        ws_res = client.post("/workspaces", json={"name": workspace_name}).json()
        workspace_id = ws_res["id"]

        # 2. Brand Profile
        bp_data = data["brand_profile"]
        client.post("/brand-profiles", json={
            "workspace_id": workspace_id,
            "name": workspace_name, # Default name
            "product_summary": bp_data["product_summary"],
            "tone_rules": bp_data["tone_rules"],
            "allowed_claims": bp_data["allowed_claims"],
            "disallowed_claims": bp_data["disallowed_claims"],
        })

        # 3. Audience Segments
        audiences = {}
        for seg_data in data["audience_segments"]:
            res = client.post("/audience-segments", json={
                "workspace_id": workspace_id,
                "persona_name": seg_data["persona_name"],
                "pain_points": seg_data["pain_points"],
                "desired_outcomes": seg_data["desired_outcomes"],
            }).json()
            audiences[seg_data["persona_name"]] = res["id"]

        # --- NARRATIVE: Historical completed launches ---
        for entry in data.get("history_launches", []):
            # Change Event
            ce_res = client.post("/change-events", json={
                "workspace_id": workspace_id,
                "title": entry["feature_title"],
                "description": entry["description"],
                "external_ticket_id": entry["jira_key"],
                "ticket_url": f"https://acme.atlassian.net/browse/{entry['jira_key']}",
            }).json()
            change_event_id = ce_res["id"]

            # Launch Candidate
            lc_res = client.post("/launch-candidates", json={
                "workspace_id": workspace_id,
                "change_event_id": change_event_id,
                "tier": entry["tier"],
                "score": entry["score"],
                "reasons": entry["reasons"],
                "is_external_safe": entry["is_external_safe"],
                "status": entry["status"],
            }).json()
            candidate_id = lc_res["id"]

            # GTM Pack
            pk_res = client.post("/gtm-packs", json={
                "workspace_id": workspace_id,
                "launch_candidate_id": candidate_id,
                "status": "FINALIZED",
            }).json()
            pack_id = pk_res["id"]

            # Assets
            asset_map = {}
            for asset_type_str, asset_content in entry["assets"].items():
                is_json = isinstance(asset_content, dict)
                # Associate emails to VP audience logic for the dummy data
                aud_id = audiences.get("VP of Marketing") if asset_type_str == "EMAIL" else None
                
                ast_res = client.post("/gtm-assets", json={
                    "gtm_pack_id": pack_id,
                    "asset_type": asset_type_str,
                    "audience_id": aud_id,
                    "content_draft": json.dumps(asset_content, indent=2) if is_json else asset_content,
                    "status": "APPROVED",
                }).json()
                asset_map[asset_type_str] = ast_res["id"]

            # Approval Events log
            if "approval" in entry and "EMAIL" in asset_map:
                app_data = entry["approval"]
                client.post("/approval-events", json={
                    "gtm_asset_id": asset_map["EMAIL"],
                    "user_id": str(uuid.uuid4()),
                    "action": app_data["action"],
                    "comments": app_data.get("comments"),
                    "edit_diff": app_data.get("edit_diff"),
                })

        # --- NARRATIVE: Pending Launches ---
        pending_ids = []
        for entry in data.get("pending_launches", []):
            ce_res = client.post("/change-events", json={
                "workspace_id": workspace_id,
                "title": entry["feature_title"],
                "description": entry["description"],
                "external_ticket_id": entry["jira_key"],
                "ticket_url": f"https://acme.atlassian.net/browse/{entry['jira_key']}",
            }).json()
            
            lc_res = client.post("/launch-candidates", json={
                "workspace_id": workspace_id,
                "change_event_id": ce_res["id"],
                "tier": entry["tier"],
                "score": entry["score"],
                "reasons": entry["reasons"],
                "is_external_safe": entry["is_external_safe"],
                "status": entry["status"],
            }).json()
            pending_ids.append((entry["feature_title"], lc_res["id"]))

        print("\n[SUCCESS] Narrative Seeding Complete!")
        if pending_ids:
            print("-" * 60)
            print("Ready to Generate:")
            for title, cid in pending_ids:
                print(f"Workspace     : {workspace_name}")
                print(f"Feature       : {title}")
                print(f"Candidate ID  : {cid}")
                print(f"Test CURL     : curl -X POST http://localhost:8080/api/generate/{cid}")
                print("-" * 60)

if __name__ == "__main__":
    seed_narrative()
