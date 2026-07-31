"""Event surveys: three questions, answers 1 to 5, aggregate-only results.

Run from backend/: python -m pytest tests/test_surveys.py
"""
import asyncio
import os

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "t")
os.environ.setdefault("JWT_SECRET", "x")

import pytest
from bson import ObjectId

import surveys


class _Col:
    """Same shape as the stub in test_announcements, plus delete_many and a
    to_list that accepts None, which surveys uses to read every response."""

    def __init__(self):
        self.docs = {}

    def _match(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    async def find_one(self, query):
        for doc in self.docs.values():
            if self._match(doc, query):
                return doc
        return None

    def find(self, query):
        rows = [d for d in self.docs.values() if self._match(d, query)]

        class _C:
            async def to_list(self, _limit=None):
                return rows

        return _C()

    async def update_one(self, query, update, upsert=False):
        doc = await self.find_one(query)
        if doc:
            doc.update(update["$set"])
        elif upsert:
            oid = ObjectId()
            self.docs[oid] = {**query, **update["$set"], "_id": oid}

    async def delete_one(self, query):
        for oid, doc in list(self.docs.items()):
            if self._match(doc, query):
                del self.docs[oid]
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()

    async def delete_many(self, query):
        n = 0
        for oid, doc in list(self.docs.items()):
            if self._match(doc, query):
                del self.docs[oid]
                n += 1
        return type("R", (), {"deleted_count": n})()


def _run(coro):
    return asyncio.run(coro)


EVENT = ObjectId()
ALICE = ObjectId()
BOB = ObjectId()
Q = ["How was the venue?", "How useful were the intros?", "Would you return?"]


@pytest.fixture(autouse=True)
def _stub(monkeypatch):
    monkeypatch.setattr(surveys, "event_surveys", _Col())
    monkeypatch.setattr(surveys, "survey_responses", _Col())


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------

def test_upsert_stores_exactly_three_questions():
    out = _run(surveys.upsert(EVENT, Q))
    assert out["questions"] == Q
    assert _run(surveys.get(EVENT))["questions"] == Q


def test_upsert_refuses_the_wrong_number_of_questions():
    for bad in ([], Q[:2], Q + ["a fourth"]):
        with pytest.raises(surveys.SurveyError):
            _run(surveys.upsert(EVENT, bad))


def test_upsert_refuses_a_blank_question():
    with pytest.raises(surveys.SurveyError):
        _run(surveys.upsert(EVENT, ["Fine", "   ", "Also fine"]))


def test_upsert_collapses_whitespace_and_truncates():
    long_q = "x" * (surveys.MAX_QUESTION + 50)
    out = _run(surveys.upsert(EVENT, ["  spaced   out  ", "b", long_q]))
    assert out["questions"][0] == "spaced out"
    assert len(out["questions"][2]) == surveys.MAX_QUESTION


def test_get_returns_none_when_no_survey_exists():
    assert _run(surveys.get(EVENT)) is None


# --------------------------------------------------------------------------
# Changing the questions must not reattribute existing answers
# --------------------------------------------------------------------------

def test_changing_a_question_clears_previous_responses():
    """Answers are positional. Leaving them attached to a rewritten question
    would report answers to a question nobody was asked."""
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [5, 4, 3]))
    assert _run(surveys.results(EVENT))["response_count"] == 1

    changed = ["How was the venue?", "Would you come back?", "Would you return?"]
    _run(surveys.upsert(EVENT, changed))
    assert _run(surveys.results(EVENT))["response_count"] == 0
    assert _run(surveys.my_answers(EVENT, ALICE)) is None


def test_resaving_identical_questions_keeps_responses():
    """Editing and saving without changing the text is not a reset; a host who
    reopens the form and saves should not silently discard their feedback."""
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [5, 4, 3]))
    _run(surveys.upsert(EVENT, list(Q)))
    assert _run(surveys.results(EVENT))["response_count"] == 1
    assert _run(surveys.my_answers(EVENT, ALICE)) == [5, 4, 3]


# --------------------------------------------------------------------------
# Responding
# --------------------------------------------------------------------------

def test_cannot_respond_when_there_is_no_survey():
    with pytest.raises(surveys.SurveyError):
        _run(surveys.respond(EVENT, ALICE, [1, 2, 3]))


