from flask import Flask, request, jsonify
from database.db import init_db
from connectors.github_connector import handle_github_webhook
from connectors.slack_connector import handle_slack_webhook
from connectors.jira_connector import handle_jira_webhook
import os

app = Flask(__name__)

# Initialize database
init_db()

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
    app.run(port=5000, debug=True)
