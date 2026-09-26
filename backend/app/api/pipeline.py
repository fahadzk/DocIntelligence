"""Pipeline configuration and provider-management API contracts."""
from uuid import UUID
import threading

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, SecretStr

from app.application.lab_search import LabSearchService
from app.application.pipeline_config import PipelineConfigService
from app.domain.documents import DocumentError
from app.main import get_lab_search_service, get_pipeline_config, get_plugin_registry, get_search_service
from app.plugins.cloud_providers import CloudProvider, HOSTS
from app.plugins.registry import PluginRegistry

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


@router.get("/api/plugins")
def plugins(registry: PluginRegistry = Depends(get_plugin_registry)):
    return {"plugins": registry.public()}


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
    models = provider(provider_id, registry).models()
    return {"connected": True, "model_count": len(models)}


@router.get("/api/providers/{provider_id}/models")
def provider_models(provider_id: str, registry: PluginRegistry = Depends(get_plugin_registry)):
    implementation = registry.get("llm_providers", provider_id).implementation()
    return {"models": implementation.models()}
