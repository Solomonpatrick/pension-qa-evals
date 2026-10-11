from types import SimpleNamespace

from evals.checks import answer_checks, passed

CASE = {"expected_behaviour": "answer", "must_include": ["8%", "3%"],
        "expected_sources": ["workplace-pensions-what-you-your-employer-and-the-government-pay"]}
DECLINE_CASE = {"expected_behaviour": "decline", "must_include": [], "expected_sources": []}


def fake_answer(text, cited=(), invalid=()):
    return SimpleNamespace(text=text, cited=list(cited), invalid_tags=list(invalid), sources=[])


def test_a_good_answer_passes():
    ans = fake_answer("At least 8% in total, 3% from your employer [S1].",
                      cited=["workplace-pensions-what-you-your-employer-and-the-government-pay#2"])
    assert passed(answer_checks(CASE, ans))


def test_missing_fact_and_uncited_answer_fail():
    checks = answer_checks(CASE, fake_answer("At least 8% in total."))
    assert checks["must_include"] is False and checks["has_citation"] is False


def test_unanswerable_case_expects_the_decline_line():
    assert passed(answer_checks(DECLINE_CASE, fake_answer("I can't find that in the guidance provided.")))
    assert not passed(answer_checks(DECLINE_CASE, fake_answer("Funds returned 7% last year [S1].", cited=["x#0"])))


def test_decline_line_matches_with_a_curly_apostrophe():
    # the GOV.UK pages use ’, so a model that copies their style must still count as declining
    assert passed(answer_checks(DECLINE_CASE, fake_answer("I can’t find that in the guidance provided.")))
