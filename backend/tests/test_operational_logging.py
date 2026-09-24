import json
from uuid import uuid4

from app.infrastructure.operational_logging import OperationalLogger


def test_operational_records_are_written_as_json_lines(tmp_path):
    logger = OperationalLogger(tmp_path)
    project_id = uuid4()
    logger.record(project_id, "chunking.completed", "Split extracted content into passages",
                  details={"max_characters": 900}, duration_ms=17)
    logger.close()

    records = [json.loads(line) for line in (tmp_path / "logs" / "document-intelligence.jsonl").read_text(encoding="utf-8").splitlines()]
    assert records[-1]["event"] == "chunking.completed"
    assert records[-1]["project_id"] == str(project_id)
    assert records[-1]["details"]["max_characters"] == 900
    assert records[-1]["duration_ms"] == 17