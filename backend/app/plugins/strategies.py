"""Built-in strategy implementations shared by Pipeline Lab and the existing engines."""
import math
import re
from uuid import NAMESPACE_URL, uuid5

from app.plugins.chunking_output import parse_boundaries


def sliding_window(project_id, document_id, content_hash, segments, version, settings, **_):
    size = settings["chunk_size"]
    overlap = settings["overlap"]
    passages = []
    for segment in segments:
        text = segment["text"]
        start = 0
        chunk = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + min(550, size // 2 + 100), end)
                if boundary > start:
                    end = boundary
            excerpt = text[start:end].strip()
            if excerpt:
                passages.append(_passage(project_id, document_id, content_hash, segment,
                                         version, chunk, start, end, excerpt))
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
            chunk += 1
    return passages


def _passage(project_id, document_id, content_hash, segment, version, chunk, start, end, text):
    return {"id": str(uuid5(NAMESPACE_URL, f"{document_id}:{segment['index']}:{chunk}:{version}")),
            "project_id": project_id, "document_id": document_id,
            "segment_index": segment["index"], "chunk_index": chunk,
            "label": segment["label"], "page_number": segment.get("page_number"),
            "paragraph_number": segment.get("paragraph_number"),
            "start_offset": start, "end_offset": end, "text": text,
            "content_hash": content_hash, "index_version": version}


def _paragraphs(text):
    return [(m.start(), m.end(), m.group().strip()) for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text)
            if m.group().strip()]


def _cosine(left, right):
    numerator = sum(a * b for a, b in zip(left, right))
    magnitude = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
    return numerator / magnitude if magnitude else 0.0


def semantic(project_id, document_id, content_hash, segments, version, settings, embeddings=None, **_):
    if embeddings is None or not embeddings.ready:
        raise RuntimeError("Set up the semantic embedding model before using semantic chunking.")
    result = []
    for segment in segments:
        paragraphs = _paragraphs(segment["text"])
        if not paragraphs:
            continue
        vectors = embeddings.embed([part[2] for part in paragraphs])
        breaks = {index for index in range(1, len(paragraphs))
                  if 1 - _cosine(vectors[index - 1], vectors[index]) >= settings["sensitivity"]}
        result.extend(_group_paragraphs(project_id, document_id, content_hash, segment, version,
                                        paragraphs, breaks, settings["min_chunk_size"], settings["max_chunk_size"]))
    return result


def llm(project_id, document_id, content_hash, segments, version, settings, llm=None, **_):
    if llm is None:
        raise RuntimeError("Select a language model provider for LLM chunking.")
    result = []
    for segment in segments:
        paragraphs = _paragraphs(segment["text"])
        if not paragraphs:
            continue
        # Bound each model call to a small window. Returned boundaries are checked below.
        breaks = set()
        for base in range(0, len(paragraphs), 12):
            batch = paragraphs[base:base + 12]
            if base:
                breaks.add(base)
            if len(batch) == 1:
                continue  # A single paragraph has no possible internal boundaries.
            numbered = "\n".join(f"{index}: {item[2][:220]}" for index, item in enumerate(batch))
            system = (f"Find paragraph boundaries where a new {settings['chunk_by']} begins. "
                      'Return only a JSON object {"boundaries": [1]}. '
                      f"Use zero-based paragraph indices from 1 to {len(batch) - 1}. "
                      'Return {"boundaries": []} if no new topic begins. '
                      "Do not include reasoning, Markdown, or rewritten source text.")
            model = settings.get("llm_model", settings.get("model", ""))
            for attempt in range(2):
                if hasattr(llm, "answer_chunk"):
                    response = llm.answer_chunk(system, numbered, model, paragraph_count=len(batch))
                else:
                    response = llm.answer(system, numbered)
                try:
                    indices = parse_boundaries(response, len(batch))
                    break
                except ValueError as error:
                    if attempt:
                        provider = settings.get("llm_provider", "llamacpp")
                        raise RuntimeError(
                            f"LLM chunking ({provider}, {model}) returned unusable boundaries "
                            f"after two attempts: {error}. Try a model that supports structured JSON output."
                        ) from error
                    system += " Your previous response was invalid. Return only the required JSON object."
            breaks.update(base + i for i in indices)
        result.extend(_group_paragraphs(project_id, document_id, content_hash, segment, version,
                                        paragraphs, breaks, 1, settings["max_chunk_size"]))
    return result


def _group_paragraphs(project_id, document_id, content_hash, segment, version, paragraphs, breaks, minimum, maximum):
    output = []
    start = paragraphs[0][0]
    end = start
    for index, (pstart, pend, _) in enumerate(paragraphs):
        if index and ((index in breaks and end - start >= minimum) or pend - start > maximum):
            output.extend(_slice_group(project_id, document_id, content_hash, segment, version, start, end, maximum, len(output)))
            start = pstart
        end = pend
    output.extend(_slice_group(project_id, document_id, content_hash, segment, version, start, end, maximum, len(output)))
    return output


def _slice_group(project_id, document_id, content_hash, segment, version, start, end, maximum, next_chunk):
    output = []
    while start < end:
        boundary = min(start + maximum, end)
        if boundary < end:
            space = segment["text"].rfind(" ", start + maximum // 2, boundary)
            if space > start:
                boundary = space
        excerpt = segment["text"][start:boundary].strip()
        if excerpt:
            output.append(_passage(project_id, document_id, content_hash, segment, version,
                                   next_chunk + len(output), start, boundary, excerpt))
        start = max(start + 1, boundary)
    return output


def rrf(rank, constant=40):
    return 1 / (constant + rank)


def weighted(rank, weight=0.5):
    # Rank contribution is explicit; it is not represented as vector similarity.
    return weight / (rank + 1)


def lexical_rerank(query, candidates):
    terms = set(re.findall(r"\w+", query.lower()))
    return sorted(candidates, key=lambda item: (-len(terms & set(re.findall(r"\w+", item["text"].lower()))),
                                                 item["final_rank"]))

