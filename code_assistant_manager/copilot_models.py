"""GitHub Copilot API models fetcher."""

import logging
import os
import threading
import time
import uuid

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
    # Security: Add timeout to prevent hanging connections
    r = requests.get(
        "https://api.github.com/copilot_internal/v2/token", headers=headers, timeout=30
    )
    r.raise_for_status()
    return r.json()


def copilot_base_url(account_type: str = "individual") -> str:
    return (
        "https://api.githubcopilot.com"
        if account_type == "individual"
        else f"https://api.{account_type}.githubcopilot.com"
    )


def copilot_headers(
    copilot_token: str, vs_code_version: str = "1.0.1", vision: bool = False
):
    h = {
        "Authorization": f"Bearer {copilot_token}",
        "content-type": "application/json",
        "copilot-integration-id": "vscode-chat",
        "editor-version": f"vscode/{vs_code_version}",
        "editor-plugin-version": COPILOT_PLUGIN_VERSION,
        "user-agent": COPILOT_USER_AGENT,
        "openai-intent": "conversation-panel",
        "x-github-api-version": API_VERSION,
        "x-request-id": str(uuid.uuid4()),
        "x-vscode-user-agent-library-version": "electron-fetch",
    }
    if vision:
        h["copilot-vision-request"] = "true"
    return h


def fetch_models(copilot_token: str, base_url: str = "https://192.168.1.100:5000"):
    url = f"{base_url}/v1/models"
    # Security: Add timeout to prevent hanging connections

    # Determine if SSL verification should be enabled
    # For internal/private IPs, skip verification as they often use self-signed certificates
    import ipaddress
    from urllib.parse import urlparse

    verify_ssl = True
    try:
        parsed = urlparse(base_url)
        if parsed.hostname:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                # Skip verification for private IPs (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8)
                if ip.is_private or ip.is_loopback:
                    verify_ssl = False
            except ValueError:
                # Not an IP address, keep verification enabled
                pass
    except Exception:
        # If parsing fails, keep verification enabled
        pass

    # Check if we're using a configured endpoint with API key authentication
    # (instead of direct GitHub Copilot API access)
    api_key = os.environ.get("api_key")
    if api_key:
        # Use OpenAI-compatible API key authentication for proxy endpoints
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    else:
        # Use GitHub Copilot token authentication for direct API access
        headers = copilot_headers(copilot_token)

    # Make the request
    r = requests.get(url, headers=headers, timeout=30, verify=verify_ssl)
    r.raise_for_status()
    return r.json()


def start_refresh_loop(github_token: str, state: dict):
    """Background thread that refreshes the Copilot token and stores it in state."""

    def _loop():
        while True:
            info = get_copilot_token(github_token)
            state["copilot_token"] = info["token"]
            refresh_in = info.get("refresh_in", 300)
            sleep_for = max(30, refresh_in - 60)
            time.sleep(sleep_for)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def list_models():
    """List available GitHub Copilot models. Returns model IDs, one per line."""
    # Load environment variables from .env file
    logger.debug("Loading environment variables from .env file")
    load_env()
    logger.debug("Environment variables loaded")

    # If EndpointManager provided an API key (proxy mode), we don't need GitHub token auth.
    if os.environ.get("api_key"):
        copilot_token = ""
    else:
        github_token = os.environ.get("GITHUB_TOKEN")
        if not github_token:
            logger.error("GITHUB_TOKEN environment variable is required but not found")
            raise SystemExit("GITHUB_TOKEN environment variable is required")

        logger.debug("Starting Copilot token refresh loop")
        state = {}
        start_refresh_loop(github_token, state)

        time.sleep(1)

        copilot_token = state.get("copilot_token")
        if not copilot_token:
            logger.debug("No token in state, fetching directly")
            info = get_copilot_token(github_token)
            copilot_token = info["token"]
            state["copilot_token"] = copilot_token

    # Get base URL from environment (set by EndpointManager) or from config
    base_url = os.environ.get("endpoint")
    if not base_url:
        # Try to get from config
        try:
            from .config import ConfigManager
            config = ConfigManager()
            copilot_config = config.get_endpoint_config("copilot-api")
            base_url = copilot_config.get("endpoint", "https://192.168.1.100:5000")
        except Exception as e:
            logger.debug(f"Could not load config, using default URL: {e}")
            base_url = "https://192.168.1.100:5000"

    logger.debug("Fetching Copilot models")
    models = fetch_models(copilot_token, base_url)
    model_count = len(models.get("data", []))
    logger.debug(f"Found {model_count} models")

    for m in models.get("data", []):
        print(m.get("id"))


if __name__ == "__main__":
    list_models()
