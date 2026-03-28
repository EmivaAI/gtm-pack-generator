"""
services/change_event_processor.py
------------------------------------
Converts unprocessed SourceEvent rows into ChangeEvent records.

Processing pipeline
~~~~~~~~~~~~~~~~~~~
1. Query all SourceEvent rows where processed=False.
2. For each event, dispatch to the appropriate per-source preprocessor:
       jira   → preprocess_jira()
       github → preprocess_github()
       slack  → preprocess_slack()
3. Build a ChangeEvent from the preprocessed data and mark the source as processed.
4. If preprocessing fails, the event is still marked processed and a
   ChangeEvent with a processing_error signal is stored — this prevents
   a single bad event from blocking the entire queue.

Helper utilities
~~~~~~~~~~~~~~~~
_safe()              — Null-safe nested dict accessor
extract_jira_key()   — Regex-based Jira key extractor (e.g. EMIVA-123)
determine_change_type() — Maps issue types / commit prefixes to change_type values
"""

import re
import json
from database.db import Session, SourceEvent, ChangeEvent
from emiva_core.core.logger import setup_logger

logger = setup_logger("ingestion.services.processor")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(obj, *keys, default=None):
    """Null-safe nested dict accessor. Returns default if any key is missing or value is None."""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key)
        if obj is None:
            return default
    return obj


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
    """Extract and normalise fields from a Jira webhook payload."""
    issue  = payload.get('issue') or {}
    fields = issue.get('fields') or {}
    key    = issue.get('key')
    summary     = fields.get('summary') or ''
    description = fields.get('description') or ''
    priority    = _safe(fields, 'priority', 'name', default='medium').lower()
    status      = _safe(fields, 'status', 'name', default='')
    issue_type  = _safe(fields, 'issuetype', 'name')
    component   = _safe(fields, 'project', 'name', default='Unknown')
    actor       = _safe(payload, 'user', 'displayName')

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
    """Extract and normalise fields from a GitHub webhook payload (PR or push)."""
    pr   = payload.get('pull_request') or {}
    repo = _safe(payload, 'repository', 'name', default='Unknown')

    if pr:
        # Pull-request event
        title  = pr.get('title') or ''
        body   = pr.get('body') or ''
        actor  = _safe(pr, 'user', 'login')
        labels = [l.get('name') for l in (pr.get('labels') or []) if l.get('name')]
        merged = pr.get('merged') or payload.get('action') == 'closed'

        # Try to find a Jira key in title or body
        jira_key = extract_jira_key(f"{title} {body}")

        return {
            "external_ticket_id": jira_key,
            "title":       title,
            "description": body,
            "ticket_url":  pr.get('html_url') or '',
            "change_type": determine_change_type(pr_title=title),
            "component":   repo,
            "severity":    "medium",
            "actors":      [actor] if actor else [],
            "raw_signals": {
                "event_kind": "pull_request",
                "pr_number":  pr.get('number'),
                "pr_merged":  merged,
                "pr_labels":  labels,
            },
        }

    # Push / commit event
    commits   = payload.get('commits') or []
    messages  = [c.get('message') or '' for c in commits if isinstance(c, dict)]
    first_msg = messages[0] if messages else ''
    all_msgs  = "\n".join(messages)
    actor     = _safe(payload, 'pusher', 'name')
    ref       = payload.get('ref') or ''

    # Collect all Jira keys from all commit messages
    all_jira_keys = list(dict.fromkeys(
        filter(None, [extract_jira_key(m) for m in messages])
    ))
    primary_key = all_jira_keys[0] if all_jira_keys else None

    return {
        "external_ticket_id": primary_key,
        "title":       f"Push to {repo} ({ref}): {first_msg[:80]}",
        "description": all_msgs,
        "ticket_url":  payload.get('compare') or '',
        "change_type": determine_change_type(pr_title=first_msg),
        "component":   repo,
        "severity":    "medium",
        "actors":      [actor] if actor else [],
        "raw_signals": {
            "event_kind":   "push",
            "push_ref":     ref,
            "commit_count": len(commits),
            "jira_keys":    all_jira_keys,
        },
    }


def preprocess_slack(payload: dict) -> dict:
    """Extract and normalise fields from a Slack event_callback payload."""
    event   = payload.get('event') or {}
    text    = event.get('text') or ''
    actor   = event.get('user')
    thread  = event.get('thread_ts')
    channel = event.get('channel')
    jira_key = extract_jira_key(text)

    if not jira_key:
        # No Jira key found — the event is stored as a standalone orphan signal
        logger.info("Slack message has no Jira key — storing as standalone signal (channel=%s)", channel)

    return {
        "external_ticket_id": jira_key,           # None is fine; stored as orphan signal
        "title":       f"Slack message: {text[:120]}" if text else "Slack message (empty)",
        "description": text,
        "ticket_url":  "",
        "change_type": "unknown",
        "component":   "slack",
        "severity":    "low",
        "actors":      [actor] if actor else [],
        "raw_signals": {
            "channel":      channel,
            "thread_ts":    thread,
            "has_thread":   thread is not None,
            "has_jira_key": jira_key is not None,
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

def process_unprocessed_events() -> None:
    """
    Query all unprocessed SourceEvents and produce a ChangeEvent for each one.

    Each event is marked as processed regardless of success or failure —
    a failure is recorded in the ChangeEvent's raw_signals so it can be
    investigated without blocking subsequent events.
    """
    session = Session()
    try:
        unprocessed = (
            session.query(SourceEvent)
            .filter(SourceEvent.processed == False)
            .all()
        )

        if not unprocessed:
            logger.info("No new events to process.")
            return

        logger.info("Processing %d new event(s)...", len(unprocessed))

        for event in unprocessed:
            preprocessor = PREPROCESSORS.get(event.source_type)
            if not preprocessor:
                logger.warning("  [SKIP] Unknown source_type '%s' for event %s", event.source_type, event.id)
                event.processed = True          # don't block the queue on unknown types
                continue

            try:
                data = preprocessor(event.raw_payload)
            except Exception as e:
                # Mark as processed so it doesn't block every subsequent run.
                # The error is surfaced in raw_signals for investigation.
                logger.error("  [ERROR] Failed to preprocess event %s: %s", event.id, e)
                event.processed = True
                error_change = ChangeEvent(
                    workspace_id=event.workspace_id,
                    source_event_id=event.id,
                    title=f"[PROCESSING ERROR] {event.source_type} event {event.id}",
                    description=str(e),
                    change_type="unknown",
                    component=event.source_type,
                    severity="low",
                    linked_issues=[],
                    linked_prs=[],
                    linked_threads=[],
                    actors=[],
                    raw_signals={"processing_error": str(e)},
                )
                session.add(error_change)
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
            logger.info("  [OK] %s event %s → change_event created", event.source_type.upper(), event.id)

        session.commit()
        logger.info("Processing complete.")

    except Exception as e:
        session.rollback()
        logger.error("Error during processing: %s", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    process_unprocessed_events()
