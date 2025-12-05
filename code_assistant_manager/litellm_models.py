"""Litellm API models fetcher."""

import json
import logging
import os

import requests

from .env_loader import load_env
from .config import ConfigManager

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

    # Make the request
    r = requests.get(url, params=params, headers=headers, timeout=30, verify=verify_ssl)
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

    # Get base URL from environment (set by EndpointManager) or from config
    base_url = os.environ.get("endpoint")
    if not base_url:
        # Try to get from config
        try:
            config = ConfigManager()
            litellm_config = config.get_endpoint_config("litellm")
            base_url = litellm_config.get("endpoint", "https://192.168.1.100:4142")
        except Exception as e:
            logger.debug(f"Could not load config, using default URL: {e}")
            base_url = "https://192.168.1.100:4142"

    logger.debug("Fetching Litellm models")
    try:
        models_data = fetch_litellm_models(api_key, base_url)
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
