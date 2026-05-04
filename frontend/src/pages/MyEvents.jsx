import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Calendar, MapPin, Plus, Users } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { formatDate } from "../lib/utils.js";

export default function MyEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showJoin, setShowJoin] = useState(false);
  const [code, setCode] = useState("");
  const [joining, setJoining] = useState(false);
  const navigate = useNavigate();
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      const list = await eventsApi.myEvents();
      setEvents(list);
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

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My events</h1>
          <p className="text-sm text-text-secondary">
            Browse the directory for any event you've joined.
          </p>
        </div>
        <button onClick={() => setShowJoin((v) => !v)} className="btn-primary">
          <Plus className="w-4 h-4" /> Join event
        </button>
      </div>

      {showJoin && (
        <form
          onSubmit={join}
          className="card p-4 mb-6 flex flex-col sm:flex-row gap-3 sm:items-end"
        >
          <div className="flex-1">
            <label className="label">Event join code</label>
            <input
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
      ) : events.length === 0 ? (
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
          {events.map((e) => (
            <Link
              key={e.id}
              to={`/events/${e.id}`}
              className="card p-5 hover:border-primary/50 transition"
            >
              <div className="font-bold text-text-primary text-lg mb-1">
                {e.name}
              </div>
              <div className="flex items-center gap-1.5 text-sm text-text-secondary">
                <Calendar className="w-4 h-4" />
                {formatDate(e.date)}
              </div>
              {e.location && (
                <div className="flex items-center gap-1.5 text-sm text-text-secondary mt-1">
                  <MapPin className="w-4 h-4" />
                  {e.location}
                </div>
              )}
              <div className="flex items-center gap-1.5 text-sm text-text-secondary mt-1">
                <Users className="w-4 h-4" />
                {e.attendee_count} attendee{e.attendee_count === 1 ? "" : "s"}
              </div>
              {e.industry_tags?.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {e.industry_tags.map((t) => (
                    <span key={t} className="pill">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
