def test_activity_records_document_lifecycle(client):
    project = client.post("/api/projects", json={"name": "Activity"}).json()["id"]
    imported = client.post(
        f"/api/projects/{project}/documents",
        files=[("files", ("notes.txt", b"A recorded document lifecycle.", "text/plain"))],
    )
    assert imported.status_code == 200
    events = client.get(f"/api/projects/{project}/activity").json()
    actions = {event["action"] for event in events}
    assert {"import.received", "import.persisted", "extraction.started", "extraction.completed", "content.persisted"} <= actions
    stored = next(event for event in events if event["action"] == "import.persisted")
    assert stored["details"]["database"] == "SQLite"
    assert client.get(f"/api/projects/{project}/activity?limit=1").status_code == 200