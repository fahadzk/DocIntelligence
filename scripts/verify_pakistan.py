"""Offline regression check against the user's existing Pakistan project (read-only)."""
import os
import sys
import json
import socket
from pathlib import Path
from time import perf_counter
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from app.main import get_search_service  # noqa: E402


def deny_network(*args, **kwargs):
    raise RuntimeError("Network access disabled during offline RAG verification")


socket.socket.connect = deny_network
socket.create_connection = deny_network


def main():
    service = get_search_service()
    with service.repository.connect() as connection:
        project = connection.execute("SELECT id FROM projects WHERE name=?", ("Pakistan",)).fetchone()
    if project is None:
        raise SystemExit("Pakistan project not found.")
    cases = [
        ("Who are the Mughals?", True),
        ("How does the main river support farming in Pakistan?", True),
        ("What is the password for my email account?", False),
        ("Which countries share land borders with Pakistan?", False),
    ]
    for question, expected in cases:
        start = perf_counter()
        response = service.ask(UUID(project["id"]), question)
        print(json.dumps(dict(question=question, seconds=round(perf_counter()-start, 2),
                              answer=response["answer"], supported=response["supported"],
                              sources=[(e["passage"]["display_name"], e["passage"]["label"]) for e in response["evidence"]]),
                         ensure_ascii=True), flush=True)
        assert response["supported"] is expected
        assert not response["answer"].startswith("The retrieved documents state:")
    service.operations.close()


if __name__ == "__main__":
    main()
