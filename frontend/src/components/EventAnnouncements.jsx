import { useCallback, useEffect, useRef, useState } from "react";
import { Megaphone, Mail, Copy, Trash2, Plus, X } from "lucide-react";

import { announcementsApi } from "../lib/api.js";
import { buildAnnouncementMailto } from "../lib/announcementMail.js";
import { formatDateTime } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";

// Mirrors backend/announcements.py. Kept as plain constants rather than fetched
// so the counter can react as the host types.
const MAX_TITLE = 200;
const MAX_BODY = 5000;

/**
 * Host announcements on the event page.
 *
 * Shown to everyone who can see the event; only the host can post or delete,
 * which the server enforces regardless of what this renders.
 *
 * Announcements are in-app by decision, and the email half is deliberately
 * "open this in your own mail client" rather than a platform send. See
 * lib/announcementMail.js for why, and for why a guest list too large for a
 * mailto: link offers the addresses to copy instead of quietly emailing the
 * first N of them.
 */
export default function EventAnnouncements({
  eventId,
  eventName = "",
  canManage = false,
  attendeeEmails = [],
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composing, setComposing] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [posting, setPosting] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  // Read state is marked once per mount. The section sits at the top of the
  // event page, so loading the page is seeing it, and the unread flags captured
  // in `items` stay on screen for this visit even after the server is told.
  const markedRef = useRef(false);

  const load = useCallback(async () => {
    try {
      const list = await announcementsApi.list(eventId);
      setItems(list);
      if (!markedRef.current && list.some((a) => a.unread)) {
        markedRef.current = true;
        // Deliberately not awaited into the render path: failing to record the
        // read is a stale badge next visit, not something worth blocking on.
        announcementsApi.markRead(eventId).catch(() => {});
      }
    } catch {
      // An event with no announcements is the normal case, and a failure here
      // must not take the rest of the event page down with it.
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    load();
  }, [load]);

  const post = async () => {
    if (!body.trim()) return;
    setPosting(true);
    try {
      const created = await announcementsApi.create(eventId, { title, body });
      setItems((prev) => [created, ...prev]);
      setTitle("");
      setBody("");
      setComposing(false);
      toast.show("Announcement posted");
    } catch (e) {
      toast.show(e?.message || "Could not post that announcement", "error");
    } finally {
      setPosting(false);
    }
  };

  const remove = async (announcement) => {
    const ok = await confirm({
      title: "Delete this announcement?",
      body: "Everyone on the event page stops seeing it. This cannot be undone.",
      confirmLabel: "Delete",
      destructive: true,
    });
    if (!ok) return;
    try {
      await announcementsApi.remove(eventId, announcement.id);
      setItems((prev) => prev.filter((a) => a.id !== announcement.id));
      toast.show("Announcement deleted");
    } catch (e) {
      toast.show(e?.message || "Could not delete that announcement", "error");
    }
  };

  if (loading) return null;
  // Nothing to show and nothing to do: stay out of the attendee's way entirely.
  if (!items.length && !canManage) return null;

  return (
    <section className="mb-6">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
          <Megaphone className="h-3.5 w-3.5" /> Announcements
        </div>
        {canManage && !composing && (
          <button
            type="button"
            onClick={() => setComposing(true)}
            className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-2.5 py-1 text-xs font-semibold text-text-primary hover:bg-bg-secondary"
          >
            <Plus className="h-3.5 w-3.5" /> Post an announcement
          </button>
        )}
      </div>

      <div className="rounded-card border border-border-default bg-white p-5 shadow-card">
        {composing && (
          <Composer
            title={title}
            body={body}
            posting={posting}
            onTitle={setTitle}
            onBody={setBody}
            onPost={post}
            onCancel={() => {
              setComposing(false);
              setTitle("");
              setBody("");
            }}
          />
        )}

        {!items.length && !composing && (
          <p className="text-sm text-text-muted">
            Nothing posted yet. Use an announcement for a schedule change, a room
            move, or anything the whole room needs to know.
          </p>
        )}

        {items.map((a, index) => (
          <article
            key={a.id}
            className={
              index > 0 || composing
                ? "mt-4 border-t border-border-default pt-4"
                : ""
            }
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                {a.title && (
                  <h3 className="flex items-center gap-2 text-sm font-bold text-text-primary">
                    <span className="truncate">{a.title}</span>
                    {a.unread && <NewBadge />}
                  </h3>
                )}
                {!a.title && a.unread && <NewBadge />}
              </div>
              {canManage && (
                <button
                  type="button"
                  onClick={() => remove(a)}
                  aria-label={`Delete announcement${a.title ? `: ${a.title}` : ""}`}
                  className="shrink-0 rounded-card p-1.5 text-text-muted hover:bg-bg-secondary hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>

            <p className="mt-1 whitespace-pre-line text-sm text-text-secondary">
              {a.body}
            </p>
            <p className="mt-1.5 text-xs text-text-muted">
              {a.author_name}
              {a.created_at ? ` · ${formatDateTime(a.created_at)}` : ""}
            </p>

            {canManage && (
              <EmailItAlso
                announcement={a}
                eventName={eventName}
                attendeeEmails={attendeeEmails}
                toast={toast}
              />
            )}
          </article>
        ))}
      </div>
    </section>
  );
}

function NewBadge() {
  return (
    <span className="inline-flex shrink-0 items-center rounded-pill bg-primary/10 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-primary">
      New
    </span>
  );
}

function Composer({ title, body, posting, onTitle, onBody, onPost, onCancel }) {
  return (
    <div className="mb-1">
      <input
        value={title}
        onChange={(e) => onTitle(e.target.value.slice(0, MAX_TITLE))}
        placeholder="Title (optional)"
        className="w-full rounded-card border border-border-default px-3 py-2 text-sm"
      />
      <textarea
        value={body}
        onChange={(e) => onBody(e.target.value.slice(0, MAX_BODY))}
        rows={4}
        placeholder="What does everyone need to know?"
        className="mt-2 w-full rounded-card border border-border-default p-3 text-sm"
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <span className="text-xs text-text-muted">
          {body.length}/{MAX_BODY}
        </span>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center gap-1 rounded-card px-3 py-1.5 text-sm font-semibold text-text-muted hover:bg-bg-secondary"
          >
            <X className="h-3.5 w-3.5" /> Cancel
          </button>
          <button
            type="button"
            onClick={onPost}
            disabled={posting || !body.trim()}
            className="rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white disabled:opacity-50"
          >
            {posting ? "Posting..." : "Post"}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * The "send it by email as well" half, host only.
 *
 * Intro Connect does not send this. The host's own mail client does, with the
 * guest list in BCC. When the list is too long for a mailto: URL the link is
 * withheld rather than shortened, and the addresses are offered for the host to
 * paste into their client's own BCC field, which has no such limit.
 */
function EmailItAlso({ announcement, eventName, attendeeEmails, toast }) {
  const subject = announcement.title || eventName || "An update about the event";
  const bodyText = `${announcement.body}\n\n${window.location.origin}/events/${announcement.event_id}`;
  const { href, bcc, recipientCount, tooLong } = buildAnnouncementMailto({
    subject,
    body: bodyText,
    emails: attendeeEmails,
  });

  if (!recipientCount) return null;

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
          Also send by email ({recipientCount})
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
          ? "Too many guests for a mail link. Copy the addresses and paste them into your BCC field."
          : "Opens in your own mail app, with guests in BCC."}
      </span>
    </div>
  );
}
