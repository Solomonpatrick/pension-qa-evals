import pytest

from pensionqa.retrieval import load_retriever, normalise

retriever = load_retriever()


@pytest.mark.parametrize("question, expected_doc", [
    ("How much must my employer pay into my workplace pension?", "workplace-pensions-what-you-your-employer-and-the-government-pay"),
    ("What is the annual allowance?", "tax-on-your-private-pension-annual-allowance"),
    ("How do I find a lost pension?", "find-pension-contact-details"),
    ("Is a final salary scheme a workplace pension?", "pension-types"),
])
def test_expected_page_is_in_top_3(question, expected_doc):
    docs = [hit["doc_id"] for hit in retriever.search(question, k=3)]
    assert expected_doc in docs


def test_aliases_map_to_the_guidance_wording():
    assert normalise("My final salary scheme") == "my defined benefit scheme"
    assert normalise("auto-enrolment rules") == "automatic enrolment rules"
