import { useEffect, useMemo, useState } from "react";
import {
  Copy,
  Mail,
  Send,
  Edit2,
  RotateCcw,
  Save,
  X,
  Cog,
} from "lucide-react";
import { eventsApi, templatesApi } from "../lib/api.js";
// templatesApi.reseedAll used below when the list is empty
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { copyToClipboard, formatDate } from "../lib/utils.js";

function mergeVars(text, ctx) {
  if (!text) return "";
  return text.replace(/\{(\w+)\}/g, (m, key) =>
    ctx[key] !== undefined && ctx[key] !== null ? String(ctx[key]) : m
  );
}

export default function AdminTemplates() {
  const { user } = useAuth();
  const toast = useToast();
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [templates, setTemplates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [activeTemplateId, setActiveTemplateId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([templatesApi.list(), eventsApi.list().catch(() => [])])
      .then(([t, ev]) => {
        setTemplates(t.templates || []);
        setCategories(t.categories || []);
        setEvents(ev);
        if (t.templates?.length) setActiveTemplateId(t.templates[0].id);
      })
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedEvent = useMemo(
    () => events.find((e) => e.id === eventId) || null,
    [events, eventId]
  );

  const ctx = useMemo(() => {
    const base = {
      host_name: user?.profile?.name || "Jim",
      site_url: window.location.origin,
    };
    if (selectedEvent) {
      const d = new Date(selectedEvent.date);
      base.event_name = selectedEvent.name;
      base.event_date = formatDate(selectedEvent.date);
      base.event_time = isNaN(d.getTime())
        ? ""
        : d.toLocaleTimeString(undefined, {
            hour: "numeric",
            minute: "2-digit",
          });
      base.event_location = selectedEvent.location || "";
      base.join_code = selectedEvent.join_code || "";
    }
    return base;
  }, [user, selectedEvent]);

  const template = templates.find((t) => t.id === activeTemplateId);
  const rendered = template
    ? {
        subject: mergeVars(template.subject, ctx),
        body: mergeVars(template.body, ctx),
      }
    : { subject: "", body: "" };

  const startEdit = () => {
    setDraftSubject(template.subject);
    setDraftBody(template.body);
    setEditing(true);
  };

  const saveEdit = async () => {
    setSaving(true);
    try {
      const updated = await templatesApi.update(activeTemplateId, {
        subject: draftSubject,
        body: draftBody,
      });
      setTemplates((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t))
      );
      setEditing(false);
      toast.show("Template saved");
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const resetEdit = async () => {
    if (!confirm("Reset this template to the default copy?")) return;
    try {
      const updated = await templatesApi.reset(activeTemplateId);
      setTemplates((prev) =>
        prev.map((t) => (t.id === updated.id ? updated : t))
      );
      setEditing(false);
      toast.show("Template reset to default");
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const copyAll = async () => {
    await copyToClipboard(`Subject: ${rendered.subject}\n\n${rendered.body}`);
    toast.show("Template copied to clipboard");
  };

  const copyBody = async () => {
    await copyToClipboard(rendered.body);
    toast.show("Body copied");
  };

  const openMailto = async () => {
    let bcc = "";
    if (selectedEvent) {
      try {
        const list = await eventsApi.attendees(selectedEvent.id);
        bcc = list.map((a) => a.email).join(",");
      } catch {
        // ignore
      }
    }
    const href =
      "mailto:" +
      (bcc
        ? `?bcc=${encodeURIComponent(bcc)}&subject=${encodeURIComponent(
            rendered.subject
          )}&body=${encodeURIComponent(rendered.body)}`
        : `?subject=${encodeURIComponent(
            rendered.subject
          )}&body=${encodeURIComponent(rendered.body)}`);
    window.location.href = href;
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 text-text-muted">Loading…</div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Email templates</h1>
      <p className="text-sm text-text-secondary mb-6">
        Edit any template — including the ones Jimbo sends automatically.
        Changes save to the server and apply to all admins.
      </p>

      <div className="card p-4 mb-6 flex flex-col sm:flex-row gap-3">
        <div className="flex-1">
          <label className="label">Event (for auto-fill)</label>
          <select
            className="input"
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
          >
            <option value="">— none —</option>
            {events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 text-xs text-text-muted self-end pb-1">
          Variables left as <code className="bg-bg-secondary px-1">{`{like_this}`}</code>{" "}
          mean Jimbo fills them in per-recipient (attendee name, password, etc.).
        </div>
      </div>

      {templates.length === 0 && !loading && (
        <div className="card p-6 mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="font-bold text-text-primary">No templates yet</div>
            <div className="text-sm text-text-secondary">
              First-run seed didn't populate. Click to load the defaults.
            </div>
          </div>
          <button
            className="btn-primary"
            onClick={async () => {
              try {
                await templatesApi.reseedAll();
                const t = await templatesApi.list();
                setTemplates(t.templates || []);
                setCategories(t.categories || []);
                if (t.templates?.length) setActiveTemplateId(t.templates[0].id);
                toast.show("Templates loaded");
              } catch (e) {
                toast.show(e.message, "error");
              }
            }}
          >
            Load defaults
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        <div className="flex flex-col gap-4">
          {categories.map((cat) => {
            const items = templates.filter((t) => t.category === cat.id);
            if (items.length === 0) return null;
            return (
              <div key={cat.id}>
                <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
                  {cat.label}
                </div>
                <div className="flex flex-col gap-1">
                  {items.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setActiveTemplateId(t.id);
                        setEditing(false);
                      }}
                      className={`text-left px-3 py-2 rounded-card border transition ${
                        activeTemplateId === t.id
                          ? "border-primary bg-primary/5"
                          : "border-border-default hover:bg-bg-secondary"
                      }`}
                    >
                      <div className="font-bold text-text-primary text-sm flex items-center gap-1">
                        {t.title}
                        {t.system && (
                          <Cog
                            className="w-3 h-3 text-text-muted"
                            title="Sent automatically by Jimbo"
                          />
                        )}
                      </div>
                      <div className="text-xs text-text-secondary line-clamp-2">
                        {t.blurb}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {template && (
          <div className="card p-5 flex flex-col">
            {!editing ? (
              <>
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="min-w-0">
                    <div className="text-xs uppercase tracking-wider text-text-muted font-semibold">
                      {template.system ? "Auto-sent · Subject" : "Subject"}
                    </div>
                    <div className="font-bold text-text-primary truncate">
                      {rendered.subject}
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <button onClick={startEdit} className="btn-ghost">
                      <Edit2 className="w-4 h-4" /> Edit
                    </button>
                    <button onClick={resetEdit} className="btn-ghost">
                      <RotateCcw className="w-4 h-4" /> Reset
                    </button>
                    {!template.system && (
                      <>
                        <button onClick={copyBody} className="btn-ghost">
                          <Copy className="w-4 h-4" /> Body
                        </button>
                        <button onClick={copyAll} className="btn-outline">
                          <Copy className="w-4 h-4" /> Copy all
                        </button>
                        <button onClick={openMailto} className="btn-primary">
                          <Mail className="w-4 h-4" /> Open in mail
                        </button>
                      </>
                    )}
                  </div>
                </div>
                <textarea
                  className="input mt-4 flex-1 min-h-[420px] whitespace-pre-wrap font-sans"
                  value={rendered.body}
                  readOnly
                />
                <p className="text-xs text-text-muted mt-2 inline-flex items-center gap-1">
                  <Send className="w-3 h-3" />
                  {template.system
                    ? "Jimbo sends this automatically when triggered. Edit affects all future sends."
                    : "\"Open in mail\" pre-fills your default email client. If an event is selected, attendees are added as BCC."}
                </p>
              </>
            ) : (
              <>
                <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
                  <div className="text-xs uppercase tracking-wider text-text-muted font-semibold">
                    Editing — variables in {`{curly_braces}`} will be filled in
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditing(false)}
                      className="btn-ghost"
                    >
                      <X className="w-4 h-4" /> Cancel
                    </button>
                    <button
                      onClick={saveEdit}
                      className="btn-primary"
                      disabled={saving}
                    >
                      <Save className="w-4 h-4" />
                      {saving ? "Saving…" : "Save changes"}
                    </button>
                  </div>
                </div>
                <label className="label">Subject line</label>
                <input
                  className="input mb-3"
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                />
                <label className="label">Body</label>
                <textarea
                  className="input flex-1 min-h-[420px] font-sans whitespace-pre-wrap"
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value)}
                />
                <p className="text-xs text-text-muted mt-2">
                  Available variables: {"{host_name}"}, {"{site_url}"},{" "}
                  {"{event_name}"}, {"{event_date}"}, {"{event_time}"},{" "}
                  {"{event_location}"}, {"{join_code}"}, {"{attendee_name}"},{" "}
                  {"{attendee_email}"}, {"{temp_password}"},{" "}
                  {"{sponsor_name}"}, {"{reset_url}"}.
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
