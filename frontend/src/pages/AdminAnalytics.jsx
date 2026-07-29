import { useEffect, useState } from "react";
import { Users, Calendar, UserCheck, MessageSquare, Bookmark, BarChart3, Repeat } from "lucide-react";
import { adminApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";

export default function AdminAnalytics() {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminApi
      .analytics(30)
      .then(setData)
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10 text-text-muted">Loading…</div>;
  }
  if (!data) return null;

  const t = data.totals;
  const series = data.signups_series || [];
  const peak = Math.max(1, ...series.map((p) => p.count));

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Analytics</h1>
      <p className="text-sm text-text-secondary mb-6">
        Platform activity across the last {data.window_days} days.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <Tile icon={<Users className="w-5 h-5" />} label="Members" value={t.users} />
        <Tile icon={<Calendar className="w-5 h-5" />} label="Events" value={t.events} />
        <Tile icon={<UserCheck className="w-5 h-5" />} label="Active hosts" value={t.active_hosts} />
        <Tile icon={<Bookmark className="w-5 h-5" />} label="Contacts saved" value={t.contacts_saved} />
        <Tile icon={<MessageSquare className="w-5 h-5" />} label="Messages sent" value={t.messages_sent} />
        <Tile icon={<BarChart3 className="w-5 h-5" />} label="Avg attendees / event" value={t.avg_attendees_per_event} />
        {/* The product led loop: guests who went on to host their own. */}
        <Tile
          icon={<Repeat className="w-5 h-5" />}
          label="Guests turned host"
          value={t.attendee_to_host ?? 0}
        />
      </div>

      <div className="card p-5 mt-6">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs uppercase tracking-wider text-text-muted font-semibold">
            Signups, last {data.window_days} days
          </div>
          <div className="text-sm font-bold text-text-primary">{data.signups_in_window} total</div>
        </div>
        <div className="flex items-end gap-[3px] h-32">
          {series.map((p) => (
            <div key={p.date} className="flex-1 group relative flex items-end" title={`${p.date}: ${p.count}`}>
              <div
                className="w-full rounded-t bg-primary/80 group-hover:bg-primary transition"
                style={{ height: `${Math.max(2, (p.count / peak) * 100)}%` }}
              />
            </div>
          ))}
        </div>
        <div className="flex justify-between text-[11px] text-text-muted mt-2">
          <span>{series[0]?.date}</span>
          <span>{series[series.length - 1]?.date}</span>
        </div>
      </div>

      <div className="card p-5 mt-6">
        <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-3">
          Plan mix
        </div>
        <div className="flex flex-col gap-2">
          {["free", "starter", "pro"].map((plan) => {
            const n = data.plan_mix?.[plan] ?? 0;
            const total = Object.values(data.plan_mix || {}).reduce((a, b) => a + b, 0) || 1;
            return (
              <div key={plan} className="flex items-center gap-3">
                <div className="w-16 text-sm capitalize text-text-secondary">{plan}</div>
                <div className="flex-1 h-3 rounded-full bg-bg-secondary overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: `${(n / total) * 100}%` }} />
                </div>
                <div className="w-10 text-right text-sm font-semibold text-text-primary">{n}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Tile({ icon, label, value }) {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 text-text-secondary text-sm font-semibold">
        <span className="text-primary">{icon}</span>
        {label}
      </div>
      <div className="text-3xl font-bold text-text-primary mt-2">{value}</div>
    </div>
  );
}
