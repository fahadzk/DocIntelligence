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



def test_citations_can_be_optional_without_disabling_claim_validation():
    passages = [{'text': 'The current account moved into surplus, and foreign exchange reserves rose.'}]
    assert validate_answer('The current account moved into surplus.', passages,
                           require_citations=False) == (True, 'validated', {1})
    assert validate_answer('The current account moved into surplus.', passages)[1] == 'missing_citations'
    assert not validate_answer('The population reached 500 million.', passages,
                               require_citations=False)[0]


def test_indicator_bullets_validate_against_separate_evidence_passages():
    passages = [
        {'text': 'KEY INDICATORS GROWTH Agriculture 2.89% Crops 1.44% Livestock 3.75% Forestry 2.02% Fishing 1.66%'},
        {'text': 'KEY INDICATORS (FY2026) GDP Growth 3.70% Agriculture 2.89% Industries 3.51% Services 4.09%'},
        {'text': 'KEY INDICATORS (FY2025) GDP Growth 2.68% Agriculture 0.56% Industries 4.77% Services 2.91%'},
    ]
    answer = "\n".join([
        '- Agriculture: 2.89%', '- Crops: 1.44%', '- Livestock: 3.75%',
        '- Forestry: 2.02%', '- Fishing: 1.66%', '- GDP Growth: 3.70%',
        '- Agriculture: 2.89%', '- Industries: 3.51%', '- Services: 4.09%',
        '- Agriculture: 0.56%', '- Industries: 4.77%', '- Services: 2.91%',
    ])
    assert validate_answer(answer, passages, require_citations=False) == (True, 'validated', {1, 2, 3})

def test_evidence_keeps_complete_relevant_text():
    def passage(id, text):
        return dict(id=id, document_id=id, segment_index=0, start_offset=0, end_offset=len(text), text=text)
    source = passage('history', 'The Mughals ' + 'had a cultural impact. ' * 35)
    other = passage('geography', 'Mountains and glaciers.')
    assert select_evidence('Who are the Mughals?', [other, source]) == [source]
