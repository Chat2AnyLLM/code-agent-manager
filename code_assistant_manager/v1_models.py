"""Unified /v1/models fetcher."""

import json
import logging
import os
import threading
import time
import uuid
import ipaddress
from urllib.parse import urlparse

import requests

from .env_loader import load_env

logger = logging.getLogger(__name__)

COPILOT_PLUGIN_VERSION = "copilot-chat/0.26.7"
COPILOT_USER_AGENT = "GitHubCopilotChat/0.26.7"
API_VERSION = "2025-04-01"


def get_copilot_token(github_token: str):
    """Calls GitHub API: GET /copilot_internal/v2/token"""
    headers = {
        "authorization": f"token {github_token}",
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": "models-fetcher/1.0",
    }
    r = requests.get(
        "https://api.github.com/copilot_internal/v2/token", headers=headers, timeout=30
    )
    r.raise_for_status()
    return r.json()


def copilot_headers(copilot_token: str):
    return {
        "Authorization": f"Bearer {copilot_token}",
        "content-type": "application/json",
        "copilot-integration-id": "vscode-chat",
        "editor-version": "vscode/1.0.1",
        "editor-plugin-version": COPILOT_PLUGIN_VERSION,
        "user-agent": COPILOT_USER_AGENT,
        "openai-intent": "conversation-panel",
        "x-github-api-version": API_VERSION,
        "x-request-id": str(uuid.uuid4()),
        "x-vscode-user-agent-library-version": "electron-fetch",
    }


def start_refresh_loop(github_token: str, state: dict):
    """Background thread that refreshes the Copilot token and stores it in state."""

    def _loop():
        while True:
            try:
                info = get_copilot_token(github_token)
                state["copilot_token"] = info["token"]
                refresh_in = info.get("refresh_in", 300)
                sleep_for = max(30, refresh_in - 60)
            except Exception as e:
                logger.error(f"Failed to refresh Copilot token: {e}")
                sleep_for = 60
            time.sleep(sleep_for)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def fetch_v1_models(url: str, headers: dict):
    """Fetch models from a /v1/models endpoint."""
    params = {
        "return_wildcard_routes": "false",
        "include_model_access_groups": "false",
        "only_model_access_groups": "false",
        "include_metadata": "false",
    }

    # Determine if SSL verification should be enabled
    verify_ssl = True
    try:
        parsed = urlparse(url)
        if parsed.hostname:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback:
                    verify_ssl = False
            except ValueError:
                pass
    except Exception:
        pass

    r = requests.get(url, params=params, headers=headers, timeout=30, verify=verify_ssl)
    r.raise_for_status()
    return r.json()


def list_models():
    """List available models. Returns model IDs, one per line."""
    load_env()

    endpoint = os.environ.get("endpoint")
    if not endpoint:
        logger.error("endpoint environment variable is required")
        raise SystemExit("endpoint environment variable is required")

    if endpoint.endswith("/v1/models"):
        url = endpoint
    elif endpoint.endswith("/v1"):
        # If it ends with /v1 but not /v1/models, append /models
        url = f"{endpoint}/models"
    else:
        # If it doesn't contain /v1 at all, append /v1/models
        if endpoint.endswith("/"):
            url = f"{endpoint}v1/models"
        else:
            url = f"{endpoint}/v1/models"

    api_key = os.environ.get("api_key")
    github_token = os.environ.get("GITHUB_TOKEN")

    headers = {}
    if api_key:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "accept": "application/json",
            "x-litellm-api-key": api_key,  # For LiteLLM backward compatibility
        }
    elif github_token:
        state = {}
        start_refresh_loop(github_token, state)
        # Wait a bit for the token
        for _ in range(5):
            if "copilot_token" in state:
                break
            time.sleep(0.5)

        copilot_token = state.get("copilot_token")
        if not copilot_token:
            # Try one last synchronous fetch
            info = get_copilot_token(github_token)
            copilot_token = info["token"]

        headers = copilot_headers(copilot_token)
    else:
        # No auth provided, try without it
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json"
        }

    try:
        models_data = fetch_v1_models(url, headers)
        for m in models_data.get("data", []):
            print(m.get("id"))
    except Exception as e:
        logger.error(f"Failed to fetch models: {e}")
        raise SystemExit(f"Failed to fetch models: {e}")


if __name__ == "__main__":
    list_models()
