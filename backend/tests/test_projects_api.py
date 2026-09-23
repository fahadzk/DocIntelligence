def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "document-intelligence-backend"


def test_project_lifecycle(client):
    created = client.post("/api/projects", json={"name": "UFO Research", "description": "Case files"})
    assert created.status_code == 201
    project = created.json()

    assert client.get(f"/api/projects/{project['id']}").json()["name"] == "UFO Research"
    updated = client.patch(f"/api/projects/{project['id']}", json={"name": "UAP Research"})
    assert updated.status_code == 200
    assert updated.json()["name"] == "UAP Research"
    assert len(client.get("/api/projects").json()) == 1
    assert client.delete(f"/api/projects/{project['id']}").status_code == 204
    missing = client.get(f"/api/projects/{project['id']}")
    assert missing.status_code == 404
    assert missing.json()["code"] == "PROJECT_NOT_FOUND"


def test_blank_project_name_is_rejected(client):
    response = client.post("/api/projects", json={"name": "   "})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
