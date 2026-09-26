"""Evidence selection and conservative claim validation for local answers."""
import re

STOP = set('a an the is are was were be been being who what when where why how do does did of to in on at for from and or with this that it its their they these those according document documents retrieved source sources says say about now over'.split())


def terms(text: str) -> set[str]:
    return {word.lower().rstrip('s') for word in re.findall(r'[A-Za-z]{3,}', text)
            if word.lower() not in STOP}


def select_evidence(question: str, candidates: list[dict], max_passages: int = 3,
                    character_budget: int = 4800) -> list[dict]:
    query = terms(question)
    ranked = sorted(enumerate(candidates), key=lambda item: (
        -len(query & terms(item[1]['text'])), item[0]))
    if ranked and query & terms(ranked[0][1]['text']):
        ranked = [item for item in ranked if query & terms(item[1]['text'])]
    selected = []
    budget = character_budget
    for _, passage in ranked:
        if len(selected) >= max_passages:
            break
        if any(passage['document_id'] == old['document_id']
               and passage['segment_index'] == old['segment_index']
               and min(passage['end_offset'], old['end_offset']) - max(passage['start_offset'], old['start_offset'])
               > 0.6 * min(len(passage['text']), len(old['text'])) for old in selected):
            continue
        if len(passage['text']) <= budget:
            selected.append(passage)
            budget -= len(passage['text'])
    return selected


def validate_answer(answer: str, passages: list[dict], require_citations: bool = True) -> tuple[bool, str, set[int]]:
    """Check claim overlap and citation shape; lexical checks cannot prove entailment."""
    if re.search(r"\b(?:cannot find support|insufficient evidence|not enough information|don.t know)\b", answer, re.I):
        return False, 'insufficient_evidence', set()
    blocks = [block.strip() for block in re.split(r'\n\s*\n', answer) if block.strip()]
    used = set()
    if not blocks:
        return False, 'empty_answer', used
    for block in blocks:
        ids = {int(n) for n in re.findall(r'\[(\d+)\]', block)}
        if require_citations and (not ids or not re.search(r'\[\d+\][.!?\s]*$', block)):
            return False, 'missing_citations', set()
        if any(n < 1 or n > len(passages) for n in ids):
            return False, 'invalid_citation', set()
        text = re.sub(r'\[\d+\]', '', block)
        claims = re.split(r'\n\s*(?=(?:[-*•]\s+|\d+[.)]\s+))', text.strip())
        for claim_text in claims:
            claim_text = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s+', '', claim_text)
            for sentence in re.split(r'(?<=[.!?])\s+', claim_text.strip()):
                claim = terms(sentence)
                if not claim:
                    continue
                names = {w.lower().rstrip('s') for w in re.findall(r'\b[A-Z][a-z]{2,}\b', sentence)
                         if w.lower() not in STOP and w.lower() not in {'however', 'also', 'following'}}
                numbers = set(re.findall(r'\b\d+(?:[,.]\d+)*\b', sentence))
                candidates = ids or set(range(1, len(passages) + 1))
                supported_by = {n for n in candidates
                                if names <= terms(passages[n-1]['text'])
                                and numbers <= set(re.findall(r'\b\d+(?:[,.]\d+)*\b', passages[n-1]['text']))
                                and len(claim & terms(passages[n-1]['text'])) / len(claim) >= 0.55}
                if not supported_by:
                    return False, 'unsupported_claim', set()
                if not ids:
                    used.update(supported_by)
        used.update(ids)
    return True, 'validated', used
