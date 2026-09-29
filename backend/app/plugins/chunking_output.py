"""Structured chunk-boundary output shared by local model providers."""
import json
import re

def chunk_boundary_schema(paragraph_count: int = 12) -> dict:
    if not 2 <= paragraph_count <= 12:
        raise ValueError("Boundary requests must contain between 2 and 12 paragraphs")
    return {
        "type": "object",
        "properties": {"boundaries": {
            "type": "array", "maxItems": paragraph_count - 1,
            # Enumeration constrains generation; numeric limits alone may be ignored by grammars.
            "items": {"type": "integer", "enum": list(range(1, paragraph_count))},
        }},
        "required": ["boundaries"],
        "additionalProperties": False,
    }


CHUNK_BOUNDARY_SCHEMA = chunk_boundary_schema()


def parse_boundaries(response: str, paragraph_count: int) -> list[int]:
    if not isinstance(response, str) or not response.strip():
        raise ValueError("The model returned an empty response")
    if "<think>" in response and "</think>" not in response:
        raise ValueError("The model returned incomplete reasoning instead of boundaries")
    # Some models include reasoning or Markdown even when JSON is requested.
    text = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if text.startswith(("[", "{")):
            raise ValueError("The model returned incomplete or malformed JSON")
        # Accept one complete JSON value surrounded by explanatory prose.
        decoder = json.JSONDecoder()
        candidates = []
        position = 0
        while position < len(text):
            match = re.search(r"[\[{]", text[position:])
            if not match:
                break
            start = position + match.start()
            try:
                value, end = decoder.raw_decode(text, start)
            except json.JSONDecodeError as error:
                raise ValueError("The model returned incomplete or malformed JSON") from error
            candidates.append(value)
            position = end
        if len(candidates) != 1:
            raise ValueError("The model did not return one complete JSON boundary list")
        parsed = candidates[0]
    if isinstance(parsed, dict):
        if set(parsed) != {"boundaries"}:
            raise ValueError("The model returned an unexpected JSON object")
        parsed = parsed["boundaries"]
    if not isinstance(parsed, list) or any(type(index) is not int or not 1 <= index < paragraph_count
                                           for index in parsed):
        raise ValueError("The model returned invalid paragraph boundaries")
    return sorted(set(parsed))
