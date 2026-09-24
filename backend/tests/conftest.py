from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_DATA_DIR", str(tmp_path))
    from app.config.settings import get_settings
    from app.main import get_operational_logger, get_project_service, get_document_service, get_search_service
    get_settings.cache_clear()
    get_operational_logger.cache_clear()
    get_project_service.cache_clear()
    get_document_service.cache_clear()
    get_search_service.cache_clear()
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client
    get_project_service.cache_clear()
    get_document_service.cache_clear()
    get_search_service.cache_clear()
    get_operational_logger.cache_clear()
    get_settings.cache_clear()
