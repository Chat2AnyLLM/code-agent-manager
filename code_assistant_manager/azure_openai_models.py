"""Azure OpenAI deployed models fetcher using Azure SDK."""

import logging
import os
from typing import Dict, List, Any

from .env_loader import load_env

# Optional Azure SDK imports - only available if installed
try:
    from azure.identity import DefaultAzureCredential
    from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
    from azure.mgmt.resource import SubscriptionClient
    AZURE_SDK_AVAILABLE = True
except ImportError:
    DefaultAzureCredential = None
    CognitiveServicesManagementClient = None
    SubscriptionClient = None
    AZURE_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)


def _fetch_deployed_models_for_subscription(subscription_id: str, credential) -> List[str]:
    """Fetch deployed Azure AI models in a subscription using Azure SDK.

    Returns a list of deployed model names (strings).
    """
    if not AZURE_SDK_AVAILABLE:
        logger.warning("Azure SDK not available. Install azure-identity, azure-mgmt-cognitiveservices, azure-mgmt-resource to enable deployed model discovery.")
        return []

    results: List[str] = []
    try:
        client = CognitiveServicesManagementClient(credential, subscription_id)
        accounts = list(client.accounts.list())

        for acct in accounts:
            try:
                rg = acct.id.split("/")[4]
                acct_name = getattr(acct, 'name', '') or ''

                if not acct_name:
                    continue

                # Determine service type to filter for OpenAI accounts
                service_type = None
                try:
                    if hasattr(acct, 'kind') and getattr(acct, 'kind'):
                        service_type = acct.kind
                    elif hasattr(acct, 'properties') and hasattr(acct.properties, 'kind') and acct.properties.kind:
                        service_type = acct.properties.kind
                    elif hasattr(acct, 'sku') and getattr(acct, 'sku') and hasattr(acct.sku, 'name'):
                        service_type = acct.sku.name
                except Exception:
                    service_type = None

                # Only process OpenAI accounts
                if not service_type or 'openai' not in service_type.lower():
                    continue

                # Get deployments for this account
                for dep in client.deployments.list(resource_group_name=rg, account_name=acct.name):
                    model = None
                    try:
                        model = dep.properties.model
                    except Exception:
                        model = getattr(getattr(dep, 'properties', None), 'model', None)

                    model_name = None
                    if model and getattr(model, 'name', None):
                        model_name = model.name

                    if model_name and model_name not in results:
                        results.append(model_name)

            except Exception as e:
                logger.debug(f"Failed to process account {acct_name}: {e}")
                continue

        # Remove duplicates while preserving order
        seen = set()
        unique_results = []
        for item in results:
            if item not in seen:
                seen.add(item)
                unique_results.append(item)

        return unique_results

    except Exception as e:
        logger.error(f"Failed to fetch deployed models for subscription {subscription_id}: {e}")
        return []


def _fetch_all_deployed_models_via_sdk(credential, subscription_ids: List[str] | None = None) -> List[str]:
    """Fetch deployed Azure AI models across subscriptions using Azure SDK.

    Returns unique deployed model names.
    """
    if not AZURE_SDK_AVAILABLE:
        return []

    subs = subscription_ids or []
    if not subs:
        try:
            sub_client = SubscriptionClient(credential)
            subs = [s.subscription_id for s in sub_client.subscriptions.list()]
        except Exception as e:
            logger.error(f"Failed to discover subscriptions: {e}")
            return []

    all_models: List[str] = []
    for sid in subs:
        try:
            models = _fetch_deployed_models_for_subscription(sid, credential)
            all_models.extend(models)
        except Exception as e:
            logger.debug(f"Failed to fetch models for subscription {sid}: {e}")
            continue

    # Remove duplicates while preserving order
    seen = set()
    unique_results = []
    for item in all_models:
        if item not in seen:
            seen.add(item)
            unique_results.append(item)

    return unique_results


def fetch_deployed_azure_openai_models() -> List[str]:
    """Fetch deployed Azure OpenAI models using Azure SDK.

    Returns a list of deployed model names.
    If Azure SDK is not available or authentication fails, returns empty list.
    """
    if not AZURE_SDK_AVAILABLE:
        logger.warning("Azure SDK not available for deployed model discovery")
        return []

    try:
        credential = DefaultAzureCredential()
        models = _fetch_all_deployed_models_via_sdk(credential)
        logger.info(f"Found {len(models)} deployed Azure OpenAI models")
        return models
    except Exception as e:
        logger.error(f"Failed to authenticate to Azure or fetch deployed models: {e}")
        return []


def list_models():
    """List deployed Azure OpenAI models. Returns model IDs, one per line."""
    load_env()

    # Check if we should use SDK-based deployed model discovery
    use_sdk = os.environ.get("AZURE_USE_SDK", "true").lower() in ("true", "1", "yes")

    if use_sdk:
        models = fetch_deployed_azure_openai_models()
        if models:
            for model in models:
                print(model)
            return

        logger.warning("No deployed models found via Azure SDK. Falling back to HTTP API approach.")

    # Fallback: Try HTTP API approach (similar to original implementation)
    # This will show all available models, not just deployed ones
    endpoint = os.environ.get("endpoint")
    if not endpoint:
        logger.error("endpoint environment variable is required")
        raise SystemExit("endpoint environment variable is required")

    # Azure OpenAI endpoints typically end with /openai/v1
    # We need to append /models to get the models endpoint
    if endpoint.endswith("/openai/v1"):
        url = f"{endpoint}/models"
    elif endpoint.endswith("/v1"):
        # If it ends with /v1 but not /openai/v1, append /models
        url = f"{endpoint}/models"
    else:
        # If it doesn't contain /v1 at all, append /v1/models
        if endpoint.endswith("/"):
            url = f"{endpoint}v1/models"
        else:
            url = f"{endpoint}/v1/models"

    api_key = os.environ.get("api_key")
    if not api_key:
        logger.error("api_key environment variable is required")
        raise SystemExit("api_key environment variable is required")

    # Import here to avoid circular imports
    import requests

    try:
        # Try different API versions if the first one fails
        api_versions = ["2024-02-01", "2023-12-01-preview", "2023-05-15"]

        models_data = None
        for api_version in api_versions:
            try:
                headers = {
                    "api-key": api_key,
                    "Content-Type": "application/json",
                }
                params = {"api-version": api_version}
                r = requests.get(url, headers=headers, params=params, timeout=30)
                r.raise_for_status()
                models_data = r.json()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    # Authentication failed, don't try other versions
                    raise
                logger.debug(f"API version {api_version} failed: {e}")
                continue
            except Exception as e:
                logger.debug(f"API version {api_version} failed: {e}")
                continue

        if models_data is None:
            # Try without api-version parameter
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json",
            }
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            models_data = r.json()

        for m in models_data.get("data", []):
            print(m.get("id"))

    except Exception as e:
        logger.error(f"Failed to fetch Azure OpenAI models: {e}")
        raise SystemExit(f"Failed to fetch Azure OpenAI models: {e}")


if __name__ == "__main__":
    list_models()
