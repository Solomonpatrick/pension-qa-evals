import json
from types import SimpleNamespace

from evals.judge import SCHEMA, judge
from pensionqa.llm import FakeLLM, LLMResponse, fake_text

GRADE = {"claims": [{"claim": "Employer pays 3%", "supported": True},
                    {"claim": "The limit rises in 2027", "supported": False}],
         "grounded": False, "correctness": 3, "source_quality": 2, "rationale": "One claim is not in the sources."}
CASE = {"question": "q", "reference_answer": "r"}
ANSWER = SimpleNamespace(text="a", sources=[{"title": "t", "section": "s", "url": "u", "text": "x"}])


def test_judge_sends_the_schema_and_lists_unsupported_claims():
    llm = FakeLLM([fake_text(json.dumps(GRADE))])
    grade = judge(CASE, ANSWER, llm)
    assert llm.calls[0]["json_schema"] == SCHEMA
    assert grade["unsupported_claims"] == ["The limit rises in 2027"]


def test_grounded_follows_the_claims_not_the_judges_own_flag():
    contradictory = dict(GRADE, grounded=True)   # says grounded, yet lists an unsupported claim
    grade = judge(CASE, ANSWER, FakeLLM([fake_text(json.dumps(contradictory))]))
    assert grade["grounded"] is False


def test_a_refused_judgement_is_an_error_row_that_keeps_its_cost():
    refused = LLMResponse(text="", stop_reason="refusal", input_tokens=1200, output_tokens=5)
    grade = judge(CASE, ANSWER, FakeLLM([refused]))
    assert grade == {"error": "refusal", "judge_tokens": [1200, 5]}
