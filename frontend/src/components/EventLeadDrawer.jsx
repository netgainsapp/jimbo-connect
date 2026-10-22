import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Archive, ArchiveRestore, Check, Copy, ExternalLink, RotateCw } from "lucide-react";
import Modal from "./Modal.jsx";
import { eventLeadsApi } from "../lib/api.js";
import { copyToClipboard, formatDateTime } from "../lib/utils.js";
import {
  LINKEDIN_NOTE_MAX,
  approveDisabled,
  approveLabel,
  categoryLabel,
  daysUntilLabel,
  drawerSections,
  eventDateLabel,
  funnelSteps,
  leadDays,
  needsRetry,
  parseScoreInput,
  scoreLabel,
  statusBadge,
} from "../lib/eventLeads.js";
import { useToast } from "../hooks/useToast.jsx";

const TONE_CLASSES = {
  neutral: "bg-bg-secondary text-text-secondary",
  success: "bg-green-100 text-green-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  info: "bg-blue-100 text-blue-700",
  muted: "bg-bg-secondary text-text-muted",
};

export function StatusBadge({ lead }) {
  const { label, tone } = statusBadge(lead);
  return (
    <span
      className={`text-[10px] uppercase font-bold tracking-wide px-2 py-0.5 rounded-full whitespace-nowrap ${
        TONE_CLASSES[tone] || TONE_CLASSES.neutral
      }`}
    >
      {label}
    </span>
  );
}

function contactForm(lead) {
  const c = lead?.contact || {};
  return { name: c.name || "", email: c.email || "", linkedin_url: c.linkedin_url || "" };
}

function Section({ title, children }) {
  return (
    <section className="px-6 py-4 border-t border-border-default">
      <h3 className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
        {title}
      </h3>
      {children}
    </section>
  );
}

/**
 * The lead drawer: loads the full lead (with the email and LinkedIn previews)
 * and edits it. `onApprove(lead)` runs the page's confirm and approve flow and
 * resolves true when it ran; `onChanged()` reloads the page's list.
 */
