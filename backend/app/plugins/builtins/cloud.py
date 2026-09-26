"""Hosted and local HTTP LLM provider plugins."""
from app.plugins.registry import Plugin
from app.plugins.cloud_providers import CloudProvider
from app.plugins.ollama_provider import OllamaProvider


def hosted(provider_id: str, name: str) -> Plugin:
    return Plugin(provider_id, name, "Uses your own API key; evidence is sent to the provider.",
                  "llm_providers", (
                      {"key": "model", "label": "Model", "type": "model_select"},
                      {"key": "temperature", "label": "Temperature", "type": "slider", "min": 0, "max": 1, "step": 0.05},
                      {"key": "max_output_tokens", "label": "Maximum output tokens", "type": "number", "min": 64, "max": 4096}),
                  {"local": False, "model_discovery": True, "temperature": True,
                   "streaming": False, "system_prompt": True},
                  lambda _directory=None: CloudProvider(provider_id))


PLUGINS = [Plugin("ollama", "Ollama (local)", "Uses models installed in your local Ollama server at localhost:11434.",
                  "llm_providers", (
                      {"key": "model", "label": "Model", "type": "model_select"},
                      {"key": "temperature", "label": "Temperature", "type": "slider", "min": 0, "max": 1, "step": 0.05},
                      {"key": "max_output_tokens", "label": "Maximum output tokens", "type": "number", "min": 64, "max": 4096}),
                  {"local": True, "model_discovery": True, "temperature": True,
                   "streaming": False, "system_prompt": True},
                  lambda _directory=None: OllamaProvider())]
PLUGINS += [hosted(provider_id, name) for provider_id, name in
            (("openai", "OpenAI"), ("anthropic", "Anthropic"), ("google", "Google"))]
