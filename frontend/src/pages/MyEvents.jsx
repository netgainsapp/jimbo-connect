import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Calendar, MapPin, Plus, Users, LogOut, Copy, Trash2 } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";
import { formatDateTime, copyToClipboard } from "../lib/utils.js";

export default function MyEvents() {
  const [events, setEvents] = useState([]);
  const [hosted, setHosted] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showJoin, setShowJoin] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [code, setCode] = useState("");
  const [joining, setJoining] = useState(false);
  const [form, setForm] = useState({ name: "", date: "", location: "" });
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();
  const confirm = useConfirm();

  const load = async () => {
    setLoading(true);
    try {
      const [joined, mine] = await Promise.all([
        eventsApi.myEvents(),
        eventsApi.myHostedEvents().catch(() => []),
      ]);
      setEvents(joined);
      setHosted(mine);
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const join = async (e) => {
    e.preventDefault();
    if (!code.trim()) return;
    setJoining(true);
    try {
      const ev = await eventsApi.join(code.trim().toUpperCase());
      toast.show(`Joined ${ev.name}`);
      setCode("");
      setShowJoin(false);
      navigate(`/events/${ev.id}`);
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setJoining(false);
    }
  };

  const create = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.date) {
      toast.show("Add a name and a date", "error");
      return;
    }
    setCreating(true);
    try {
      const ev = await eventsApi.create({
        name: form.name.trim(),
        date: new Date(form.date).toISOString(),
        location: form.location.trim(),
      });
      setHosted((prev) => [ev, ...prev]);
      setForm({ name: "", date: "", location: "" });
      setShowCreate(false);
      toast.show(`Created ${ev.name}. Share code ${ev.join_code} with your guests.`);
    } catch (err) {
      if (err.status === 403) {
        toast.show("Your free plan includes one event. Upgrade to host more.", "error");
      } else {
        toast.show(err.message, "error");
      }
    } finally {
      setCreating(false);
    }
  };

  const removeHosted = async (ev) => {
    if (
      !(await confirm({
        title: `Delete "${ev.name}"?`,
        body: "This removes the event and its directory for everyone. Cannot be undone.",
        confirmLabel: "Delete event",
        destructive: true,
      }))
    )
      return;
    try {
      await eventsApi.remove(ev.id);
      setHosted((prev) => prev.filter((x) => x.id !== ev.id));
      toast.show("Event deleted");
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My events</h1>
          <p className="text-sm text-text-secondary">
            Host your own event, or browse a directory you've joined.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              setShowCreate((v) => !v);
              setShowJoin(false);
            }}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" /> Host an event
          </button>
          <button
            onClick={() => {
              setShowJoin((v) => !v);
              setShowCreate(false);
            }}
            className="btn-outline"
          >
            Join event
          </button>
        </div>
      </div>

      {showCreate && (
        <form onSubmit={create} className="card p-4 mb-6 flex flex-col gap-3">
          <div className="text-sm font-bold text-text-primary">Host a new event</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="event-name">Event name</label>
              <input
                id="event-name"
                className="input"
                placeholder="Denver Founders Dinner"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                autoFocus
              />
            </div>
            <div>
              <label className="label" htmlFor="event-date">Date and time</label>
              <input
                id="event-date"
                type="datetime-local"
                className="input"
                value={form.date}
                onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
              />
            </div>
            <div className="sm:col-span-2">
              <label className="label" htmlFor="event-location">Location (optional)</label>
              <input
                id="event-location"
                className="input"
                placeholder="Improper City, Denver"
                value={form.location}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button type="submit" className="btn-primary" disabled={creating}>
              {creating ? "Creating…" : "Create event"}
            </button>
            <span className="text-xs text-text-muted">
              Free plan includes one event. We generate a join code to share.
            </span>
          </div>
        </form>
      )}

      {showJoin && (
        <form
          onSubmit={join}
          className="card p-4 mb-6 flex flex-col sm:flex-row gap-3 sm:items-end"
        >
          <div className="flex-1">
            <label className="label" htmlFor="join-code">Event join code</label>
            <input
              id="join-code"
              className="input"
              placeholder="e.g. DENVER01"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              autoFocus
            />
          </div>
          <button type="submit" className="btn-primary" disabled={joining}>
            {joining ? "Joining…" : "Join"}
          </button>
        </form>
      )}

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : (
        <>
          {hosted.length > 0 && (
            <div className="mb-8">
              <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
                Events you host
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {hosted.map((e) => (
                  <div key={e.id} className="card p-4 flex flex-col gap-2">
                    <Link to={`/events/${e.id}`} className="block">
                      <div className="font-bold text-text-primary text-lg leading-tight">
                        {e.name}
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary mt-1">
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" /> {formatDateTime(e.date)}
                        </span>
                        {e.location && (
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5" /> {e.location}
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1">
                          <Users className="w-3.5 h-3.5" /> {e.attendee_count}
                        </span>
                      </div>
                    </Link>
                    <div className="flex items-center justify-between gap-2 pt-2 border-t border-border-default">
                      <button
                        onClick={() => {
                          copyToClipboard(e.join_code);
                          toast.show(`Join code ${e.join_code} copied`);
                        }}
                        className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
                      >
                        <Copy className="w-3.5 h-3.5" /> Code {e.join_code}
                      </button>
                      <button
                        onClick={() => removeHosted(e)}
                        className="p-1.5 rounded-full text-text-secondary hover:bg-red-50 hover:text-red-500"
                        aria-label={`Delete ${e.name}`}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
            Events you've joined
          </div>
          {events.length === 0 ? (
            <div className="card p-10 text-center">
              <Calendar className="w-10 h-10 text-text-muted mx-auto mb-3" />
              <div className="font-bold text-text-primary mb-1">
                You haven't joined any events yet
              </div>
              <div className="text-sm text-text-secondary mb-4">
                Got a join code from a host? Tap "Join event" above to get started.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link
                to="/events/all"
                className="card p-5 hover:border-primary/50 transition border-dashed flex flex-col justify-center"
              >
                <div className="font-bold text-text-primary text-lg mb-1">
                  Everyone (all cohorts)
                </div>
                <div className="text-sm text-text-secondary">
                  Browse every attendee from every event you've joined, one
                  combined directory.
                </div>
              </Link>
              {events.map((e) => (
                <div key={e.id} className="card p-4 hover:border-primary/50 transition group relative">
                  <Link to={`/events/${e.id}`} className="block">
                    <div className="font-bold text-text-primary text-lg leading-tight pr-8">
                      {e.name}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary mt-1">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" /> {formatDateTime(e.date)}
                      </span>
                      {e.location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5" /> {e.location}
                        </span>
                      )}
                      <span className="inline-flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" /> {e.attendee_count}
                      </span>
                      {e.industry_tags?.map((t) => (
                        <span
                          key={t}
                          className="bg-bg-secondary text-text-secondary px-2 py-0.5 rounded-pill"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  </Link>
                  <button
                    onClick={async (ev) => {
                      ev.preventDefault();
                      ev.stopPropagation();
                      if (
                        !(await confirm({
                          title: `Leave "${e.name}"?`,
                          body: "You won't see the directory anymore.",
                          confirmLabel: "Leave event",
                          destructive: true,
                        }))
                      )
                        return;
                      try {
                        await eventsApi.leave(e.id);
                        setEvents((prev) => prev.filter((x) => x.id !== e.id));
                        toast.show("Left event");
                      } catch (err) {
                        toast.show(err.message, "error");
                      }
                    }}
                    className="absolute top-2 right-2 p-1.5 rounded-full bg-white border border-border-default text-text-secondary hover:bg-red-50 hover:text-red-500 hover:border-red-200 opacity-0 group-hover:opacity-100 focus:opacity-100 transition"
                    aria-label={`Leave ${e.name}`}
                  >
                    <LogOut className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
