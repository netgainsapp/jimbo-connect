import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Search, Users, Trash2 } from "lucide-react";
import { adminApi, eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventFilter, setEventFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(null);
  const toast = useToast();

  useEffect(() => {
    Promise.all([adminApi.listUsers(), eventsApi.list().catch(() => [])])
      .then(([u, ev]) => {
        setUsers(u);
        setEvents(ev);
      })
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return users.filter((u) => {
      if (eventFilter !== "all" && !(u.event_ids || []).includes(eventFilter)) {
        return false;
      }
      if (!q) return true;
      const p = u.profile || {};
      const hay = [p.name, p.role, p.company, p.industry, u.email]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [users, query, eventFilter]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <Link
        to="/admin"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-primary mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to dashboard
      </Link>

      <div className="flex items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary inline-flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" /> All members
          </h1>
          <p className="text-sm text-text-secondary">
            Everyone who's ever attended one of your events.
          </p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-text-primary">
            {users.length}
          </div>
          <div className="text-xs text-text-muted">total members</div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            className="input pl-9"
            placeholder="Search by name, company, role, industry…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          className="input sm:w-64"
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
        >
          <option value="all">All events</option>
          {events.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.name}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-text-secondary">
          {users.length === 0
            ? "No members yet. Import attendees to populate this list."
            : "No matches."}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((u) => (
            <div key={u.id} className="relative group">
              <AttendeeCard
                attendee={u}
                hideActions
                onOpen={setActive}
                meta={
                  <span>
                    {u.event_count} event{u.event_count === 1 ? "" : "s"} attended
                  </span>
                }
              />
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  const name = u.profile?.name || u.email;
                  if (
                    !confirm(
                      `Permanently delete ${name}?\n\nThis removes them from every event, deletes their saved contacts and messages, and frees up their email for re-registration. Cannot be undone.`
                    )
                  )
                    return;
                  try {
                    await adminApi.deleteUser(u.id);
                    setUsers((prev) => prev.filter((x) => x.id !== u.id));
                    toast.show("User deleted");
                  } catch (err) {
                    toast.show(err.message, "error");
                  }
                }}
                className="absolute top-2 right-2 p-1.5 rounded-full bg-white border border-border-default text-text-secondary hover:bg-red-50 hover:text-red-500 hover:border-red-200 opacity-0 group-hover:opacity-100 transition"
                title="Delete account"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      <AttendeeProfileModal
        attendee={active}
        open={Boolean(active)}
        onClose={() => setActive(null)}
      />
    </div>
  );
}
