"""Event survey: exactly three questions the host writes, each answered 1 to 5.

Deliberately narrow. The marketing copy once promised six question types with
charts; this is the opposite of that on purpose. Three questions is short enough
that attendees actually finish it, and a fixed 1 to 5 scale means the results
are comparable across events without anyone choosing a scale.

The shape is one survey per event rather than a survey builder. There is no
"which survey" anywhere in the API: the event is the survey's identity, which
removes a whole class of "responded to the wrong one" bugs and keeps the host
UI to three text boxes.

Responses are stored with the responder's id so a person can edit their own
answers and cannot stuff the ballot, but `results` returns aggregate numbers
ONLY and never who said what. Note the honest limit of that: on an event with
two attendees the totals still narrow it down, so the UI does not promise
anonymity it cannot deliver. It says the host sees totals, which is true.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId

from database import event_surveys, survey_responses

QUESTION_COUNT = 3
MIN_ANSWER = 1
MAX_ANSWER = 5
MAX_QUESTION = 200


class SurveyError(Exception):
    """Bad input, with a message intended for the person who typed it."""


def clean_question(value) -> str:
    return " ".join(str(value or "").split())[:MAX_QUESTION]


def _serialize(doc: dict) -> dict:
    return {
        "event_id": str(doc["event_id"]),
        "questions": list(doc.get("questions", [])),
        "updated_at": doc.get("updated_at"),
    }


async def upsert(event_id: ObjectId, questions) -> dict:
    """Create or replace the event's survey.

    Replacing the questions deliberately clears the responses. Answers are
    stored positionally, so leaving them in place after question two changes
    from "How was the venue" to "Would you come back" would silently reattribute
    every previous answer to a question nobody was asked.
    """
    cleaned = [clean_question(q) for q in questions]
    if len(cleaned) != QUESTION_COUNT:
        raise SurveyError(f"A survey has exactly {QUESTION_COUNT} questions.")
    if any(q == "" for q in cleaned):
        raise SurveyError("Every question needs some text.")

    existing = await event_surveys.find_one({"event_id": event_id})
    if existing and list(existing.get("questions", [])) != cleaned:
        await survey_responses.delete_many({"event_id": event_id})

    doc = {
        "event_id": event_id,
        "questions": cleaned,
        "updated_at": datetime.now(timezone.utc),
    }
    await event_surveys.update_one(
        {"event_id": event_id}, {"$set": doc}, upsert=True
    )
    return _serialize(doc)


async def get(event_id: ObjectId) -> dict | None:
    doc = await event_surveys.find_one({"event_id": event_id})
    return _serialize(doc) if doc else None


async def respond(event_id: ObjectId, user_id, answers) -> dict:
    """Record one person's answers, replacing their previous ones.

    Upserted on (event_id, user_id) so a second submission is an edit rather
    than a second vote.
    """
    survey = await event_surveys.find_one({"event_id": event_id})
    if not survey:
        raise SurveyError("This event has no survey.")

    values = list(answers)
    if len(values) != QUESTION_COUNT:
        raise SurveyError(f"Answer all {QUESTION_COUNT} questions.")
    for v in values:
        if not isinstance(v, int) or isinstance(v, bool):
            raise SurveyError("Answers must be whole numbers.")
        if not MIN_ANSWER <= v <= MAX_ANSWER:
            raise SurveyError(f"Answers run from {MIN_ANSWER} to {MAX_ANSWER}.")

    await survey_responses.update_one(
        {"event_id": event_id, "user_id": user_id},
        {"$set": {
            "event_id": event_id,
            "user_id": user_id,
            "answers": values,
            "updated_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    return {"answers": values}


async def my_answers(event_id: ObjectId, user_id):
    doc = await survey_responses.find_one({"event_id": event_id, "user_id": user_id})
    return list(doc.get("answers", [])) if doc else None


async def results(event_id: ObjectId) -> dict:
    """Aggregate only. No identities, by design; see the module docstring.

    A response whose length does not match the current question count is
    skipped rather than padded. That should not happen, because changing the
    questions clears the responses, but padding would invent answers and an
    invented answer in a feedback report is worse than a smaller sample.
    """
    survey = await event_surveys.find_one({"event_id": event_id})
    questions = list(survey.get("questions", [])) if survey else []
    rows = await survey_responses.find({"event_id": event_id}).to_list(None)

    per_question = []
    for index in range(len(questions)):
        values = [
            r["answers"][index]
            for r in rows
            if len(r.get("answers", [])) == len(questions)
        ]
        distribution = {str(n): 0 for n in range(MIN_ANSWER, MAX_ANSWER + 1)}
        for v in values:
            key = str(v)
            if key in distribution:
                distribution[key] += 1
        per_question.append({
            "question": questions[index],
            # None rather than 0: "no responses yet" and "everyone said the
            # lowest score" must not render as the same number.
            "average": round(sum(values) / len(values), 2) if values else None,
            "distribution": distribution,
            "count": len(values),
        })

    return {"response_count": len(rows), "per_question": per_question}


async def delete(event_id: ObjectId) -> bool:
    result = await event_surveys.delete_one({"event_id": event_id})
    await survey_responses.delete_many({"event_id": event_id})
    return result.deleted_count > 0
