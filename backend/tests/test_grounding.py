from app.application.grounding import select_evidence, validate_answer


def test_cited_hallucination_is_rejected():
    passages = [{'text': 'Pakistan has mountains and glaciers in its northern region.'}]
    assert not validate_answer('Pakistan borders Afghanistan, Iran and India. [1]', passages)[0]
    assert not validate_answer('Pakistan has 500 mountains. [1]', passages)[0]


def test_supported_paraphrase_and_invalid_citations():
    passages = [{'text': 'The Mughals (1526–1857) left a cultural and architectural mark.'}]
    assert validate_answer('The Mughals left an architectural and cultural mark. [1]', passages)[0]
    assert not validate_answer('The Mughals left a cultural mark. [9]', passages)[0]
    assert not validate_answer('The Mughals left a cultural mark.', passages)[0]
    assert validate_answer('Insufficient evidence.', passages)[1] == 'insufficient_evidence'


def test_evidence_keeps_complete_relevant_text():
    def passage(id, text):
        return dict(id=id, document_id=id, segment_index=0, start_offset=0, end_offset=len(text), text=text)
    source = passage('history', 'The Mughals ' + 'had a cultural impact. ' * 35)
    other = passage('geography', 'Mountains and glaciers.')
    assert select_evidence('Who are the Mughals?', [other, source]) == [source]
