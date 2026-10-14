"""LLM-as-judge with a written rubric and a JSON schema the model must follow."""
import json
from pathlib import Path

from pensionqa.rag import format_sources

RUBRIC_VERSION = "judge_v1"
RUBRIC = (Path(__file__).parent / "rubrics" / f"{RUBRIC_VERSION}.md").read_text(encoding="utf-8")

SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"claim": {"type": "string"}, "supported": {"type": "boolean"}},
                "required": ["claim", "supported"],
                "additionalProperties": False,
            },
        },
        "grounded": {"type": "boolean"},
        "correctness": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "source_quality": {"type": "integer", "enum": [1, 2, 3]},
        "rationale": {"type": "string"},
    },
    "required": ["claims", "grounded", "correctness", "source_quality", "rationale"],
    "additionalProperties": False,
}


def judge(case: dict, answer, llm) -> dict:
    prompt = (
        f"QUESTION:\n{case['question']}\n\nREFERENCE ANSWER:\n{case['reference_answer']}\n\n"
        f"SOURCES:\n{format_sources(answer.sources)}\n\nANSWER:\n{answer.text}"
    )
    # max_tokens is a cap, not a budget: a cut-off judgement is wasted, so leave plenty of room
    resp = llm.complete(RUBRIC, [{"role": "user", "content": prompt}], json_schema=SCHEMA, max_tokens=16000)
    tokens = [resp.input_tokens, resp.output_tokens]
    if resp.stop_reason in ("refusal", "max_tokens"):
        return {"error": resp.stop_reason, "judge_tokens": tokens}   # a failed call still costs money
    grade = json.loads(resp.text)
    grade["unsupported_claims"] = [c["claim"] for c in grade["claims"] if not c["supported"]]
    grade["grounded"] = not grade["unsupported_claims"]   # defined by the claims, so the two can't disagree
    grade["judge_tokens"] = tokens
    return grade