export default function EventLeadDrawer({ leadId, approving, onClose, onApprove, onChanged }) {
  const [lead, setLead] = useState(null);
  const [contact, setContact] = useState(contactForm(null));
  const [scoreText, setScoreText] = useState("");
  const [busy, setBusy] = useState("");
  const toast = useToast();

  const refresh = useCallback(async () => {
    const detail = await eventLeadsApi.get(leadId);
    setLead(detail);
    setContact(contactForm(detail));
    setScoreText(Number.isInteger(detail.score_override) ? String(detail.score_override) : "");
    return detail;
  }, [leadId]);

  useEffect(() => {
    setLead(null);
    refresh().catch((e) => toast.show(e.message, "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh]);

  const reloadBoth = () => Promise.all([refresh(), onChanged()]);

  // One action at a time; every write ends with a fresh read of the lead and
  // the list, since a contact edit can change the status and the previews.
  // Buttons stay enabled while busy (a disabled button drops keyboard focus
  // out of the dialog); the guard here is what stops a second write.
  const act = async (key, fn, success) => {
    if (busy || approving) return;
    setBusy(key);
    try {
      await fn();
      await reloadBoth();
      toast.show(success);
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setBusy("");
    }
  };

  const saveContact = () =>
    act("contact", () => eventLeadsApi.saveContact(lead.id, contact), "Contact saved");

  const saveScore = () => {
    const parsed = parseScoreInput(scoreText);
    if (!parsed.ok) {
      toast.show(parsed.error, "error");
      return;
    }
    act("score", () => eventLeadsApi.overrideScore(lead.id, parsed.value), "Score override saved");
  };

  const toggleArchive = () =>
    lead.status === "archived"
      ? act("archive", () => eventLeadsApi.unarchive(lead.id), "Lead restored")
      : act("archive", () => eventLeadsApi.archive(lead.id), "Lead archived");

  // The page owns the confirm, the call and its toast, and resolves true
  // only when the call ran.
  const approve = async () => {
    if (busy || approving) return;
    if (await onApprove(lead)) await reloadBoth().catch((e) => toast.show(e.message, "error"));
  };

  const copyClaim = () =>
    copyToClipboard(lead.claim_url)
      .then(() => toast.show("Claim link copied"))
      .catch(() => toast.show("Could not copy the link", "error"));

  const title = lead?.anchor?.title || lead?.organizer_name || "Lead";

  return (
    <Modal open onClose={onClose} maxWidth="max-w-3xl" label={`Lead: ${title}`}>
      {!lead ? (
        <div className="p-6 text-text-muted">Loading…</div>
      ) : (
        <>
          <Header lead={lead} title={title} />
          <Actions
            lead={lead}
            approving={approving}
            onApprove={approve}
            onArchive={toggleArchive}
            onCopyClaim={copyClaim}
          />
          {drawerSections(lead).map((key) => (
            <DrawerSection
              key={key}
              name={key}
              lead={lead}
              contact={contact}
              setContact={setContact}
              onSaveContact={saveContact}
              scoreText={scoreText}
              setScoreText={setScoreText}
              onSaveScore={saveScore}
              busy={busy}
            />
          ))}
        </>
      )}
    </Modal>
  );
}

function Header({ lead, title }) {
  const days = daysUntilLabel(leadDays(lead));
  return (
    <div className="p-6 pr-12">
      <div className="flex flex-wrap items-center gap-2 mb-1">
        <StatusBadge lead={lead} />
        <span className="text-xs text-text-muted">{scoreLabel(lead)}</span>
        <span className="text-xs text-text-muted">{categoryLabel(lead)}</span>
      </div>
      <h2 className="text-xl font-bold text-text-primary">{title}</h2>
      <p className="text-sm text-text-secondary">
        {eventDateLabel(lead)}
        {days && `, ${days}`}
        {lead.organizer_name && ` · ${lead.organizer_name}`}
      </p>
      {lead.status === "existing_customer" && (
        <p className="text-sm text-text-secondary mt-2">
          This organizer already uses Intro Connect (user {lead.existing_user_id}).{" "}
          <Link to="/admin/users" className="text-primary font-semibold">
            Open users
          </Link>
        </p>
      )}
      {lead.auto_approve_error && (
        <p className="text-sm text-red-600 mt-2">Auto approve failed: {lead.auto_approve_error}</p>
      )}
      {lead.signal_scout?.error && (
        <p className="text-sm text-red-600 mt-2">Outreach failed: {lead.signal_scout.error}</p>
      )}
    </div>
  );
}

function Actions({ lead, approving, onApprove, onArchive, onCopyClaim }) {
  const archived = lead.status === "archived";
  return (
    <div className="px-6 pb-4 flex flex-wrap items-center gap-2">
      {needsRetry(lead) ? (
        <button onClick={onApprove} className="btn-primary">
          <RotateCw className="w-4 h-4" /> {approving ? "Retrying…" : "Retry outreach"}
        </button>
      ) : (
        <button
          onClick={onApprove}
          className="btn-primary"
          disabled={approveDisabled(lead)}
        >
          <Check className="w-4 h-4" /> {approving ? "Approving…" : approveLabel(lead)}
        </button>
      )}
      <button onClick={onArchive} className="btn-ghost">
        {archived ? <ArchiveRestore className="w-4 h-4" /> : <Archive className="w-4 h-4" />}
        {archived ? "Unarchive" : "Archive"}
      </button>
      {lead.event_id && (
        <Link to={`/admin/events/${lead.event_id}`} className="btn-ghost">
          <ExternalLink className="w-4 h-4" /> Open event
        </Link>
      )}
      {lead.claim_url && (
        <div className="w-full flex items-center gap-2 mt-2">
          <label htmlFor="lead-claim-url" className="sr-only">
            Claim link
          </label>
          <input id="lead-claim-url" className="input font-mono text-xs" readOnly value={lead.claim_url} />
          <button onClick={onCopyClaim} className="btn-outline shrink-0">
            <Copy className="w-4 h-4" /> Copy
          </button>
        </div>
      )}
    </div>
  );
}

function DrawerSection({ name, lead, ...props }) {
  switch (name) {
    case "reason":
      return (
        <Section title="Why it scored">
          <p className="text-sm text-text-primary whitespace-pre-line">{lead.score.reason}</p>
        </Section>
      );
    case "description":
      return <DescriptionSection anchor={lead.anchor} />;
    case "contact":
      return <ContactSection {...props} />;
    case "score":
      return <ScoreSection lead={lead} {...props} />;
    case "email_preview":
      return <EmailPreview preview={lead.email_preview} />;
    case "linkedin_preview":
      return <LinkedinPreview preview={lead.linkedin_preview} />;
    case "funnel":
      return <FunnelSection lead={lead} />;
    default:
      return null;
  }
}

function DescriptionSection({ anchor }) {
  return (
    <Section title="Event">
      {anchor.venue && (
        <p className="text-sm text-text-secondary mb-1">
          {[anchor.venue, anchor.city].filter(Boolean).join(", ")}
        </p>
      )}
      {anchor.description && (
        <p className="text-sm text-text-primary whitespace-pre-line">{anchor.description}</p>
      )}
      {anchor.source_url && (
        <a
          href={anchor.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-sm text-primary font-semibold mt-2"
        >
          <ExternalLink className="w-3.5 h-3.5" /> Source listing
        </a>
      )}
    </Section>
  );
}

function ContactSection({ contact, setContact, onSaveContact, busy }) {
  const field = (key, label, type = "text") => (
    <div>
      <label htmlFor={`lead-contact-${key}`} className="label">
        {label}
      </label>
      <input
        id={`lead-contact-${key}`}
        type={type}
        className="input"
        value={contact[key]}
        onChange={(e) => setContact({ ...contact, [key]: e.target.value })}
      />
    </div>
  );
  return (
    <Section title="Contact">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {field("name", "Name")}
        {field("email", "Email", "email")}
        {field("linkedin_url", "LinkedIn URL", "url")}
      </div>
      <button onClick={onSaveContact} className="btn-outline mt-3">
        {busy === "contact" ? "Saving…" : "Save contact"}
      </button>
    </Section>
  );
}

function ScoreSection({ lead, scoreText, setScoreText, onSaveScore, busy }) {
  return (
    <Section title="Score">
      <p className="text-sm text-text-secondary mb-2">
        Claude scored this {lead.score?.score ?? "without a number"}, tier{" "}
        {lead.score?.tier ?? "unknown"}. An override sits beside that score and never replaces it.
      </p>
      <div className="flex items-end gap-2">
        <div className="w-32">
          <label htmlFor="lead-score-override" className="label">
            Override
          </label>
          <input
            id="lead-score-override"
            type="number"
            min="0"
            max="100"
            step="1"
            className="input"
            value={scoreText}
            onChange={(e) => setScoreText(e.target.value)}
          />
        </div>
        <button onClick={onSaveScore} className="btn-outline">
          {busy === "score" ? "Saving…" : "Save score"}
        </button>
      </div>
    </Section>
  );
}

function EmailPreview({ preview }) {
  return (
    <Section title="Email preview">
      <p className="text-sm font-semibold text-text-primary mb-2">{preview.subject}</p>
      <pre className="text-xs text-text-primary bg-bg-secondary rounded-card p-3 whitespace-pre-wrap font-sans">
        {preview.body}
      </pre>
    </Section>
  );
}

function LinkedinPreview({ preview }) {
  const note = preview.note || "";
  return (
    <Section title="LinkedIn preview">
      <div className="text-xs text-text-muted mb-1">
        Connection note, {note.length} of {LINKEDIN_NOTE_MAX} characters
      </div>
      <pre className="text-xs text-text-primary bg-bg-secondary rounded-card p-3 whitespace-pre-wrap font-sans mb-3">
        {note}
      </pre>
      <div className="text-xs text-text-muted mb-1">Follow up after they connect</div>
      <pre className="text-xs text-text-primary bg-bg-secondary rounded-card p-3 whitespace-pre-wrap font-sans">
        {preview.followup}
      </pre>
    </Section>
  );
}

function FunnelSection({ lead }) {
  const linkedin = lead.linkedin || {};
  return (
    <Section title="Funnel">
      <ol className="space-y-1">
        {funnelSteps(lead).map((step) => (
          <li key={step.key} className="flex items-center justify-between text-sm">
            <span className={step.at ? "text-text-primary font-semibold" : "text-text-muted"}>
              {step.label}
            </span>
            <span className="text-xs text-text-muted">
              {step.at ? formatDateTime(step.at) : "Not yet"}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-xs text-text-muted mt-3">
        LinkedIn: {linkedin.status || "none"}
        {linkedin.updated_at && `, updated ${formatDateTime(linkedin.updated_at)}`}
      </p>
    </Section>
  );
}
