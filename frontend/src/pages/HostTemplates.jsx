import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Mail, Copy, RotateCcw, Pencil, X, BadgeCheck } from "lucide-react";

import { eventsApi, hostTemplatesApi } from "../lib/api.js";
import { mergeVars } from "../lib/mergeVars.js";
import { buildAnnouncementMailto } from "../lib/announcementMail.js";
import { formatDate } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";
import { useAuth } from "../hooks/useAuth.jsx";

/**
 * A host's own email templates.
 *
 * The same shape as the admin templates screen, narrowed to one person: the
 * six templates that go out in a host's name, editable per host, with the
 * platform defaults underneath. Password reset and the sales templates are
 * not here and not editable; that is enforced server side, this page just
 * does not show them.
 *
 * Sending follows the announcement pattern: the invitation is sent by the
 * platform automatically when guests are imported, and everything else opens
 * in the host's OWN mail client with their guests in BCC. Intro Connect does
 * not bulk-send on the transactional domain; see lib/announcementMail.js.
 */
const VARIABLES = [
  "{attendee_name}",
  "{event_name}",
  "{event_date}",
  "{event_location}",
  "{host_name}",
  "{site_url}",
];

export default function HostTemplates() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [attendeeEmails, setAttendeeEmails] = useState([]);
  const toast = useToast();
  const confirm = useConfirm();

  const load = useCallback(async () => {
    try {
      const [tpl, hosted] = await Promise.all([
        hostTemplatesApi.list(),
        eventsApi.myHostedEvents().catch(() => []),
      ]);
      setTemplates(tpl.templates || []);
      setEvents(hosted);
      if (hosted.length && !eventId) setEventId(hosted[0].id);
    } catch (e) {
      toast.show(e?.message || "Could not load your templates", "error");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectedEvent = useMemo(
    () => events.find((e) => e.id === eventId) || null,
    [events, eventId]
  );

  // Guest addresses for the BCC path. Host only data: the API includes email
  // on the attendee list precisely and only for whoever manages the event.
  useEffect(() => {
    let cancelled = false;
    if (!selectedEvent) {
      setAttendeeEmails([]);
      return undefined;
    }
    eventsApi
      .attendees(selectedEvent.id)
      .then((list) => {
        if (!cancelled)
          setAttendeeEmails(list.map((a) => a.email).filter(Boolean));
      })
      .catch(() => setAttendeeEmails([]));
    return () => {
      cancelled = true;
    };
  }, [selectedEvent]);

  const ctx = useMemo(() => {
    const base = {
      host_name: user?.profile?.name || "Your host",
      site_url: window.location.origin,
      attendee_name: "there",
    };
    if (selectedEvent) {
      base.event_name = selectedEvent.name;
      base.event_date = formatDate(selectedEvent.date);
      base.event_location = selectedEvent.location || "";
    }
    return base;
  }, [user, selectedEvent]);

  const startEditing = (t) => {
    setEditingId(t.id);
    setDraftSubject(t.subject);
    setDraftBody(t.body);
  };

  const save = async () => {
    if (!draftSubject.trim() || !draftBody.trim()) {
      toast.show("A template needs both a subject and a body.", "error");
      return;
    }
    setBusy(true);
    try {
      const updated = await hostTemplatesApi.update(editingId, {
        subject: draftSubject,
        body: draftBody,
      });
      setTemplates((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
      setEditingId(null);
      toast.show("Template saved");
    } catch (e) {
      toast.show(e?.message || "Could not save that template", "error");
    } finally {
      setBusy(false);
    }
  };

  const resetToDefault = async (t) => {
    const ok = await confirm({
      title: "Reset to the default wording?",
      body: "Your version of this template is deleted and future sends use the standard wording again.",
      confirmLabel: "Reset",
      destructive: true,
    });
    if (!ok) return;
    try {
      const restored = await hostTemplatesApi.reset(t.id);
      setTemplates((prev) => prev.map((x) => (x.id === restored.id ? restored : x)));
      if (editingId === t.id) setEditingId(null);
      toast.show("Back to the default");
    } catch (e) {
      toast.show(e?.message || "Could not reset that template", "error");
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 text-text-muted sm:px-6 sm:py-10">
        Loading...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-10">
      <Link
        to="/events"
        className="inline-flex items-center gap-1 text-xs font-semibold text-text-secondary hover:text-primary"
      >
        <ArrowLeft className="h-3 w-3" /> My events
      </Link>
      <h1 className="mt-2 flex items-center gap-2 text-2xl font-bold text-text-primary">
        <Mail className="h-6 w-6" /> Email templates
      </h1>
      <p className="mt-1 text-sm text-text-secondary">
        The emails that go out in your name, in your words. Guests who are
        imported get your invitation automatically; the rest open in your own
        mail app with your guests in BCC.
      </p>

      {events.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-text-muted">Preview and send for</span>
          <select
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            aria-label="Choose an event for previews and sending"
            className="rounded-card border border-border-default px-3 py-1.5 text-sm"
          >
            {events.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </div>
      )}
      {events.length === 0 && (
        <p className="mt-4 rounded-card border border-border-default bg-bg-secondary p-3 text-sm text-text-secondary">
          You are not hosting an event yet, so previews use placeholder details.
          Your edits still save and will apply to your first event.
        </p>
      )}

      <div className="mt-6 space-y-5">
        {templates.map((t) => (
          <section
            key={t.id}
            className="rounded-card border border-border-default bg-white p-5 shadow-card"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="flex items-center gap-2 text-base font-bold text-text-primary">
                  {t.title}
                  {t.customized && (
                    <span className="inline-flex items-center gap-1 rounded-pill bg-primary/10 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-primary">
                      <BadgeCheck className="h-3 w-3" /> Customized
                    </span>
                  )}
                </h2>
                <p className="mt-0.5 text-xs text-text-muted">{t.blurb}</p>
              </div>
              <div className="flex shrink-0 gap-1.5">
                {editingId !== t.id && (
                  <button
                    type="button"
                    onClick={() => startEditing(t)}
                    className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-bg-secondary"
                  >
                    <Pencil className="h-3.5 w-3.5" /> Edit
                  </button>
                )}
                {t.customized && (
                  <button
                    type="button"
                    onClick={() => resetToDefault(t)}
                    className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-muted hover:bg-bg-secondary hover:text-red-600"
                  >
                    <RotateCcw className="h-3.5 w-3.5" /> Reset to default
                  </button>
                )}
              </div>
            </div>

            {editingId === t.id ? (
              <div className="mt-4">
                <label
                  htmlFor={`tpl-subject-${t.id}`}
                  className="block text-sm font-semibold text-text-secondary"
                >
                  Subject
                </label>
                <input
                  id={`tpl-subject-${t.id}`}
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value.slice(0, 300))}
                  className="mt-1 w-full rounded-card border border-border-default px-3 py-2 text-sm"
                />
                <label
                  htmlFor={`tpl-body-${t.id}`}
                  className="mt-3 block text-sm font-semibold text-text-secondary"
                >
                  Body
                </label>
                <textarea
                  id={`tpl-body-${t.id}`}
                  value={draftBody}
                  onChange={(e) => setDraftBody(e.target.value.slice(0, 20000))}
                  rows={9}
                  className="mt-1 w-full rounded-card border border-border-default p-3 font-mono text-sm"
                />
                <p className="mt-2 text-xs text-text-muted">
                  Placeholders fill in per guest and per event:{" "}
                  {VARIABLES.join("  ")}
                </p>
                <div className="mt-3 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="inline-flex items-center gap-1 rounded-card px-3 py-1.5 text-sm font-semibold text-text-muted hover:bg-bg-secondary"
                  >
                    <X className="h-3.5 w-3.5" /> Cancel
                  </button>
                  <button
                    type="button"
                    onClick={save}
                    disabled={busy}
                    className="rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white disabled:opacity-50"
                  >
                    {busy ? "Saving..." : "Save template"}
                  </button>
                </div>
              </div>
            ) : (
              <TemplatePreview template={t} ctx={ctx} />
            )}

            {editingId !== t.id && (
              <SendRow
                template={t}
                ctx={ctx}
                selectedEvent={selectedEvent}
                attendeeEmails={attendeeEmails}
                toast={toast}
              />
            )}
          </section>
        ))}
      </div>
    </div>
  );
}

function TemplatePreview({ template, ctx }) {
  return (
    <div className="mt-4 rounded-card border border-border-default bg-bg-secondary p-4">
      <p className="text-sm font-semibold text-text-primary">
        {mergeVars(template.subject, ctx)}
      </p>
      <p className="mt-2 whitespace-pre-line text-sm text-text-secondary">
        {mergeVars(template.body, ctx)}
      </p>
    </div>
  );
}

/**
 * The send affordance, template by template.
 *
 * The invitation is special: the platform already sends it automatically when
 * guests are imported, so offering a manual blast would double-send it. Every
 * other template opens in the host's own mail client, guests in BCC, with the
 * same too-long fallback as announcements: past the mailto ceiling the link is
 * withheld and the addresses are offered to copy, never silently truncated.
 */
function SendRow({ template, ctx, selectedEvent, attendeeEmails, toast }) {
  if (template.id === "invitation") {
    return (
      <p className="mt-3 border-t border-border-default pt-3 text-xs text-text-muted">
        Sent automatically, with each guest's own sign in details, when you
        import your guest list.
      </p>
    );
  }
  if (!selectedEvent || attendeeEmails.length === 0) return null;

  const { href, bcc, recipientCount, tooLong } = buildAnnouncementMailto({
    subject: mergeVars(template.subject, ctx),
    body: mergeVars(template.body, ctx),
    emails: attendeeEmails,
  });

  const copyAddresses = async () => {
    try {
      await navigator.clipboard.writeText(bcc);
      toast.show(`${recipientCount} addresses copied`);
    } catch {
      toast.show("Could not copy. Select and copy the list by hand.", "error");
    }
  };

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border-default pt-3">
      {href ? (
        <a
          href={href}
          className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-bg-secondary"
        >
          <Mail className="h-3.5 w-3.5" />
          Send for {selectedEvent.name} ({recipientCount})
        </a>
      ) : (
        <button
          type="button"
          onClick={copyAddresses}
          className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-bg-secondary"
        >
          <Copy className="h-3.5 w-3.5" />
          Copy {recipientCount} addresses for BCC
        </button>
      )}
      <span className="text-xs text-text-muted">
        {tooLong
          ? "Too many guests for a mail link. Copy the addresses into your BCC field."
          : "Opens in your own mail app, with your guests in BCC."}
      </span>
    </div>
  );
}
