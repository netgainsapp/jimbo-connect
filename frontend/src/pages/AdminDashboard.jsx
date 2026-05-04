import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Users,
  Calendar,
  CalendarPlus,
  UserPlus,
  Mail,
  HelpCircle,
  MapPin,
  ArrowRight,
} from "lucide-react";
import { adminApi, eventsApi } from "../lib/api.js";
import { formatDate } from "../lib/utils.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import WelcomeModal, { shouldShowWelcome } from "../components/WelcomeModal.jsx";

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [nextEvent, setNextEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const toast = useToast();

  useEffect(() => {
    Promise.all([adminApi.stats(), eventsApi.list().catch(() => [])])
      .then(([s, evs]) => {
        setStats(s);
        const now = Date.now();
        const upcoming = evs
          .filter((e) => new Date(e.date).getTime() >= now)
          .sort((a, b) => new Date(a.date) - new Date(b.date));
        setNextEvent(upcoming[0] || null);
      })
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    if (shouldShowWelcome()) setWelcomeOpen(true);
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatCard
            to="/admin/users"
            icon={<Users className="w-5 h-5" />}
            label="Total members"
            value={stats?.total_users ?? 0}
          />
          <StatCard
            to="/admin/events"
            icon={<Calendar className="w-5 h-5" />}
            label="Events"
            value={stats?.total_events ?? 0}
          />
        </div>
      )}

      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <ActionCard
          to="/admin/events"
          icon={<CalendarPlus className="w-5 h-5" />}
          title="Create an event"
          body="Name, date, location — we'll generate the join code."
        />
        <ActionCard
          to="/admin/events"
          icon={<UserPlus className="w-5 h-5" />}
          title="Import attendees"
          body="Paste emails or a CSV. We'll create accounts and temp passwords."
        />
        <ActionCard
          to="/admin/templates"
          icon={<Mail className="w-5 h-5" />}
          title="Email templates"
          body="Save the date, day-of, post-event — copy or open in your mail."
        />
      </div>

      <div className="mt-8">
        <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
          Next event
        </div>
        {nextEvent ? (
          <Link
            to={`/admin/events/${nextEvent.id}`}
            className="card p-5 flex flex-col sm:flex-row sm:items-center gap-4 hover:border-primary/50 transition"
          >
            <div className="w-12 h-12 rounded-card bg-primary/10 text-primary flex flex-col items-center justify-center shrink-0">
              <div className="text-[10px] uppercase font-bold leading-none">
                {new Date(nextEvent.date).toLocaleString(undefined, {
                  month: "short",
                })}
              </div>
              <div className="text-xl font-bold leading-none">
                {new Date(nextEvent.date).getDate()}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-bold text-text-primary text-lg truncate">
                {nextEvent.name}
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-text-secondary mt-0.5">
                <span className="inline-flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {formatDate(nextEvent.date)}
                </span>
                {nextEvent.location && (
                  <span className="inline-flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" /> {nextEvent.location}
                  </span>
                )}
                <span className="inline-flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  {nextEvent.attendee_count} attendee
                  {nextEvent.attendee_count === 1 ? "" : "s"}
                </span>
              </div>
            </div>
            <div className="text-primary font-semibold inline-flex items-center gap-1 text-sm">
              Open <ArrowRight className="w-4 h-4" />
            </div>
          </Link>
        ) : (
          <div className="card p-5 text-text-secondary text-sm">
            No upcoming events.{" "}
            <Link to="/admin/events" className="text-primary font-semibold">
              Create one →
            </Link>
          </div>
        )}
      </div>

      <button
        onClick={() => setWelcomeOpen(true)}
        className="mt-6 inline-flex items-center gap-1 text-sm text-text-secondary hover:text-primary"
      >
        <HelpCircle className="w-4 h-4" /> Replay the welcome tour
      </button>

      <WelcomeModal
        open={welcomeOpen}
        onClose={() => setWelcomeOpen(false)}
        hostName={user?.profile?.name}
      />
    </div>
  );
}

function ActionCard({ to, icon, title, body }) {
  return (
    <Link
      to={to}
      className="card p-5 hover:border-primary/50 transition flex flex-col gap-1"
    >
      <div className="text-primary">{icon}</div>
      <div className="font-bold text-text-primary mt-1">{title}</div>
      <p className="text-sm text-text-secondary">{body}</p>
    </Link>
  );
}

function StatCard({ icon, label, value, to }) {
  const inner = (
    <>
      <div className="flex items-center gap-2 text-text-secondary text-sm font-semibold">
        <span className="text-primary">{icon}</span>
        {label}
      </div>
      <div className="text-3xl font-bold text-text-primary mt-2">{value}</div>
    </>
  );
  if (to) {
    return (
      <Link to={to} className="card p-5 hover:border-primary/50 transition block">
        {inner}
      </Link>
    );
  }
  return <div className="card p-5">{inner}</div>;
}
