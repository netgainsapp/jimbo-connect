import { useEffect, useState } from "react";
import { adminApi } from "../lib/api.js";
import { formatDateTime } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";

const REASON_STYLE = {
  bounce: "bg-red-100 text-red-700",
  complaint: "bg-amber-100 text-amber-700",
  unsubscribe: "bg-bg-secondary text-text-secondary",
};

const REASON_HELP = {
  bounce: "Address does not deliver. Blocked for all mail.",
  complaint: "Marked our email as spam. Blocked for marketing mail.",
  unsubscribe: "Opted out. Blocked for marketing mail.",
};

export default function AdminSuppressions() {
  const toast = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .suppressions()
      .then(setRows)
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Suppressed emails</h1>
      <p className="text-sm text-text-secondary mb-6">
        Addresses we no longer send to, and why. This list is enforced
        automatically: unsubscribes and spam complaints stop marketing mail, and
        hard bounces stop all mail.
      </p>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : rows.length === 0 ? (
        <div className="card p-5 text-sm text-text-secondary">
          No suppressed addresses. Nobody has unsubscribed, complained, or hard
          bounced.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted border-b border-border-default">
                <th className="p-3 font-semibold">Email</th>
                <th className="p-3 font-semibold">Reason</th>
                <th className="p-3 font-semibold">Source</th>
                <th className="p-3 font-semibold">Date</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-border-default last:border-0">
                  <td className="p-3 text-text-primary break-all">{r.email}</td>
                  <td className="p-3">
                    <span
                      title={REASON_HELP[r.reason] || ""}
                      className={`text-[10px] uppercase font-bold tracking-wide px-2 py-0.5 rounded-full ${
                        REASON_STYLE[r.reason] || "bg-bg-secondary text-text-secondary"
                      }`}
                    >
                      {r.reason || "unknown"}
                    </span>
                  </td>
                  <td className="p-3 text-text-secondary">{r.source || "—"}</td>
                  <td className="p-3 text-text-secondary whitespace-nowrap">
                    {r.created_at ? formatDateTime(r.created_at) : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