def test_response_must_answer_every_question():
    _run(surveys.upsert(EVENT, Q))
    for bad in ([], [1, 2], [1, 2, 3, 4]):
        with pytest.raises(surveys.SurveyError):
            _run(surveys.respond(EVENT, ALICE, bad))


def test_answers_outside_one_to_five_are_refused():
    _run(surveys.upsert(EVENT, Q))
    for bad in ([0, 3, 3], [3, 6, 3], [-1, 3, 3]):
        with pytest.raises(surveys.SurveyError):
            _run(surveys.respond(EVENT, ALICE, bad))


def test_a_boolean_is_not_an_answer():
    """bool is a subclass of int, so True would otherwise be stored and scored
    as 1 without anyone noticing."""
    _run(surveys.upsert(EVENT, Q))
    with pytest.raises(surveys.SurveyError):
        _run(surveys.respond(EVENT, ALICE, [True, 3, 3]))


def test_responding_twice_edits_rather_than_votes_twice():
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [1, 1, 1]))
    _run(surveys.respond(EVENT, ALICE, [5, 5, 5]))
    res = _run(surveys.results(EVENT))
    assert res["response_count"] == 1
    assert res["per_question"][0]["average"] == 5.0
    assert _run(surveys.my_answers(EVENT, ALICE)) == [5, 5, 5]


def test_my_answers_is_none_before_responding():
    _run(surveys.upsert(EVENT, Q))
    assert _run(surveys.my_answers(EVENT, ALICE)) is None


def test_one_persons_answers_do_not_leak_into_anothers():
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [1, 2, 3]))
    _run(surveys.respond(EVENT, BOB, [5, 5, 5]))
    assert _run(surveys.my_answers(EVENT, ALICE)) == [1, 2, 3]
    assert _run(surveys.my_answers(EVENT, BOB)) == [5, 5, 5]


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

def test_results_average_and_distribution():
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [5, 1, 3]))
    _run(surveys.respond(EVENT, BOB, [4, 2, 3]))
    res = _run(surveys.results(EVENT))

    assert res["response_count"] == 2
    first = res["per_question"][0]
    assert first["question"] == Q[0]
    assert first["average"] == 4.5
    assert first["count"] == 2
    assert first["distribution"] == {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1}
    assert res["per_question"][2]["distribution"]["3"] == 2


def test_average_is_none_not_zero_when_nobody_has_answered():
    """Zero is a score. "No responses yet" and "everyone gave the lowest score"
    must not render as the same number."""
    _run(surveys.upsert(EVENT, Q))
    res = _run(surveys.results(EVENT))
    assert res["response_count"] == 0
    assert all(q["average"] is None for q in res["per_question"])
    assert all(q["count"] == 0 for q in res["per_question"])


def test_results_never_include_who_answered():
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [5, 4, 3]))
    serialized = repr(_run(surveys.results(EVENT)))
    assert str(ALICE) not in serialized
    assert "user_id" not in serialized


def test_results_for_an_event_with_no_survey_are_empty():
    res = _run(surveys.results(EVENT))
    assert res["response_count"] == 0
    assert res["per_question"] == []


# --------------------------------------------------------------------------
# Deleting
# --------------------------------------------------------------------------

def test_delete_removes_the_survey_and_every_response():
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.respond(EVENT, ALICE, [5, 4, 3]))
    _run(surveys.respond(EVENT, BOB, [1, 1, 1]))

    assert _run(surveys.delete(EVENT)) is True
    assert _run(surveys.get(EVENT)) is None
    assert _run(surveys.results(EVENT))["response_count"] == 0
    assert _run(surveys.my_answers(EVENT, ALICE)) is None


def test_delete_reports_false_when_there_was_nothing_to_delete():
    assert _run(surveys.delete(EVENT)) is False


def test_surveys_are_scoped_to_their_event():
    other = ObjectId()
    _run(surveys.upsert(EVENT, Q))
    _run(surveys.upsert(other, ["a", "b", "c"]))
    _run(surveys.respond(EVENT, ALICE, [5, 5, 5]))

    assert _run(surveys.results(other))["response_count"] == 0
    assert _run(surveys.my_answers(other, ALICE)) is None
    _run(surveys.delete(other))
    assert _run(surveys.get(EVENT)) is not None
