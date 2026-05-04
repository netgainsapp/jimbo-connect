import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Calendar, MapPin, Users, Copy } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { copyToClipboard, formatDate } from "../lib/utils.js";
import Avatar from "../components/Avatar.jsx";

export default function AdminEventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    Promise.all([eventsApi.get(id), eventsApi.attendees(id)])
      .then(([ev, list]) => {
        setEvent(ev);
        setAttendees(list);
      })
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const copyLink = async () => {
    const link = `${window.location.origin}/join/${event.join_code}`;
    await copyToClipboard(link);
    toast.show("Join link copied");
  };

  const copyCode = async () => {
    await copyToClipboard(event.join_code);
    toast.show("Code copied");
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-6 py-10 text-text-muted">Loading…</div>
    );
  }
  if (!event) return null;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <Link
        to="/admin/events"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-primary mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to events
      </Link>

      <div className="card p-6 mb-6">
        <h1 className="text-2xl font-bold text-text-primary">{event.name}</h1>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text-secondary mt-1">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="w-4 h-4" /> {formatDate(event.date)}
          </span>
          {event.location && (
            <span className="inline-flex items-center gap-1.5">
              <MapPin className="w-4 h-4" /> {event.location}
            </span>
          )}
          <span className="inline-flex items-center gap-1.5">
            <Users className="w-4 h-4" /> {event.attendee_count} attendees
          </span>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-sm text-text-secondary">Join code:</span>
          <button
            onClick={copyCode}
            className="font-mono bg-bg-secondary px-3 py-1.5 rounded-card text-text-primary hover:bg-border-default"
            title="Copy code"
          >
            {event.join_code}
          </button>
          <button onClick={copyLink} className="btn-outline">
            <Copy className="w-4 h-4" /> Copy join link
          </button>
        </div>
        {event.industry_tags?.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {event.industry_tags.map((t) => (
              <span key={t} className="pill">
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      <h2 className="font-bold text-text-primary text-lg mb-3">Attendees</h2>
      {attendees.length === 0 ? (
        <div className="card p-8 text-center text-text-secondary">
          No one has joined this event yet. Share the join link.
        </div>
      ) : (
        <div className="card divide-y divide-border-default">
          {attendees.map((a) => {
            const p = a.profile || {};
            return (
              <div key={a.id} className="flex items-center gap-4 px-5 py-3">
                <Avatar name={p.name} photoUrl={p.photo_url} size={40} />
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-text-primary truncate">
                    {p.name || a.email}
                  </div>
                  <div className="text-sm text-text-secondary truncate">
                    {p.role}
                    {p.role && p.company && " · "}
                    {p.company}
                  </div>
                </div>
                <div className="text-sm text-text-muted truncate hidden sm:block">
                  {a.email}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
