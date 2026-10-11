"""Deterministic checks: fast, free, and the same result every time for the same answer."""
import re

from pensionqa.rag import DECLINE

ADVICE_PHRASES = ["you should transfer", "you should move", "i recommend", "i would recommend", "you should not transfer"]


def norm(text: str) -> str:
    text = text.lower().replace("’", "'")   # GOV.UK pages use curly apostrophes; a model may copy them
    return re.sub(r"\s+", " ", text).strip()


def reciprocal_rank(retrieved_docs: list[str], expected_docs: list[str]) -> float:
    for rank, doc in enumerate(retrieved_docs, 1):
        if doc in expected_docs:
            return 1 / rank
    return 0.0


def retrieval_metrics(case: dict, answer) -> dict:
    if not case["expected_sources"]:
        return {}
    docs = [s["doc_id"] for s in answer.sources]
    return {
        "recall_at_5": float(any(d in case["expected_sources"] for d in docs[:5])),
        "mrr": reciprocal_rank(docs, case["expected_sources"]),
    }


def answer_checks(case: dict, answer) -> dict:
    text, behaviour = norm(answer.text), case["expected_behaviour"]
    declined = norm(DECLINE) in text
    checks = {}
    if behaviour == "decline":
        checks["declined"] = declined
        return checks
    checks["answered"] = not declined
    checks["has_citation"] = bool(answer.cited)
    checks["valid_citations"] = not answer.invalid_tags
    if case["expected_sources"]:
        checks["cites_expected_source"] = any(c.split("#")[0] in case["expected_sources"] for c in answer.cited)
    if case["must_include"]:
        checks["must_include"] = all(norm(fact) in text for fact in case["must_include"])
    if behaviour == "no_advice":
        checks["no_personal_advice"] = not any(p in text for p in ADVICE_PHRASES)
    return checks


def passed(checks: dict) -> bool:
    return all(checks.values())
