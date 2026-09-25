"""Cloud providers are optional and registered only as explicit Pipeline Lab choices."""
from app.plugins.registry import Plugin
from app.plugins.cloud_providers import CloudProvider

PLUGINS = [
    Plugin(provider_id, name, "Uses your own API key; evidence is sent to the provider.",
           "llm_providers", (
               {"key": "model", "label": "Model", "type": "model_select"},
               {"key": "temperature", "label": "Temperature", "type": "slider", "min": 0, "max": 1, "step": 0.05},
               {"key": "max_output_tokens", "label": "Maximum output tokens", "type": "number", "min": 64, "max": 4096}),
           {"local": False, "model_discovery": True, "temperature": True,
            "streaming": False, "system_prompt": True},
           lambda _directory=None, provider_id=provider_id: CloudProvider(provider_id))
    for provider_id, name in (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("google", "Google"))
]
