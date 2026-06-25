import { useEffect, useState } from "react";
import { Send, Download, Trash2, ExternalLink, Plus } from "lucide-react";
import { outreachApi } from "../lib/api.js";
import { formatDateTime } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";

function parseLeads(text) {
  return text
    .split(/\n/)
    .map((line) => {
      const parts = line.split(",").map((s) => s.trim());
      const email = (parts[0] || "").toLowerCase();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return null;
      return {
        email,
        name: parts[1] || "",
        company: parts[2] || "",
        role: parts[3] || "",
      };
    })
    .filter(Boolean);
}

export default function AdminOutreach() {
  const [status, setStatus] = useState(null);
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [adding, setAdding] = useState(false);
  const [pushing, setPushing] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const load = () =>
    Promise.all([outreachApi.status(), outreachApi.list()])
      .then(([s, l]) => {
        setStatus(s);
        setLeads(l);
      })
      .catch((e) => toast.show(e.message, "error"));

  useEffect(() => {
    load().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const add = async () => {
    const parsed = parseLeads(text);
    if (parsed.length === 0) {
      toast.show("Add at least one line starting with a valid email", "error");
      return;
    }
    setAdding(true);
    try {
      const res = await outreachApi.add(parsed);
      toast.show(`Added ${res.added} new lead${res.added === 1 ? "" : "s"}`);
      setText("");
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setAdding(false);
    }
  };

  const remove = async (lead) => {
    if (
      !(await confirm({
        title: "Remove this lead?",
        body: lead.email,
        confirmLabel: "Remove",
        destructive: true,
      }))
    )
      return;
    try {
      await outreachApi.remove(lead.id);
      setLeads((prev) => prev.filter((l) => l.id !== lead.id));
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const exportCsv = async () => {
    try {
      const csv = await outreachApi.exportCsv();
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "intro-connect-leads.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const push = async () => {
    setPushing(true);
    try {
      const res = await outreachApi.push();
      if (res.ok) {
        toast.show(`Pushed ${res.pushed} leads to signal-scout`);
        await load();
      } else if (res.skipped === "not_configured") {
        toast.show("Set SIGNAL_SCOUT_URL and SIGNAL_SCOUT_API_KEY first", "error");
      } else if (res.skipped === "no_new_leads") {
        toast.show("No new leads to push", "error");
      } else {
        toast.show(res.error || res.detail || "Push failed", "error");
      }
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setPushing(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 text-text-muted">
        Loading…
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Outreach</h1>
      <p className="text-sm text-text-secondary mb-6">
        Stage your host-acquisition leads here, then hand them to signal-scout,
        which does the sending, warmup, and reporting. Export the CSV and upload
        it on the signal-scout dashboard, or push directly once the connection
        is configured.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <Stat label="Total leads" value={status?.total ?? 0} />
        <Stat label="Not pushed" value={status?.new ?? 0} />
        <Stat label="Pushed" value={status?.pushed ?? 0} />
      </div>

      <div className="card p-4 mb-6">
        <div className="text-sm font-bold text-text-primary mb-1">Add leads</div>
        <p className="text-xs text-text-muted mb-2">
          One per line: <code>email, name, company, role</code>. Only the email
          is required.
        </p>
        <textarea
          className="input min-h-[120px] font-mono text-xs"
          placeholder={"eric@thunderview.com, Eric Marcoullier, Thunderview CEO Dinners, Founder\nalexandra@startupgrind.com, Alexandra Poelstra, Startup Grind Denver"}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="mt-2">
          <button onClick={add} className="btn-primary" disabled={adding}>
            <Plus className="w-4 h-4" /> {adding ? "Adding…" : "Add leads"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        <button onClick={exportCsv} className="btn-outline">
          <Download className="w-4 h-4" /> Export CSV
        </button>
        <button
          onClick={push}
          className="btn-primary"
          disabled={pushing || !status?.configured}
          title={
            status?.configured
              ? ""
              : "Set SIGNAL_SCOUT_URL and SIGNAL_SCOUT_API_KEY to enable a live push"
          }
        >
          <Send className="w-4 h-4" />
          {pushing ? "Pushing…" : "Push to signal-scout"}
        </button>
        {status?.signal_scout_url && (
          <a
            href={`${status.signal_scout_url}/dashboard/reports`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost"
          >
            <ExternalLink className="w-4 h-4" /> Open signal-scout
          </a>
        )}
        {!status?.configured && (
          <span className="text-xs text-text-muted">
            Live push is off until the signal-scout connection is configured.
            Export and upload in the meantime.
          </span>
        )}
      </div>

      {leads.length === 0 ? (
        <div className="card p-8 text-center text-sm text-text-secondary">
          No leads yet. Paste a list above to get started.
        </div>
      ) : (
        <div className="card divide-y divide-border-default">
          {leads.map((l) => (
            <div key={l.id} className="flex items-center gap-3 p-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wide px-2 py-0.5 rounded-full shrink-0 ${
                      l.status === "pushed"
                        ? "bg-green-100 text-green-700"
                        : "bg-bg-secondary text-text-secondary"
                    }`}
                  >
                    {l.status === "pushed" ? "Pushed" : "New"}
                  </span>
                  <span className="font-semibold text-text-primary truncate">
                    {l.name || l.email}
                  </span>
                </div>
                <div className="text-xs text-text-secondary truncate">
                  {l.email}
                  {l.company && ` · ${l.company}`}
                  {l.role && ` · ${l.role}`}
                </div>
              </div>
              {l.pushed_at && (
                <span className="text-xs text-text-muted shrink-0 hidden sm:block">
                  {formatDateTime(l.pushed_at)}
                </span>
              )}
              <button
                onClick={() => remove(l)}
                className="p-1.5 rounded-full text-text-secondary hover:bg-red-50 hover:text-red-500 shrink-0"
                aria-label={`Remove ${l.email}`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-text-secondary font-semibold">{label}</div>
      <div className="text-2xl font-bold text-text-primary mt-1">{value}</div>
    </div>
  );
}
