"""
main.py
-------
Flask application entry point for the Emiva Ingestion Service.

Registers three webhook endpoints:
  POST /webhooks/github  — GitHub push & pull-request events
  POST /webhooks/slack   — Slack event callbacks (and URL verification)
  POST /webhooks/jira    — Jira issue events

Database tables must be created or migrated using Alembic from emiva_core.
"""

import sys
import os

from flask import Flask, request, jsonify
from connectors.github_connector import handle_github_webhook
from connectors.slack_connector import handle_slack_webhook
from connectors.jira_connector import handle_jira_webhook
from emiva_core.core.logger import setup_logger
import os

logger = setup_logger("ingestion.main")

app = Flask(__name__)


@app.route('/webhooks/github', methods=['POST'])
def github_webhook():
    return handle_github_webhook(request.json, request.headers)


@app.route('/webhooks/slack', methods=['POST'])
def slack_webhook():
    return handle_slack_webhook(request.json, request.headers)


@app.route('/webhooks/jira', methods=['POST'])
def jira_webhook():
    return handle_jira_webhook(request.json, request.headers)


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200


if __name__ == '__main__':
    logger.info("Starting Emiva Ingestion Service on port 5000")
    app.run(port=5000, debug=True)
