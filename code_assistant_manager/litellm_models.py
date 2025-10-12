"""Litellm API models fetcher."""

import json
import logging
import os

import requests

from .env_loader import load_env

logger = logging.getLogger(__name__)


def fetch_litellm_models(api_key: str, base_url: str = "https://192.168.1.100:4142"):
    """Fetch models from Litellm API."""
    url = f"{base_url}/v1/models"
    params = {
        "return_wildcard_routes": "false",
        "include_model_access_groups": "false",
        "only_model_access_groups": "false",
        "include_metadata": "false",
    }
    headers = {
        "accept": "application/json",
        "x-litellm-api-key": api_key,
    }
    # Security: Enable SSL certificate verification for secure connections
    r = requests.get(url, params=params, headers=headers, timeout=30, verify=True)
    r.raise_for_status()
    return r.json()


def list_models():
    """List available Litellm models. Returns model IDs, one per line."""
    # Load environment variables from .env file
    logger.debug("Loading environment variables from .env file")
    load_env()
    logger.debug("Environment variables loaded")

    api_key = os.environ.get("API_KEY_LITELLM")
    if not api_key:
        logger.error("API_KEY_LITELLM environment variable is required but not found")
        raise SystemExit("API_KEY_LITELLM environment variable is required")

    logger.debug("Fetching Litellm models")
    try:
        models_data = fetch_litellm_models(api_key)
        model_count = len(models_data.get("data", []))
        logger.debug(f"Found {model_count} models")

        for m in models_data.get("data", []):
            print(m.get("id"))
    except requests.RequestException as e:
        logger.error(f"Failed to fetch models: {e}")
        raise SystemExit(f"Failed to fetch models: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse response: {e}")
        raise SystemExit(f"Failed to parse response: {e}")


if __name__ == "__main__":
    list_models()
