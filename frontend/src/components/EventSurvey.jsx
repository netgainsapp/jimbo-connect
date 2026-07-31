import { useCallback, useEffect, useState } from "react";
import { ClipboardList, Trash2, Pencil, X } from "lucide-react";

import { surveysApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";

const QUESTION_COUNT = 3;
const SCALE = [1, 2, 3, 4, 5];
const MAX_QUESTION = 200;
const BLANK = Array(QUESTION_COUNT).fill("");

/**
 * The event survey: three questions the host writes, answered 1 to 5.
 *
 * Attendees see the questions and their own answers. The host sees the results
 * and the controls, and does not get the answering form: a survey exists to
 * tell the organizer how it went, so the organizer scoring their own event
 * would only muddy the numbers.
 *
 * Results are aggregate. The component never receives individual answers,
 * because the API never sends them. It also does not promise anonymity, since
 * on a small event the totals still narrow it down; the copy says the host sees
 * totals, which is true.
 */
export default function EventSurvey({ eventId, canManage = false }) {
  const [survey, setSurvey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [drafts, setDrafts] = useState(BLANK);
  const [answers, setAnswers] = useState(Array(QUESTION_COUNT).fill(null));
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const load = useCallback(async () => {
    try {
      const s = await surveysApi.get(eventId);
      setSurvey(s);
      if (s.my_answers) setAnswers(s.my_answers);
    } catch {
      // 404 is the ordinary case for an event without a survey.
      setSurvey(null);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    load();
  }, [load]);

  const saveQuestions = async () => {
    if (drafts.some((q) => !q.trim())) {
      toast.show("Every question needs some text.", "error");
      return;
    }
    setBusy(true);
    try {
      await surveysApi.upsert(eventId, drafts);
      setEditing(false);
      // Reload rather than patch: changing a question clears the responses
      // server side, and the results on screen must reflect that immediately
      // instead of showing totals for questions that no longer exist.
      await load();
      toast.show("Survey saved");
    } catch (e) {
      toast.show(e?.message || "Could not save that survey", "error");
    } finally {
      setBusy(false);
    }
  };

  const submitAnswers = async () => {
    if (answers.some((a) => a == null)) {
      toast.show("Answer all three questions.", "error");
      return;
    }
    setBusy(true);
    try {
      await surveysApi.respond(eventId, answers);
      setSurvey((prev) => ({ ...prev, my_answers: answers }));
      toast.show("Thanks for the feedback");
    } catch (e) {
      toast.show(e?.message || "Could not save your answers", "error");
    } finally {
      setBusy(false);
    }
  };

  const removeSurvey = async () => {
    const ok = await confirm({
      title: "Delete this survey?",
      body: "The questions and every answer given so far are removed. This cannot be undone.",
      confirmLabel: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await surveysApi.remove(eventId);
      setSurvey(null);
      setAnswers(Array(QUESTION_COUNT).fill(null));
      toast.show("Survey deleted");
    } catch (e) {
      toast.show(e?.message || "Could not delete that survey", "error");
    }
  };

  const startEditing = () => {
    setDrafts(survey ? [...survey.questions] : BLANK);
    setEditing(true);
  };

  if (loading) return null;
  if (!survey && !canManage) return null;

  return (
    <section className="mb-6">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
          <ClipboardList className="h-3.5 w-3.5" /> Survey
        </div>
        {canManage && survey && !editing && (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={startEditing}
              className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-bg-secondary"
            >
              <Pencil className="h-3.5 w-3.5" /> Edit questions
            </button>
            <button
              type="button"
              onClick={removeSurvey}
              aria-label="Delete survey"
              className="rounded-card p-1.5 text-text-muted hover:bg-bg-secondary hover:text-red-600"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      <div className="rounded-card border border-border-default bg-white p-5 shadow-card">
        {editing && (
          <QuestionEditor
            drafts={drafts}
            busy={busy}
            existing={Boolean(survey)}
            onChange={(i, v) =>
              setDrafts((prev) =>
                prev.map((q, index) => (index === i ? v.slice(0, MAX_QUESTION) : q))
              )
            }
            onSave={saveQuestions}
            onCancel={() => setEditing(false)}
          />
        )}

        {!editing && !survey && canManage && (
          <div>
            <p className="text-sm text-text-secondary">
              Ask your guests three questions, answered one to five. Short enough
              that people finish it, and the same scale every time so you can
              compare one event against the next.
            </p>
            <button
              type="button"
              onClick={startEditing}
              className="mt-3 rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white"
            >
              Add a survey
            </button>
          </div>
        )}

        {!editing && survey && canManage && <Results results={survey.results} />}

        {!editing && survey && !canManage && (
          <AnswerForm
            questions={survey.questions}
            answers={answers}
            answered={Boolean(survey.my_answers)}
            busy={busy}
            onPick={(qIndex, value) =>
              setAnswers((prev) =>
                prev.map((a, index) => (index === qIndex ? value : a))
              )
            }
            onSubmit={submitAnswers}
          />
        )}
      </div>
    </section>
  );
}

function QuestionEditor({ drafts, busy, existing, onChange, onSave, onCancel }) {
  return (
    <div>
      {existing && (
        <p className="mb-3 rounded-card bg-bg-secondary p-3 text-xs text-text-secondary">
          Changing the wording of a question clears the answers given so far.
          Answers are recorded against the question in each position, so keeping
          them would report replies to a question nobody was asked.
        </p>
      )}
      {drafts.map((q, i) => (
        <div key={i} className={i > 0 ? "mt-3" : ""}>
          <label
            htmlFor={`survey-q-${i}`}
            className="block text-sm font-semibold text-text-secondary"
          >
            Question {i + 1}
          </label>
          <input
            id={`survey-q-${i}`}
            value={q}
            onChange={(e) => onChange(i, e.target.value)}
            placeholder={
              ["How was the venue?", "How useful were the introductions?", "Would you come again?"][i]
            }
            className="mt-1 w-full rounded-card border border-border-default px-3 py-2 text-sm"
          />
        </div>
      ))}
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="inline-flex items-center gap-1 rounded-card px-3 py-1.5 text-sm font-semibold text-text-muted hover:bg-bg-secondary"
        >
          <X className="h-3.5 w-3.5" /> Cancel
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={busy}
          className="rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white disabled:opacity-50"
        >
          {busy ? "Saving..." : "Save survey"}
        </button>
      </div>
    </div>
  );
}

function AnswerForm({ questions, answers, answered, busy, onPick, onSubmit }) {
  return (
    <div>
      {answered && (
        <p className="mb-3 text-sm text-text-secondary">
          Thanks, your answers are saved. Change them any time.
        </p>
      )}
      {questions.map((q, i) => (
        <fieldset key={i} className={i > 0 ? "mt-4" : ""}>
          <legend className="text-sm font-semibold text-text-primary">{q}</legend>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {SCALE.map((n) => {
              const selected = answers[i] === n;
              return (
                <label
                  key={n}
                  className={`cursor-pointer rounded-pill border px-3.5 py-1.5 text-sm font-semibold ${
                    selected
                      ? "border-primary bg-primary text-white"
                      : "border-border-default text-text-secondary hover:bg-bg-secondary"
                  }`}
                >
                  <input
                    type="radio"
                    name={`survey-answer-${i}`}
                    value={n}
                    checked={selected}
                    onChange={() => onPick(i, n)}
                    className="sr-only"
                  />
                  {n}
                </label>
              );
            })}
            <span className="ml-1 text-xs text-text-muted">1 low, 5 high</span>
          </div>
        </fieldset>
      ))}
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="text-xs text-text-muted">
          Your host sees the totals for everyone, not who said what.
        </span>
        <button
          type="button"
          onClick={onSubmit}
          disabled={busy}
          className="rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white disabled:opacity-50"
        >
          {busy ? "Saving..." : answered ? "Update answers" : "Submit"}
        </button>
      </div>
    </div>
  );
}

function Results({ results }) {
  const count = results?.response_count ?? 0;
  const questions = results?.per_question || [];

  return (
    <div>
      <p className="text-sm font-semibold text-text-primary">
        {count} response{count === 1 ? "" : "s"}
      </p>
      {count === 0 && (
        <p className="mt-1 text-sm text-text-muted">
          Nobody has answered yet. Guests see the survey on this page.
        </p>
      )}

      {questions.map((q, i) => (
        <div key={i} className="mt-4">
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-sm font-semibold text-text-primary">{q.question}</p>
            <span className="shrink-0 text-sm font-bold text-primary">
              {/* Null average means nobody answered. Rendering 0 here would
                  read as "everyone gave it the lowest score". */}
              {q.average == null ? "no answers" : q.average.toFixed(2)}
            </span>
          </div>
          <div className="mt-1.5 space-y-1">
            {SCALE.map((n) => {
              const value = q.distribution?.[String(n)] || 0;
              const pct = q.count ? Math.round((value / q.count) * 100) : 0;
              return (
                <div key={n} className="flex items-center gap-2">
                  <span className="w-3 shrink-0 text-xs text-text-muted">{n}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-pill bg-bg-secondary">
                    <div
                      className="h-full rounded-pill bg-primary"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right text-xs text-text-muted">
                    {value}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
