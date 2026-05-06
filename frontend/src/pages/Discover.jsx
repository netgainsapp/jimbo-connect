import { useEffect, useState } from "react";
import { Calendar, MapPin, Users, Compass, Send, Check } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { formatDate } from "../lib/utils.js";
import Modal from "../components/Modal.jsx";

export default function Discover() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  const [requested, setRequested] = useState(new Set());
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    eventsApi
      .discover()
      .then(setEvents)
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const submitRequest = async () => {
    if (!active) return;
    setSubmitting(true);
    try {
      await eventsApi.requestInvite(active.id, message);
      setRequested((prev) => new Set(prev).add(active.id));
      toast.show("Invite request sent");
      setActive(null);
      setMessage("");
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary inline-flex items-center gap-2">
        <Compass className="w-6 h-6 text-primary" /> Discover events
      </h1>
      <p className="text-sm text-text-secondary mb-6">
        Upcoming events you haven't joined yet. Tap "Ask for an invite" to
        message the host.
      </p>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : events.length === 0 ? (
        <div className="card p-10 text-center text-text-secondary">
          Nothing on the horizon. You're up to date.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {events.map((e) => {
            const sent = requested.has(e.id);
            return (
              <div key={e.id} className="card p-4 flex flex-col gap-2">
                <div className="font-bold text-text-primary text-lg leading-tight">
                  {e.name}
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-text-secondary">
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" /> {formatDate(e.date)}
                  </span>
                  {e.location && (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5" /> {e.location}
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1">
                    <Users className="w-3.5 h-3.5" /> {e.attendee_count}
                  </span>
                  {e.host_name && (
                    <span className="text-text-muted">Hosted by {e.host_name}</span>
                  )}
                </div>
                {e.industry_tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {e.industry_tags.map((t) => (
                      <span
                        key={t}
                        className="text-xs bg-bg-secondary text-text-secondary px-2 py-0.5 rounded-pill"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                <div className="mt-1">
                  {sent ? (
                    <button
                      disabled
                      className="btn-ghost cursor-default text-primary"
                    >
                      <Check className="w-4 h-4" /> Request sent
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setActive(e);
                        setMessage("");
                      }}
                      className="btn-primary"
                    >
                      <Send className="w-4 h-4" /> Ask for an invite
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Modal open={Boolean(active)} onClose={() => setActive(null)} maxWidth="max-w-md">
        {active && (
          <div className="p-6">
            <h2 className="text-lg font-bold text-text-primary">
              Request invite to {active.name}
            </h2>
            <p className="text-sm text-text-secondary mt-1">
              Hosted by {active.host_name || "the host"}. We'll send them a quick
              note and your profile.
            </p>
            <label className="label mt-4">Optional message</label>
            <textarea
              className="input min-h-[100px]"
              placeholder="Hey, would love to come — heard about it from a friend."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
            />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setActive(null)} className="btn-ghost">
                Cancel
              </button>
              <button
                onClick={submitRequest}
                className="btn-primary"
                disabled={submitting}
              >
                {submitting ? "Sending…" : "Send request"}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
