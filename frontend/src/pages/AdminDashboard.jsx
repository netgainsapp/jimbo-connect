import { useEffect, useState } from "react";
import { Users, Calendar, Bookmark } from "lucide-react";
import { adminApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    adminApi
      .stats()
      .then(setStats)
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Admin dashboard</h1>
      <p className="text-sm text-text-secondary mb-6">
        Platform-wide engagement at a glance.
      </p>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            icon={<Users className="w-5 h-5" />}
            label="Total members"
            value={stats?.total_users ?? 0}
          />
          <StatCard
            icon={<Calendar className="w-5 h-5" />}
            label="Events"
            value={stats?.total_events ?? 0}
          />
          <StatCard
            icon={<Bookmark className="w-5 h-5" />}
            label="Connections saved"
            value={stats?.total_connections ?? 0}
          />
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value }) {
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
