"""Discover and validate only bundled Pipeline Lab plugins."""
from dataclasses import dataclass, field
import importlib
import pkgutil
from typing import Callable


FIELD_TYPES = {"slider", "number", "boolean", "select", "text", "model_select"}
CATEGORIES = {"chunking", "embeddings", "vector_stores", "retrieval", "fusion", "rerankers", "llm_providers"}


@dataclass(frozen=True)
class Plugin:
    id: str
    name: str
    description: str
    category: str
    schema: tuple[dict, ...] = ()
    capabilities: dict = field(default_factory=dict)
    implementation: Callable | None = None

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description,
                "category": self.category, "schema": list(self.schema), "capabilities": self.capabilities}


class PluginRegistry:
    def __init__(self, plugins: list[Plugin]):
        self._plugins = {}
        for plugin in plugins:
            if not plugin.id.isidentifier() or plugin.category not in CATEGORIES:
                raise ValueError(f"Invalid plugin identity: {plugin.id}")
            if (plugin.category, plugin.id) in self._plugins:
                raise ValueError(f"Duplicate plugin: {plugin.id}")
            if not callable(plugin.implementation):
                raise ValueError(f"Plugin has no implementation: {plugin.id}")
            names = set()
            for setting in plugin.schema:
                if setting.get("type") not in FIELD_TYPES or not setting.get("key") or setting["key"] in names:
                    raise ValueError(f"Invalid schema for plugin: {plugin.id}")
                names.add(setting["key"])
            self._plugins[plugin.category, plugin.id] = plugin

    def get(self, category: str, plugin_id: str) -> Plugin:
        try:
            return self._plugins[category, plugin_id]
        except KeyError as error:
            raise ValueError(f"Unknown {category} plugin: {plugin_id}") from error

    def public(self) -> list[dict]:
        return [plugin.public() for plugin in self._plugins.values()]

    @classmethod
    def discover(cls) -> "PluginRegistry":
        package = importlib.import_module("app.plugins.builtins")
        discovered = []
        for module in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            implementation = importlib.import_module(module.name)
            discovered.extend(getattr(implementation, "PLUGINS", ()))
        return cls(discovered)
