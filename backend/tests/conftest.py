from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOCUMENT_INTELLIGENCE_DATA_DIR", str(tmp_path))
    from app.config.settings import get_settings
    from app.main import get_project_service, get_document_service
    get_settings.cache_clear()
    get_project_service.cache_clear()
    get_document_service.cache_clear()
    from app.main import app
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    get_project_service.cache_clear()
    get_document_service.cache_clear()
    get_settings.cache_clear()
