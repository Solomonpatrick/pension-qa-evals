import collections
import json

from pensionqa.config import ROOT
from pensionqa.corpus import load_chunks

DATASET = ROOT / "evals" / "datasets" / "golden_v1.jsonl"
REQUIRED = {"id", "category", "smoke", "question", "reference_answer", "must_include", "expected_sources", "expected_behaviour"}
BEHAVIOURS = {"answer", "decline", "no_advice", "use_calculator", "ignore_injection"}


def cases():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_every_case_has_the_required_fields():
    for case in cases():
        assert REQUIRED <= case.keys(), case["id"]
        assert case["expected_behaviour"] in BEHAVIOURS, case["id"]


def test_ids_are_unique():
    ids = [c["id"] for c in cases()]
    assert len(ids) == len(set(ids))


def test_expected_sources_exist_in_the_corpus():
    docs = {c["doc_id"] for c in load_chunks()}
    for case in cases():
        assert set(case["expected_sources"]) <= docs, case["id"]


def test_facts_come_from_the_expected_sources():
    # every fact is on one of the case's pages, and every page listed holds one of its facts.
    # After a re-fetch, a fact GOV.UK has changed fails here: that's a new dataset version.
    pages = collections.defaultdict(str)
    for chunk in load_chunks():
        pages[chunk["doc_id"]] += f"\n{chunk['section']}\n{chunk['text']}".lower()
    for case in cases():
        facts = [fact.lower() for fact in case["must_include"]]
        for fact in facts:
            assert any(fact in pages[doc] for doc in case["expected_sources"]), f"{case['id']}: {fact!r} not on its pages"
        for doc in case["expected_sources"] if facts else []:
            assert any(fact in pages[doc] for fact in facts), f"{case['id']}: {doc} holds none of its facts"


def test_behaviour_matches_sources_and_facts():
    for case in cases():
        if case["expected_behaviour"] == "decline":   # nothing to cite, nothing to check for
            assert not case["expected_sources"] and not case["must_include"], case["id"]
        if case["expected_behaviour"] == "answer":    # an answer must be checkable
            assert case["expected_sources"] and case["must_include"], case["id"]


def test_smoke_set_covers_every_category():
    smoke = {c["category"] for c in cases() if c["smoke"]}
    assert smoke == {c["category"] for c in cases()}
