# Emiva Ingestion Pipeline

A Flask-based webhook ingestion service that captures raw signals from **GitHub**, **Slack**, and **Jira**, preprocesses each one automatically, and writes a structured `change_event` row immediately — one per incoming webhook.

## 🚀 Key Features

- **Real-Time Processing**: Every webhook is preprocessed and stored as a `change_event` the moment it arrives.
- **Row-by-Row Pipeline**: No merging — one `source_event` → one `change_event`, always.
- **Multi-Source Support**: Handles GitHub PRs **and** push/commit events, Slack messages (with or without a Jira key), and Jira issue webhooks.
- **Fault-Isolated**: A crashing event is marked as processed with an error record so it never blocks the queue.
- **Lossless Raw Storage**: Every incoming payload is preserved in `source_event` for full auditability.
- **Multi-Tenancy**: Native `workspace_id` support for isolated data streams.

## 🏗️ Architecture

```
Webhook (GitHub / Slack / Jira)
        │
        ▼
   main.py  (Flask routes)
        │
        ▼
  Source Connector  (connectors/)
        │  — saves raw payload
        ▼
  source_event table  (processed = False)
        │  — auto-triggers processor
        ▼
  ChangeEventProcessor  (services/)
        │  — preprocesses, one row per event
        ▼
  change_event table  (processed = False → ready for Stage 3)
```

## 🛠️ Setup

### 1. Clone & Install
```bash
git clone https://github.com/EmivaAI/emiva.git
cd emiva-data-work

python -m venv venv
# Windows:   .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

### 2. Initialise the Database
```bash
# Database tables must be created or migrated using Alembic from the root directory.
cd ..
alembic upgrade head
cd injestion
```

### 3. Expose with ngrok (for live webhooks)
```bash
ngrok http 5000
```
Copy the forwarding URL (e.g. `https://xxxx.ngrok-free.app`).

### 4. Configure Webhooks
| Source | Endpoint |
|--------|----------|
| Jira   | `https://YOUR_URL/webhooks/jira` |
| GitHub | `https://YOUR_URL/webhooks/github` |
| Slack  | `https://YOUR_URL/webhooks/slack` |

### 5. Start the Server
```bash
python main.py
```

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/github` | Receives GitHub PR & push events |
| `POST` | `/webhooks/slack`  | Receives Slack event callbacks |
| `POST` | `/webhooks/jira`   | Receives Jira issue webhooks |
| `GET`  | `/health`          | Health check |

---

## 🔍 Diagnostic Tools

| Tool | Command | Description |
|------|---------|-------------|
| **Source Viewer** | `python view_data.py` | Last 20 raw `source_event` rows |
| **Change Viewer** | `python view_changes.py` | Last 20 `change_event` rows |

---

## 🐛 Recent Bug Fixes

| Issue | Fix |
|-------|-----|
| Null nested fields crashed preprocessors | Added `_safe()` helper for null-safe nested dict access |
| GitHub push/commit events were ignored | `github_connector` now passes event type; push events produce full `change_event` rows with all Jira keys extracted |
| Slack messages without a Jira key were silently dropped | Stored as standalone signals; `has_jira_key` flag added to `raw_signals` |
| A crashing event blocked the entire queue forever | Errored events are marked `processed=True` and a `[PROCESSING ERROR]` `change_event` is written |

---

## 📊 Data Schema

### `source_event`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `workspace_id` | String | Tenant isolation |
| `source_type` | String | `github`, `slack`, `jira` |
| `raw_payload` | JSON | Full original webhook payload |
| `processed` | Boolean | Set to `True` after preprocessing |
| `created_at` | DateTime | UTC timestamp |

### `change_event`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID | Primary key |
| `source_event_id` | UUID (FK) | Links back to `source_event` |
| `external_ticket_id` | String | Jira key if present (e.g. `EMIVA-42`) |
| `title` / `description` | String / Text | Human-readable summary |
| `change_type` | String | `bug_fix`, `feature`, `chore`, `docs`, `unknown` |
| `component` | String | Repo name, Jira project, or `slack` |
| `severity` | String | `low`, `medium`, `high`, `critical` |
| `actors` | JSON | List of user names/IDs involved |
| `raw_signals` | JSON | Source-specific structured flags |
| `processed` | Boolean | For Stage 3 analysis |

---
Developed for the **EmivaAI Ingestion Pipeline**.
