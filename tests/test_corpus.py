import collections

from pensionqa.config import ROOT
from pensionqa.corpus import MAX_WORDS, load_chunks


def test_every_chunk_has_a_source_and_text():
    for chunk in load_chunks():
        # zz- pages are the planted test pages you add in Phase 10
        assert chunk["url"].startswith("https://www.gov.uk/") or chunk["doc_id"].startswith("zz-")
        assert chunk["text"].strip()


def test_chunks_respect_the_size_limit():
    # only a chunk made of one very long line can exceed the limit
    for chunk in load_chunks():
        assert len(chunk["text"].split()) <= MAX_WORDS or "\n" not in chunk["text"], chunk["chunk_id"]


def test_no_two_pages_have_identical_text():
    bodies = collections.defaultdict(list)
    for chunk in load_chunks():
        bodies[chunk["doc_id"]].append(chunk["text"])
    texts = ["\n".join(parts) for parts in bodies.values()]
    assert len(texts) == len(set(texts)), "two URLs saved the same page: check for redirects"


def test_corpus_matches_sources_txt():
    # every listed page saved some text, and no page dropped from the list lingers in data/raw
    sources = set((ROOT / "data" / "sources.txt").read_text(encoding="utf-8").split())
    assert {c["url"] for c in load_chunks() if not c["doc_id"].startswith("zz-")} == sources


def test_every_page_has_its_own_title():
    # guide parts share their guide's h1, so the part's own h1 must be in the title too
    titles = {c["doc_id"]: c["title"] for c in load_chunks()}
    assert len(set(titles.values())) == len(titles)


def test_step_by_step_sidebar_is_stripped():
    # GOV.UK repeats this sidebar on many pages; left in, it pollutes search results
    for chunk in load_chunks():
        assert "step by step" not in f"{chunk['section']}\n{chunk['text']}".lower(), chunk["chunk_id"]


def test_contribution_table_keeps_its_headers():
    # the minimum contribution rates exist only in an HTML table
    row = "The minimum your employer pays 3%; You pay 5%; Total minimum contribution 8%"
    assert any(row in chunk["text"] for chunk in load_chunks())
