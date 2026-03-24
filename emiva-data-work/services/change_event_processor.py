import re
import json
from database.db import Session, SourceEvent, ChangeEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_jira_key(text: str):
    """Return the first Jira key (e.g. EMIVA-123) found in text, or None."""
    if not text:
        return None
    match = re.search(r'[A-Z]+-\d+', text)
    return match.group(0) if match else None


def determine_change_type(issue_type: str = None, pr_title: str = None, summary: str = "") -> str:
    """Determine change_type from available metadata."""
    mapping = {
        "Bug":         "bug_fix",
        "Story":       "feature",
        "Task":        "chore",
        "Epic":        "feature",
        "Improvement": "feature",
    }
    if issue_type and issue_type in mapping:
        return mapping[issue_type]

    text = " ".join(filter(None, [pr_title, summary, issue_type])).lower()
    if "fix" in text or text.startswith("bug"):   return "bug_fix"
    if text.startswith("feat"):                   return "feature"
    if text.startswith("chore"):                  return "chore"
    if "critical" in text:                        return "bug_fix"
    if "docs" in text:                            return "docs"

    if pr_title:
        t = pr_title.lower()
        if t.startswith("fix"):      return "bug_fix"
        if t.startswith("feat"):     return "feature"
        if t.startswith("chore"):    return "chore"
        if t.startswith("docs"):     return "docs"
        if t.startswith("refactor"): return "chore"

    return "unknown"


# ---------------------------------------------------------------------------
# Per-source preprocessors
# ---------------------------------------------------------------------------

def preprocess_jira(payload: dict) -> dict:
    issue  = payload.get('issue', {})
    fields = issue.get('fields', {})
    key    = issue.get('key')
    summary     = fields.get('summary', '')
    description = fields.get('description', '')
    priority    = fields.get('priority', {}).get('name', 'medium').lower()
    status      = fields.get('status', {}).get('name', '')
    issue_type  = fields.get('issuetype', {}).get('name')
    component   = fields.get('project', {}).get('name', 'Unknown')
    actor       = payload.get('user', {}).get('displayName')

    return {
        "external_ticket_id": key,
        "title":       summary,
        "description": description,
        "ticket_url":  f"https://emiva.atlassian.net/browse/{key}" if key else "",
        "change_type": determine_change_type(issue_type=issue_type, summary=summary),
        "component":   component,
        "severity":    priority,
        "actors":      [actor] if actor else [],
        "raw_signals": {
            "issue_status":   status,
            "issue_resolved": status in ['Done', 'Resolved', 'Closed'],
        },
    }


def preprocess_github(payload: dict) -> dict:
    pr  = payload.get('pull_request', {})
    repo = payload.get('repository', {}).get('name', 'Unknown')

    if pr:
        # Pull-request event
        title  = pr.get('title', '')
        body   = pr.get('body', '') or ''
        actor  = pr.get('user', {}).get('login')
        labels = [l.get('name') for l in pr.get('labels', [])]
        merged = pr.get('merged') or payload.get('action') == 'closed'

        # Try to find a Jira key in title or body
        jira_key = extract_jira_key(f"{title} {body}")

        return {
            "external_ticket_id": jira_key,
            "title":       title,
            "description": body,
            "ticket_url":  pr.get('html_url', ''),
            "change_type": determine_change_type(pr_title=title),
            "component":   repo,
            "severity":    "medium",
            "actors":      [actor] if actor else [],
            "raw_signals": {
                "pr_number": pr.get('number'),
                "pr_merged": merged,
                "pr_labels": labels,
            },
        }

    # Push event
    commits = payload.get('commits', [])
    messages = [c.get('message', '') for c in commits]
    first_msg = messages[0] if messages else ''
    actor = payload.get('pusher', {}).get('name')

    return {
        "external_ticket_id": extract_jira_key(first_msg),
        "title":       f"Push to {repo}: {first_msg[:80]}",
        "description": "\n".join(messages),
        "ticket_url":  payload.get('compare', ''),
        "change_type": determine_change_type(pr_title=first_msg),
        "component":   repo,
        "severity":    "medium",
        "actors":      [actor] if actor else [],
        "raw_signals": {
            "push_ref":     payload.get('ref'),
            "commit_count": len(commits),
        },
    }


def preprocess_slack(payload: dict) -> dict:
    event  = payload.get('event', {})
    text   = event.get('text', '')
    actor  = event.get('user')
    thread = event.get('thread_ts')
    channel = event.get('channel')
    jira_key = extract_jira_key(text)

    return {
        "external_ticket_id": jira_key,
        "title":       f"Slack message: {text[:120]}",
        "description": text,
        "ticket_url":  "",
        "change_type": "unknown",
        "component":   "slack",
        "severity":    "low",
        "actors":      [actor] if actor else [],
        "raw_signals": {
            "channel":   channel,
            "thread_ts": thread,
            "has_thread": thread is not None,
        },
    }


PREPROCESSORS = {
    "jira":   preprocess_jira,
    "github": preprocess_github,
    "slack":  preprocess_slack,
}


# ---------------------------------------------------------------------------
# Main processor
# ---------------------------------------------------------------------------

def process_unprocessed_events():
    session = Session()
    try:
        unprocessed = (
            session.query(SourceEvent)
            .filter(SourceEvent.processed == False)
            .all()
        )

        if not unprocessed:
            print("No new events to process.")
            return

        print(f"Processing {len(unprocessed)} new event(s)...")

        for event in unprocessed:
            preprocessor = PREPROCESSORS.get(event.source_type)
            if not preprocessor:
                print(f"  [SKIP] Unknown source_type '{event.source_type}' for event {event.id}")
                event.processed = True
                continue

            try:
                data = preprocessor(event.raw_payload)
            except Exception as e:
                print(f"  [ERROR] Failed to preprocess event {event.id}: {e}")
                continue

            change = ChangeEvent(
                workspace_id=event.workspace_id,
                source_event_id=event.id,
                external_ticket_id=data.get("external_ticket_id"),
                title=data.get("title", ""),
                description=data.get("description", ""),
                ticket_url=data.get("ticket_url", ""),
                change_type=data.get("change_type", "unknown"),
                component=data.get("component", "Unknown"),
                severity=data.get("severity", "medium"),
                linked_issues=[data["external_ticket_id"]] if data.get("external_ticket_id") else [],
                linked_prs=[],
                linked_threads=[],
                actors=list(filter(None, data.get("actors", []))),
                raw_signals=data.get("raw_signals", {}),
            )
            session.add(change)
            event.processed = True
            print(f"  [OK] {event.source_type.upper()} event {event.id} → change_event created")

        session.commit()
        print("Processing complete.")

    except Exception as e:
        session.rollback()
        print(f"Error during processing: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    process_unprocessed_events()
