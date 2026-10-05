from pensionqa.llm import FakeLLM, LLMResponse, fake_text
from pensionqa.rag import DECLINE, answer, parse_citations
from pensionqa.retrieval import load_retriever

CHUNKS = [{"chunk_id": "a#0"}, {"chunk_id": "b#1"}]


def test_parse_citations_handles_grouped_and_invalid_tags():
    cited, invalid = parse_citations("Fact one [S1]. Fact two [S1, S2]. Made up [S9].", CHUNKS)
    assert cited == ["a#0", "b#1"]
    assert invalid == ["S9"]


def test_answer_maps_tags_to_the_chunks_shown():
    llm = FakeLLM([fake_text("Your employer must pay at least 3% [S1].")])
    result = answer("How much must my employer pay?", load_retriever(), llm)
    assert result.cited == [result.sources[0]["chunk_id"]]
    assert "Sources:" in llm.calls[0]["messages"][0]["content"]


def test_decline_text_is_passed_through():
    result = answer("What did the average pension fund return last year?", load_retriever(), FakeLLM())
    assert result.text == DECLINE and result.cited == []


def test_refusal_is_recorded_not_hidden():
    # CLAUDE.md: handle refusal and max_tokens explicitly rather than assuming text came back
    result = answer("What is the annual allowance?", load_retriever(), FakeLLM([LLMResponse(text="", stop_reason="refusal")]))
    assert result.stop_reason == "refusal" and result.text == "" and result.cited == []
