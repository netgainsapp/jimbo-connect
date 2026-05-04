import { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Calendar, MapPin, Search, Users } from "lucide-react";
import { eventsApi, contactsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { formatDate } from "../lib/utils.js";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";

export default function EventDirectory() {
  const { id } = useParams();
  const { user } = useAuth();
  const toast = useToast();

  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [savedSet, setSavedSet] = useState(new Set());
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState("all");
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const [ev, list, saved] = await Promise.all([
        eventsApi.get(id),
        eventsApi.attendees(id),
        contactsApi.list(),
      ]);
      setEvent(ev);
      setAttendees(list.filter((a) => a.id !== user.id));
      setSavedSet(new Set(saved.map((s) => s.contact_id)));
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const industries = useMemo(() => {
    const s = new Set();
    attendees.forEach((a) => {
      const v = a.profile?.industry;
      if (v) s.add(v);
    });
    return ["all", ...Array.from(s).sort()];
  }, [attendees]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return attendees.filter((a) => {
      const p = a.profile || {};
      if (industry !== "all" && p.industry !== industry) return false;
      if (!q) return true;
      const hay = [p.name, p.role, p.company, p.industry, a.email]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [attendees, query, industry]);

  const toggleSave = async (attendee) => {
    const isSaved = savedSet.has(attendee.id);
    try {
      if (isSaved) {
        await contactsApi.remove(attendee.id);
        setSavedSet((prev) => {
          const next = new Set(prev);
          next.delete(attendee.id);
          return next;
        });
        toast.show("Contact removed");
      } else {
        await contactsApi.save(attendee.id, "");
        setSavedSet((prev) => new Set(prev).add(attendee.id));
        toast.show("Contact saved");
      }
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <Link
        to="/events"
        className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-primary mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Back to my events
      </Link>

      {event && (
        <div className="mb-6">
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
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            className="input pl-9"
            placeholder="Search by name, company, role…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          className="input sm:w-56"
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
        >
          {industries.map((i) => (
            <option key={i} value={i}>
              {i === "all" ? "All industries" : i}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-text-secondary">
          No attendees match your search.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((a) => (
            <AttendeeCard
              key={a.id}
              attendee={a}
              isSaved={savedSet.has(a.id)}
              onToggleSave={toggleSave}
              onOpen={setActive}
            />
          ))}
        </div>
      )}

      <AttendeeProfileModal
        attendee={active}
        open={Boolean(active)}
        onClose={() => setActive(null)}
        onSavedChange={async () => {
          const saved = await contactsApi.list();
          setSavedSet(new Set(saved.map((s) => s.contact_id)));
        }}
      />
    </div>
  );
}
