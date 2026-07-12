import { useEffect, useState } from "react";
import { ExternalLink, Plus, Trash2, FileText } from "lucide-react";
import { newsApi, newsPublicUrl } from "../lib/api.js";
import { formatDateTime } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";

const EMPTY_FORM = {
  headline: "",
  summary: "",
  sections: [{ heading: "", body: "" }],
  source_url: "",
  sources: "",
  event_date: "",
  image_url: "",
};

export default function AdminNews() {
  const toast = useToast();
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = () =>
    newsApi
      .list()
      .then(setArticles)
      .catch((e) => toast.show(e.message, "error"));

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const setField = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const setSection = (i, k, v) =>
    setForm((f) => ({
      ...f,
      sections: f.sections.map((s, j) => (j === i ? { ...s, [k]: v } : s)),
    }));
  const addSection = () =>
    setForm((f) => ({ ...f, sections: [...f.sections, { heading: "", body: "" }] }));
  const removeSection = (i) =>
    setForm((f) => ({ ...f, sections: f.sections.filter((_, j) => j !== i) }));

  const submit = async (e) => {
    e.preventDefault();
    const sections = form.sections
      .map((s) => ({ heading: s.heading.trim(), body: s.body.trim() }))
      .filter((s) => s.heading && s.body);
    if (form.headline.trim().length < 8)
      return toast.show("Headline needs at least 8 characters.", "error");
    if (form.summary.trim().length < 8)
      return toast.show("Summary needs at least 8 characters.", "error");
    if (!sections.length)
      return toast.show("Add at least one section with a heading and body.", "error");
    if (!/^https?:\/\//.test(form.source_url.trim()))
      return toast.show("A primary source URL (http/https) is required.", "error");

    const sources = form.sources
      .split(/[\s,]+/)
      .map((u) => u.trim())
      .filter(Boolean);
    if (sources.some((u) => !/^https?:\/\//.test(u)))
      return toast.show("Every extra source must be an http/https URL.", "error");

    setSaving(true);
    try {
      await newsApi.create({
        headline: form.headline.trim(),
        summary: form.summary.trim(),
        sections,
        source_url: form.source_url.trim(),
        sources,
        event_date: form.event_date.trim() || null,
        image_url: form.image_url.trim() || null,
      });
      toast.show("Draft created. Review it below, then publish.");
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const publish = async (id) => {
    try {
      await newsApi.publish(id);
      toast.show("Published");
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };
  const unpublish = async (id) => {
    try {
      await newsApi.unpublish(id);
      toast.show("Moved back to draft");
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const drafts = articles.filter((a) => a.status !== "published");
  const published = articles.filter((a) => a.status === "published");

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">News</h1>
      <p className="text-sm text-text-secondary mb-6">
        Write source-attributed news for the public /news section. Every article
        needs a real primary source. Articles start as drafts and go live only
        when you publish them.
      </p>

      <form onSubmit={submit} className="card p-5 mb-8 flex flex-col gap-4">
        <div className="text-xs uppercase tracking-wider text-text-muted font-semibold">
          New article
        </div>
        <Field label="Headline">
          <input
            className="input"
            value={form.headline}
            onChange={(e) => setField("headline", e.target.value)}
            placeholder="What happened, in plain words"
          />
        </Field>
        <Field label="Summary">
          <textarea
            className="input min-h-[70px]"
            value={form.summary}
            onChange={(e) => setField("summary", e.target.value)}
            placeholder="One or two sentences a reader could quote."
          />
        </Field>

        <div className="flex flex-col gap-3">
          <div className="text-sm font-bold text-text-primary">Sections</div>
          {form.sections.map((s, i) => (
            <div key={i} className="flex flex-col gap-2 border border-border-default rounded-card p-3">
              <div className="flex items-center gap-2">
                <input
                  className="input flex-1"
                  value={s.heading}
                  onChange={(e) => setSection(i, "heading", e.target.value)}
                  placeholder="Section heading"
                />
                {form.sections.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeSection(i)}
                    className="btn-ghost"
                    aria-label="Remove section"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
              <textarea
                className="input min-h-[90px]"
                value={s.body}
                onChange={(e) => setSection(i, "body", e.target.value)}
                placeholder="Paragraphs. Separate them with a blank line."
              />
            </div>
          ))}
          <button type="button" onClick={addSection} className="btn-outline self-start">
            <Plus className="w-4 h-4" /> Add section
          </button>
        </div>

        <Field label="Primary source URL">
          <input
            className="input"
            value={form.source_url}
            onChange={(e) => setField("source_url", e.target.value)}
            placeholder="https://…  (required)"
          />
        </Field>
        <Field label="Additional sources (optional)">
          <textarea
            className="input min-h-[54px]"
            value={form.sources}
            onChange={(e) => setField("sources", e.target.value)}
            placeholder="More https URLs, one per line or comma-separated"
          />
        </Field>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Event date (optional)">
            <input
              className="input"
              value={form.event_date}
              onChange={(e) => setField("event_date", e.target.value)}
              placeholder="e.g. July 10, 2026"
            />
          </Field>
          <Field label="Image URL (optional, https)">
            <input
              className="input"
              value={form.image_url}
              onChange={(e) => setField("image_url", e.target.value)}
              placeholder="https://…"
            />
          </Field>
        </div>

        <button type="submit" className="btn-primary self-start" disabled={saving}>
          <FileText className="w-4 h-4" /> {saving ? "Saving…" : "Save as draft"}
        </button>
      </form>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : (
        <>
          <Section title={`Drafts (${drafts.length})`}>
            {drafts.length === 0 ? (
              <Empty>No drafts. New articles you write appear here for review.</Empty>
            ) : (
              drafts.map((a) => (
                <ArticleRow key={a.id} article={a} onPublish={publish} onUnpublish={unpublish} />
              ))
            )}
          </Section>
          <Section title={`Published (${published.length})`}>
            {published.length === 0 ? (
              <Empty>Nothing published yet.</Empty>
            ) : (
              published.map((a) => (
                <ArticleRow key={a.id} article={a} onPublish={publish} onUnpublish={unpublish} />
              ))
            )}
          </Section>
        </>
      )}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-sm font-bold text-text-primary">{label}</span>
      {children}
    </label>
  );
}

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h2 className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
        {title}
      </h2>
      <div className="flex flex-col gap-3">{children}</div>
    </div>
  );
}

function Empty({ children }) {
  return <div className="card p-5 text-sm text-text-secondary">{children}</div>;
}

function ArticleRow({ article, onPublish, onUnpublish }) {
  const isPublished = article.status === "published";
  return (
    <div className="card p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <StatusBadge status={article.status} />
            <span className="font-bold text-text-primary truncate">
              {article.headline}
            </span>
          </div>
          {article.summary && (
            <div className="text-sm text-text-secondary line-clamp-2 mt-1">
              {article.summary}
            </div>
          )}
          {article.source_url && (
            <a
              href={article.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary break-all mt-1 inline-block"
            >
              Source
            </a>
          )}
        </div>
        <div className="flex gap-2 shrink-0">
          {isPublished ? (
            <>
              <a
                href={newsPublicUrl(article.slug)}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost"
              >
                <ExternalLink className="w-4 h-4" /> View
              </a>
              <button onClick={() => onUnpublish(article.id)} className="btn-ghost">
                Unpublish
              </button>
            </>
          ) : (
            <button onClick={() => onPublish(article.id)} className="btn-primary">
              <FileText className="w-4 h-4" /> Publish
            </button>
          )}
        </div>
      </div>
      <div className="text-xs text-text-muted">
        Created {formatDateTime(article.created_at)}
        {article.published_at && ` · Published ${formatDateTime(article.published_at)}`}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const published = status === "published";
  return (
    <span
      className={`text-[10px] uppercase font-bold tracking-wide px-2 py-0.5 rounded-full shrink-0 ${
        published ? "bg-green-100 text-green-700" : "bg-bg-secondary text-text-secondary"
      }`}
    >
      {published ? "Live" : "Draft"}
    </span>
  );
}
