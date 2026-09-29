from types import SimpleNamespace

import pytest

from app.plugins.chunking_output import CHUNK_BOUNDARY_SCHEMA, chunk_boundary_schema, parse_boundaries
from app.plugins.strategies import llm


@pytest.mark.parametrize("response", [
    "[1, 2]", '{"boundaries": [1, 2]}',
    '```json\n{"boundaries": [1, 2]}\n```',
    'Here are the boundaries: [1, 2].',
    '<think>Consider [99] as an example.</think>\n{"boundaries": [1, 2]}',
])
def test_parse_formatted_boundaries(response):
    assert parse_boundaries(response, 3) == [1, 2]


@pytest.mark.parametrize("response", [
    "", "   ", "No boundaries", "[0]", "[3]", "[true]", '["1"]', "[-1]",
    "[1.0]", 'Here are boundaries: {"boundaries": [1]', "Here: [1", '{"boundaries": [1]', "[1", "[1] and [2]",
    '{"unrelated": [1]}', '<think>Maybe [1]',
])
def test_reject_invalid_or_incomplete_boundaries(response):
    with pytest.raises(ValueError):
        parse_boundaries(response, 3)


def test_chunking_retries_and_preserves_source_offsets():
    responses = iter(["", '```json\n{"boundaries": [1]}\n```'])
    prompts = []
    def answer_chunk(system, prompt, model, *, paragraph_count):
        assert paragraph_count == 2
        prompts.append(system)
        return next(responses)
    segment = {"index": 0, "text": "First topic.\n\nSecond topic.", "label": "Page 1", "page_number": 1}
    chunks = llm("p", "d", "hash", [segment], "v",
                 {"chunk_by": "topic", "max_chunk_size": 100, "llm_model": "chosen"},
                 llm=SimpleNamespace(answer_chunk=answer_chunk))
    assert len(prompts) == 2
    assert "previous response was invalid" in prompts[1]
    assert len(chunks) == 2
    for chunk in chunks:
        assert segment["text"][chunk["start_offset"]:chunk["end_offset"]].strip() == chunk["text"]
        assert chunk["page_number"] == 1


def test_persistently_invalid_output_fails_after_one_retry():
    calls = []
    def answer_chunk(*args, **kwargs):
        calls.append(args)
        return "invalid"
    with pytest.raises(RuntimeError, match="after two attempts"):
        llm("p", "d", "hash", [{"index": 0, "text": "First.\n\nSecond.", "label": "Page 1"}],
            "v", {"chunk_by": "topic", "max_chunk_size": 100},
            llm=SimpleNamespace(answer_chunk=answer_chunk))
    assert len(calls) == 2


def test_single_paragraph_skips_model_and_still_respects_maximum():
    def answer_chunk(*args, **kwargs):
        pytest.fail("Single-paragraph segments should not call the model")
    chunks = llm("p", "d", "hash", [{"index": 0, "text": "word " * 60, "label": "Page 1"}],
                 "v", {"chunk_by": "topic", "max_chunk_size": 100},
                 llm=SimpleNamespace(answer_chunk=answer_chunk))
    assert len(chunks) >= 3
    assert all(len(chunk["text"]) <= 100 for chunk in chunks)


def test_local_chunking_uses_json_schema_without_changing_answer_format(tmp_path, monkeypatch):
    from app.infrastructure.local_models import LocalLLM
    calls = []
    class Model:
        def reset(self):
            pass
        def create_chat_completion(self, **options):
            calls.append(options)
            return {"choices": [{"message": {"content": '{"boundaries": []}'}}]}
    provider = LocalLLM(tmp_path)
    provider._model = Model()
    provider._loaded_path = tmp_path / "chosen.gguf"
    monkeypatch.setattr(provider, "ready_for", lambda _: True)
    provider.answer_chunk("system", "prompt", "chosen.gguf")
    assert calls[-1]["response_format"] == {"type": "json_object", "schema": CHUNK_BOUNDARY_SCHEMA}
    assert calls[-1]["max_tokens"] == 512
    provider.answer_chunk("system", "prompt", "chosen.gguf", paragraph_count=3)
    assert calls[-1]["response_format"]["schema"] == chunk_boundary_schema(3)
    provider.answer("system", "prompt", {"model": "chosen.gguf"})
    assert "response_format" not in calls[-1]


def test_ollama_chunking_requests_structured_output_and_disables_thinking(monkeypatch):
    from app.plugins.ollama_provider import OllamaProvider
    calls = []
    def request(method, path, payload):
        calls.append(payload)
        return {"message": {"content": '{"boundaries": []}'}}
    provider = OllamaProvider()
    monkeypatch.setattr(provider, "_request", request)
    assert provider.answer_chunk("system", "prompt", "chosen") == '{"boundaries": []}'
    assert calls[-1]["format"] == CHUNK_BOUNDARY_SCHEMA
    boundaries = calls[-1]["format"]["properties"]["boundaries"]
    assert boundaries["maxItems"] == 11
    assert boundaries["items"]["enum"] == list(range(1, 12))
    assert calls[-1]["think"] is False
    provider.answer_chunk("system", "prompt", "chosen", paragraph_count=3)
    boundaries = calls[-1]["format"]["properties"]["boundaries"]
    assert boundaries["maxItems"] == 2
    assert boundaries["items"]["enum"] == [1, 2]
    provider.answer("system", "prompt", "chosen", 0, 300)
    assert "format" not in calls[-1]
    assert "think" not in calls[-1]
