import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Download, Eye, RotateCw, Upload } from "lucide-react";
import { eventLeadsApi } from "../lib/api.js";
import { parseCsvObjects } from "../lib/parseAttendeeCsv.js";
import {
  KPI_METRICS,
  approveDisabled,
  approveLabel,
  approveOutcome,
  categoryLabel,
  contactSummary,
  daysUntilLabel,
  eventDateLabel,
  formatKpi,
  kpiRows,
  leadDays,
  linkedinResultSummary,
  needsRetry,
  parseScoreInput,
  scoreLabel,
  sortLeads,
  visibleLeads,
  weekLabel,
} from "../lib/eventLeads.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";
import EventLeadDrawer, { StatusBadge } from "../components/EventLeadDrawer.jsx";

function eventName(lead) {
  return lead.anchor?.title || lead.organizer_name || "this lead";
}

// The queue is a cross-origin attachment: a top-level navigation carries the
// session cookie and the server's filename, and the page stays where it is.
function startDownload(url) {
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener";
  a.click();
}

export default function AdminEventLeads() {
  const [leads, setLeads] = useState([]);
  const [kpis, setKpis] = useState([]);
  const [minScore, setMinScore] = useState("");
  const [showC, setShowC] = useState(false);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState(null);
  const [approvingId, setApprovingId] = useState(null);
  const loadSeq = useRef(0);
  const toast = useToast();
  const confirm = useConfirm();

  // Resolves the list payload, or null after toasting the error. Only the
  // latest request is applied: toggling Show C quickly fires two requests
  // that can answer out of order.
  const load = (withC = showC) => {
    loadSeq.current += 1;
    const seq = loadSeq.current;
    return eventLeadsApi
      .list(withC)
      .then((res) => {
        if (seq !== loadSeq.current) return null;
        setLeads(res.leads || []);
        setKpis(res.kpis || []);
        return res;
      })
      .catch((e) => {
        if (seq === loadSeq.current) toast.show(e.message, "error");
        return null;
      });
  };

  useEffect(() => {
    // The setting is read once: a later reload must not clobber an unsaved edit.
    load(false)
      .then((res) => {
        const saved = res?.settings?.auto_approve_min_score;
        setMinScore(Number.isInteger(saved) ? String(saved) : "");
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleC = (next) => {
    setShowC(next);
    load(next);
  };

  // Approve, or Retry outreach for an approved lead whose push failed.
  // Resolves true when the call ran, so the caller knows to reload.
  const runApprove = async (lead) => {
    if (approvingId) return false;
    const name = eventName(lead);
    const retry = needsRetry(lead);
    const ok = await confirm(
      retry
        ? {
            title: `Retry outreach for ${name}?`,
            body: "This sends the lead to Signal Scout again.",
            confirmLabel: "Retry outreach",
          }
        : {
            title: `Approve ${name}?`,
            body: "This creates the host account and the event and starts outreach.",
            confirmLabel: "Approve",
          },
    );
    if (!ok) return false;
    setApprovingId(lead.id);
    try {
      const res = retry
        ? await eventLeadsApi.retryOutreach(lead.id)
        : await eventLeadsApi.approve(lead.id);
      const outcome = approveOutcome(res);
      toast.show(outcome.message, outcome.type);
      return true;
    } catch (e) {
      toast.show(e.message, "error");
      return false;
    } finally {
      setApprovingId(null);
    }
  };

  const approveFromRow = async (lead) => {
    if (await runApprove(lead)) await load();
  };

  const closeDrawer = useCallback(() => setOpenId(null), []);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 text-text-muted">
        Loading…
      </div>
    );
  }

  const rows = sortLeads(visibleLeads(leads, { showC }), new Date());

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Event Leads</h1>
      <p className="text-sm text-text-secondary mb-6">
        Hosts found and scored each week. Approve creates the host account and the
        event, then hands the lead to Signal Scout for the email sequence.
      </p>

      <KpiStrip kpis={kpis} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <AutoApproveCard value={minScore} onChange={setMinScore} />
        <LinkedinCard confirm={confirm} onImported={load} />
      </div>

      <div className="flex items-center gap-2 mb-3">
        <input
          id="show-c-tier"
          type="checkbox"
          checked={showC}
          onChange={(e) => toggleC(e.target.checked)}
        />
        <label htmlFor="show-c-tier" className="text-sm text-text-secondary font-semibold">
          Show C tier
        </label>
      </div>

      {rows.length === 0 ? (
        <div className="card p-8 text-center text-sm text-text-secondary">
          No leads yet. The weekly batch lands here once the finder runs.
        </div>
      ) : (
        <LeadsTable
          rows={rows}
          approvingId={approvingId}
          onOpen={(lead) => setOpenId(lead.id)}
          onApprove={approveFromRow}
        />
      )}

      {openId && (
        <EventLeadDrawer
          leadId={openId}
          approving={approvingId === openId}
          onClose={closeDrawer}
          onApprove={runApprove}
          onChanged={() => load()}
        />
      )}
    </div>
  );
}

function KpiStrip({ kpis }) {
  const weeks = kpiRows(kpis);
  return (
    <div className="card mb-6 overflow-x-auto">
      <table className="w-full text-sm">
        <caption className="text-left text-sm font-bold text-text-primary px-4 pt-4 pb-2">
          This week and the four before it
        </caption>
        <thead>
          <tr className="text-xs text-text-muted">
            <th scope="col" className="text-left font-semibold px-4 py-2">
              Measure
            </th>
            {weeks.map((w, i) => (
              <th key={w.week || `pad-${i}`} scope="col" className="text-right font-semibold px-4 py-2">
                {i === 0 ? "This week" : weekLabel(w.week)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-default">
          {KPI_METRICS.map((metric) => (
            <tr key={metric.key}>
              <th scope="row" className="text-left font-semibold text-text-secondary px-4 py-1.5">
                {metric.label}
              </th>
              {weeks.map((w, i) => (
                <td key={w.week || `pad-${i}`} className="text-right text-text-primary px-4 py-1.5">
                  {formatKpi(metric, w[metric.key])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AutoApproveCard({ value, onChange }) {
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const save = async () => {
    const parsed = parseScoreInput(value, { allowBlank: true });
    if (!parsed.ok) {
      toast.show(parsed.error, "error");
      return;
    }
    setSaving(true);
    try {
      const res = await eventLeadsApi.saveSettings({ auto_approve_min_score: parsed.value });
      const saved = res.auto_approve_min_score;
      onChange(Number.isInteger(saved) ? String(saved) : "");
      toast.show(
        Number.isInteger(saved)
          ? `Auto approve is on for leads with an email scoring ${saved} or more.`
          : "Auto approve is off.",
      );
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card p-4">
      <label htmlFor="auto-approve-min" className="text-sm font-bold text-text-primary block mb-1">
        Auto approve
      </label>
      <p className="text-xs text-text-muted mb-2">
        New leads with an email at or above this score are approved as they arrive.
        Leave it blank to keep auto approve off.
      </p>
      <div className="flex items-center gap-2">
        <input
          id="auto-approve-min"
          type="number"
          min="0"
          max="100"
          step="1"
          placeholder="Off"
          className="input w-28"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button onClick={save} className="btn-outline" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}

function LinkedinCard({ confirm, onImported }) {
  const [includeExported, setIncludeExported] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [unknown, setUnknown] = useState([]);
  const fileRef = useRef(null);
  const toast = useToast();

  const preview = () =>
    startDownload(eventLeadsApi.linkedinQueueUrl({ dryRun: true, includeExported }));

  const download = async () => {
    const ok = await confirm({
      title: "Download the LinkedIn queue?",
      body: "Every lead in the file is marked exported, so the next download leaves it out.",
      confirmLabel: "Download",
    });
    if (!ok) return;
    startDownload(eventLeadsApi.linkedinQueueUrl({ dryRun: false, includeExported }));
  };

  const upload = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const rows = parseCsvObjects(await file.text());
      if (rows.length === 0) {
        toast.show("That file has no rows to import.", "error");
        return;
      }
      const res = await eventLeadsApi.uploadLinkedinResults(rows);
      const summary = linkedinResultSummary(res);
      toast.show(summary.message, summary.type);
      setUnknown([...new Set(res.unknown || [])]);
      await onImported();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div className="card p-4">
      <div className="text-sm font-bold text-text-primary mb-1">LinkedIn queue</div>
      <p className="text-xs text-text-muted mb-2">
        Approved leads with a LinkedIn URL. Download the file for Linked Helper,
        then upload its results here.
      </p>
      <div className="flex items-center gap-2 mb-3">
        <input
          id="include-exported"
          type="checkbox"
          checked={includeExported}
          onChange={(e) => setIncludeExported(e.target.checked)}
        />
        <label htmlFor="include-exported" className="text-xs text-text-secondary">
          Include leads already exported
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={download} className="btn-primary">
          <Download className="w-4 h-4" /> Download queue
        </button>
        <button onClick={preview} className="btn-ghost">
          <Eye className="w-4 h-4" /> Preview queue
        </button>
        <label
          htmlFor="linkedin-results"
          className={`btn-outline cursor-pointer ${uploading ? "opacity-50" : ""}`}
        >
          <Upload className="w-4 h-4" /> {uploading ? "Uploading…" : "Upload results"}
        </label>
        <input
          id="linkedin-results"
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          disabled={uploading}
          onChange={(e) => upload(e.target.files?.[0])}
        />
      </div>
      {unknown.length > 0 && (
        <div className="mt-3">
          <div className="text-xs font-semibold text-text-secondary mb-1">
            Not matched to a lead
          </div>
          <ul className="text-xs text-text-muted font-mono space-y-0.5 max-h-32 overflow-y-auto">
            {unknown.map((url, i) => (
              <li key={`${i}-${url}`}>{url}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LeadsTable({ rows, approvingId, onOpen, onApprove }) {
  const now = new Date();
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-text-muted text-left">
            <th scope="col" className="font-semibold px-3 py-2">Event</th>
            <th scope="col" className="font-semibold px-3 py-2">Host organization</th>
            <th scope="col" className="font-semibold px-3 py-2">Category</th>
            <th scope="col" className="font-semibold px-3 py-2">Score</th>
            <th scope="col" className="font-semibold px-3 py-2">Contact</th>
            <th scope="col" className="font-semibold px-3 py-2">Status</th>
            <th scope="col" className="font-semibold px-3 py-2">
              <span className="sr-only">Approve</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-default">
          {rows.map((lead) => (
            <LeadRow
              key={lead.id}
              lead={lead}
              now={now}
              approving={approvingId === lead.id}
              onOpen={onOpen}
              onApprove={onApprove}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LeadRow({ lead, now, approving, onOpen, onApprove }) {
  const days = daysUntilLabel(leadDays(lead, now));
  const retry = needsRetry(lead);
  return (
    <tr
      role="button"
      tabIndex={0}
      aria-label={`Open ${eventName(lead)}`}
      className={`cursor-pointer hover:bg-bg-secondary focus:outline-none focus:ring-2 focus:ring-primary/50 ${
        lead.status === "archived" ? "opacity-60" : ""
      }`}
      onClick={() => onOpen(lead)}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen(lead);
        }
      }}
    >
      <td className="px-3 py-2 align-top">
        <div className="font-semibold text-text-primary">{eventName(lead)}</div>
        <div className="text-xs text-text-muted">
          {eventDateLabel(lead)}
          {days && `, ${days}`}
        </div>
      </td>
      <td className="px-3 py-2 align-top text-text-secondary">{lead.organizer_name}</td>
      <td className="px-3 py-2 align-top text-text-secondary">{categoryLabel(lead)}</td>
      <td className="px-3 py-2 align-top text-text-primary whitespace-nowrap">{scoreLabel(lead)}</td>
      <td className="px-3 py-2 align-top text-text-secondary">{contactSummary(lead)}</td>
      <td className="px-3 py-2 align-top">
        <StatusBadge lead={lead} />
      </td>
      <td className="px-3 py-2 align-top text-right">
        <button
          className={`${retry ? "btn-outline" : "btn-primary"} whitespace-nowrap`}
          disabled={approveDisabled(lead)}
          onClick={(e) => {
            e.stopPropagation();
            onApprove(lead);
          }}
          onKeyDown={(e) => e.stopPropagation()}
        >
          {retry ? <RotateCw className="w-4 h-4" /> : <Check className="w-4 h-4" />}
          {approving ? "Working…" : approveLabel(lead)}
        </button>
      </td>
    </tr>
  );
}
