import { useEffect, useMemo, useState } from "react";
import { Copy, Plus, Trash2, Files, Check } from "lucide-react";
import { salesTemplatesApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";

const CATEGORIES = [
  { value: "cold", label: "Cold outreach" },
  { value: "follow_up", label: "Follow up" },
  { value: "partnership", label: "Partnership" },
  { value: "re_engage", label: "Re-engagement" },
];

const EMPTY = { title: "", category: "cold", subject: "", body: "" };

export default function AdminSalesTemplates() {
  const toast = useToast();
  const confirm = useConfirm();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // {id?} | null
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState("");

  const load = () =>
    salesTemplatesApi.list().then(setItems).catch((e) => toast.show(e.message, "error"));

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grouped = useMemo(() => {
    const g = {};
    for (const c of CATEGORIES) g[c.value] = [];
    for (const t of items) (g[t.category] || (g[t.category] = [])).push(t);
    return g;
  }, [items]);

  const openNew = () => {
    setForm(EMPTY);
    setEditing({});
  };
  const openEdit = (t) => {
    setForm({ title: t.title, category: t.category, subject: t.subject, body: t.body });
    setEditing({ id: t.id });
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.subject.trim() || !form.body.trim())
      return toast.show("Title, subject, and body are all required.", "error");
    setSaving(true);
    try {
      if (editing.id) await salesTemplatesApi.update(editing.id, form);
      else await salesTemplatesApi.create(form);
      toast.show("Saved");
      setEditing(null);
      await load();
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const copy = async (t) => {
    try {
      await navigator.clipboard.writeText(`Subject: ${t.subject}\n\n${t.body}`);
      setCopied(t.id);
      setTimeout(() => setCopied(""), 1500);
    } catch {
      toast.show("Copy failed. Select and copy manually.", "error");
    }
  };

  const duplicate = async (t) => {
    try {
      await salesTemplatesApi.duplicate(t.id);
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const remove = async (t) => {
    const ok = await confirm({
      title: "Delete this template?",
      body: `"${t.title}" will be removed for good.`,
      confirmLabel: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await salesTemplatesApi.remove(t.id);
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <div className="flex items-start justify-between gap-3 flex-wrap mb-1">
        <h1 className="text-2xl font-bold text-text-primary">Sales &amp; outreach templates</h1>
        <button onClick={openNew} className="btn-primary">
          <Plus className="w-4 h-4" /> New template
        </button>
      </div>
      <p className="text-sm text-text-secondary mb-6">
        Reusable copy for reaching out to prospective hosts. Copy a template,
        swap the {"{first_name}"} / {"{company}"} / {"{event_name}"} placeholders,
        and send it from your own inbox.
      </p>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : (
        CATEGORIES.map((c) => (
          <div key={c.value} className="mb-7">
            <h2 className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
              {c.label} ({grouped[c.value]?.length || 0})
            </h2>
            {(grouped[c.value] || []).length === 0 ? (
              <div className="card p-4 text-sm text-text-secondary">Nothing here yet.</div>
            ) : (
              <div className="flex flex-col gap-3">
                {grouped[c.value].map((t) => (
                  <div key={t.id} className="card p-4">
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="min-w-0 flex-1">
                        <div className="font-bold text-text-primary">{t.title}</div>
                        <div className="text-sm text-text-secondary mt-0.5">
                          <span className="font-semibold">Subject:</span> {t.subject}
                        </div>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <button onClick={() => copy(t)} className="btn-ghost" title="Copy subject + body">
                          {copied === t.id ? (
                            <><Check className="w-4 h-4" /> Copied</>
                          ) : (
                            <><Copy className="w-4 h-4" /> Copy</>
                          )}
                        </button>
                        <button onClick={() => openEdit(t)} className="btn-ghost">Edit</button>
                        <button onClick={() => duplicate(t)} className="btn-ghost" title="Duplicate">
                          <Files className="w-4 h-4" />
                        </button>
                        <button onClick={() => remove(t)} className="btn-ghost" title="Delete">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <pre className="mt-2 text-sm text-text-secondary whitespace-pre-wrap font-sans">
                      {t.body}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))
      )}

      {editing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <form onSubmit={save} className="card p-6 w-full max-w-lg bg-bg-primary max-h-[90vh] overflow-auto">
            <h2 className="text-lg font-bold text-text-primary mb-4">
              {editing.id ? "Edit template" : "New template"}
            </h2>
            <label className="flex flex-col gap-1 mb-3">
              <span className="text-sm font-bold text-text-primary">Title</span>
              <input className="input" value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Internal name, for your reference" />
            </label>
            <label className="flex flex-col gap-1 mb-3">
              <span className="text-sm font-bold text-text-primary">Category</span>
              <select className="input" value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </label>
            <label className="flex flex-col gap-1 mb-3">
              <span className="text-sm font-bold text-text-primary">Subject</span>
              <input className="input" value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })} />
            </label>
            <label className="flex flex-col gap-1 mb-4">
              <span className="text-sm font-bold text-text-primary">Body</span>
              <textarea className="input min-h-[180px]" value={form.body}
                onChange={(e) => setForm({ ...form, body: e.target.value })}
                placeholder="Use {first_name}, {company}, {event_name} placeholders." />
            </label>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setEditing(null)} className="btn-ghost">Cancel</button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
