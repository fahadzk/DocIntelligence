"""Pipeline configuration and provider-management API contracts."""
from uuid import UUID
import json
import threading

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, SecretStr

from app.application.lab_search import LabSearchService
from app.application.pipeline_config import PipelineConfigService
from app.domain.documents import DocumentError
from app.main import (get_lab_search_service, get_pipeline_config, get_plugin_registry,
                      get_search_service, get_plugin_instance_store)
from app.plugins.cloud_providers import CloudProvider, HOSTS
from app.plugins.instances import DRIVERS, PluginInstanceStore, test_instance
from app.plugins.registry import PluginRegistry
from app.config.settings import get_settings

router = APIRouter(tags=["pipeline lab"])


class ConfigRequest(BaseModel):
    overrides: dict = Field(default_factory=dict)


class PreviewRequest(BaseModel):
    document_id: UUID


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    document_id: UUID | None = None


class CredentialRequest(BaseModel):
    key: SecretStr = Field(min_length=1)


class PluginInstanceRequest(BaseModel):
    id: str
    name: str
    category: str
    driver: str
    location: str
    enabled: bool = True
    settings: dict = Field(default_factory=dict)


@router.get("/api/plugins")
def plugins(registry: PluginRegistry = Depends(get_plugin_registry)):
    return {"plugins": registry.public()}


@router.get("/api/plugin-drivers")
def plugin_drivers():
    return {"drivers": DRIVERS}


@router.get("/api/plugin-instances")
def plugin_instances(store: PluginInstanceStore = Depends(get_plugin_instance_store),
                     registry: PluginRegistry = Depends(get_plugin_registry)):
    active = {(item["category"], item["id"]) for item in registry.public()}
    return {"plugins": [{**item, "active": (item["category"], item["id"]) in active}
                        for item in store.list()]}


def _instance_payload(body: PluginInstanceRequest) -> dict:
    return body.model_dump()


@router.post("/api/plugin-instances", status_code=201)
def create_plugin_instance(body: PluginInstanceRequest,
                           store: PluginInstanceStore = Depends(get_plugin_instance_store),
                           registry: PluginRegistry = Depends(get_plugin_registry)):
    if any(item["id"] == body.id for item in registry.public()):
        raise DocumentError("PLUGIN_ID_EXISTS", "That plugin ID is already in use.", 409)
    try:
        item = store.create(_instance_payload(body))
    except ValueError as error:
        raise DocumentError("INVALID_PLUGIN_CONFIG", str(error), 422) from error
    return {**item, "active": False, "restart_required": True}


@router.put("/api/plugin-instances/{plugin_id}")
def update_plugin_instance(plugin_id: str, body: PluginInstanceRequest,
                           store: PluginInstanceStore = Depends(get_plugin_instance_store)):
    if not body.enabled and _plugin_in_use(plugin_id):
        raise DocumentError("PLUGIN_IN_USE", "Choose another plugin in each Pipeline Lab project before disabling it.", 409)
    try:
        item = store.update(plugin_id, _instance_payload(body))
    except KeyError as error:
        raise DocumentError("PLUGIN_NOT_FOUND", "The configured plugin could not be found.", 404) from error
    except ValueError as error:
        raise DocumentError("INVALID_PLUGIN_CONFIG", str(error), 422) from error
    return {**item, "active": False, "restart_required": True}


def _contains_plugin(value, plugin_id: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_plugin(item, plugin_id) for item in value.values())
    if isinstance(value, list):
        return any(_contains_plugin(item, plugin_id) for item in value)
    return value == plugin_id


def _plugin_in_use(plugin_id: str) -> bool:
    with get_search_service().repository.connect() as connection:
        rows = connection.execute("SELECT overrides_json FROM project_pipeline_config").fetchall()
    return any(_contains_plugin(json.loads(row[0]), plugin_id) for row in rows)


@router.delete("/api/plugin-instances/{plugin_id}", status_code=204)
def delete_plugin_instance(plugin_id: str,
                           store: PluginInstanceStore = Depends(get_plugin_instance_store)):
    if _plugin_in_use(plugin_id):
        raise DocumentError("PLUGIN_IN_USE", "Choose another plugin in each Pipeline Lab project before deleting it.", 409)
    try:
        store.delete(plugin_id)
    except KeyError as error:
        raise DocumentError("PLUGIN_NOT_FOUND", "The configured plugin could not be found.", 404) from error


@router.post("/api/plugin-instances/test")
def test_plugin_connection(body: PluginInstanceRequest):
    try:
        return test_instance(_instance_payload(body), get_settings().data_dir)
    except ValueError as error:
        raise DocumentError("INVALID_PLUGIN_CONFIG", str(error), 422) from error


@router.get("/api/projects/{project_id}/pipeline")
def get_pipeline(project_id: UUID, config: PipelineConfigService = Depends(get_pipeline_config)):
    return config.state(project_id)


@router.put("/api/projects/{project_id}/pipeline")
def put_pipeline(project_id: UUID, body: ConfigRequest,
                 config: PipelineConfigService = Depends(get_pipeline_config)):
    return config.save(project_id, body.overrides)


@router.post("/api/projects/{project_id}/pipeline/index/ensure")
def ensure_index(project_id: UUID):
    search = get_search_service()
    search.documents.require_project(project_id)
    threading.Thread(target=search.rebuild_project, args=(project_id,), daemon=True,
                     name=f"reindex-{project_id}").start()
    return {"status": "indexing"}


@router.get("/api/projects/{project_id}/pipeline/index/status")
def lab_index_status(project_id: UUID):
    return get_search_service().statuses(project_id)


@router.post("/api/projects/{project_id}/pipeline/preview")
def preview(project_id: UUID, body: PreviewRequest, lab: LabSearchService = Depends(get_lab_search_service)):
    try:
        return lab.preview(project_id, body.document_id)
    except RuntimeError as error:
        raise DocumentError("PREVIEW_UNAVAILABLE", str(error), 409) from error


@router.post("/api/projects/{project_id}/pipeline/search")
def search(project_id: UUID, body: SearchRequest, lab: LabSearchService = Depends(get_lab_search_service)):
    return {"results": lab.search(project_id, body.query, body.document_id)}


def provider(provider_id: str, registry: PluginRegistry) -> CloudProvider:
    registry.get("llm_providers", provider_id)
    if provider_id not in HOSTS:
        raise DocumentError("INVALID_PROVIDER", "This provider does not use API credentials.", 422)
    return CloudProvider(provider_id)


@router.get("/api/providers")
def providers(registry: PluginRegistry = Depends(get_plugin_registry)):
    return [{"id": item, "configured": CloudProvider(item).configured()} for item in HOSTS]


@router.put("/api/providers/{provider_id}/credential")
def set_credential(provider_id: str, body: CredentialRequest,
                   registry: PluginRegistry = Depends(get_plugin_registry)):
    instance = provider(provider_id, registry)
    instance.save_credential(body.key.get_secret_value())
    return {"configured": True}


@router.delete("/api/providers/{provider_id}/credential")
def delete_credential(provider_id: str, registry: PluginRegistry = Depends(get_plugin_registry)):
    provider(provider_id, registry).remove_credential()
    return {"configured": False}


@router.post("/api/providers/{provider_id}/test")
def test_provider(provider_id: str, registry: PluginRegistry = Depends(get_plugin_registry)):
    models = registry.get("llm_providers", provider_id).implementation().models()
    return {"connected": True, "model_count": len(models)}


@router.get("/api/providers/{provider_id}/models")
def provider_models(provider_id: str, registry: PluginRegistry = Depends(get_plugin_registry)):
    implementation = registry.get("llm_providers", provider_id).implementation()
    return {"models": implementation.models()}


@router.get("/api/embedding-providers/{provider_id}/models")
def embedding_provider_models(provider_id: str,
                              registry: PluginRegistry = Depends(get_plugin_registry)):
    try:
        plugin = registry.get("embeddings", provider_id)
        settings = get_settings()
        if plugin.capabilities.get("managed"):
            from app.infrastructure.local_models import LocalEmbeddings
            implementation = LocalEmbeddings((settings.model_dir or settings.data_dir / "models") / "embeddings")
        else:
            implementation = plugin.implementation(settings.data_dir, model="")
        models = implementation.models()
        default_model = plugin.capabilities.get("default_model")
        if default_model and not any(item["id"] == default_model for item in models):
            models.insert(0, {"id": default_model, "name": default_model})
        return {"models": models}
    except ValueError as error:
        raise DocumentError("INVALID_EMBEDDING_PROVIDER", str(error), 422) from error
