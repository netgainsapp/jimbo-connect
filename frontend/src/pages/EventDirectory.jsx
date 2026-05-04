import { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Calendar, MapPin, Search, Users, ChevronDown } from "lucide-react";
import { eventsApi, contactsApi, sponsorsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { formatDate } from "../lib/utils.js";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";
import SponsorTile from "../components/SponsorTile.jsx";

export default function EventDirectory() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [event, setEvent] = useState(null);
  const [myEvents, setMyEvents] = useState([]);
  const [attendees, setAttendees] = useState([]);
  const [sponsors, setSponsors] = useState([]);
  const [savedSet, setSavedSet] = useState(new Set());
  const [notesMap, setNotesMap] = useState({});
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState("all");
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);

  const isAll = id === "all";

  const load = async () => {
    setLoading(true);
    try {
      if (isAll) {
        const [list, saved, mine] = await Promise.all([
          eventsApi.allMyAttendees(),
          contactsApi.list(),
          eventsApi.myEvents().catch(() => []),
        ]);
        setEvent(null);
        setAttendees(list.filter((a) => a.id !== user.id));
        setSavedSet(new Set(saved.map((s) => s.contact_id)));
        const nm = {};
        saved.forEach((s) => {
          if (s.note) nm[s.contact_id] = s.note;
        });
        setNotesMap(nm);
        setSponsors([]);
        setMyEvents(mine);
      } else {
        const [ev, list, saved, sp, mine] = await Promise.all([
          eventsApi.get(id),
          eventsApi.attendees(id),
          contactsApi.list(),
          sponsorsApi.list(id).catch(() => []),
          eventsApi.myEvents().catch(() => []),
        ]);
        setEvent(ev);
        setAttendees(list.filter((a) => a.id !== user.id));
        setSavedSet(new Set(saved.map((s) => s.contact_id)));
        const nm = {};
        saved.forEach((s) => {
          if (s.note) nm[s.contact_id] = s.note;
        });
        setNotesMap(nm);
        setSponsors(sp.filter((s) => s.active));
        setMyEvents(mine);
      }
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
      <div className="mb-6">
        <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-1">
          {isAll ? "Everyone you've met" : "Cohort"}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {myEvents.length >= 1 ? (
            <div className="relative inline-block">
              <select
                value={isAll ? "all" : id}
                onChange={(e) => navigate(`/events/${e.target.value}`)}
                className="appearance-none bg-transparent text-lg font-bold text-text-primary pr-7 hover:text-primary cursor-pointer focus:outline-none"
              >
                <option value="all">Everyone (all cohorts)</option>
                {myEvents.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-4 h-4 text-text-secondary absolute right-0 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          ) : (
            <h1 className="text-lg font-bold text-text-primary">
              {event?.name || "Everyone you've met"}
            </h1>
          )}
          <Link
            to="/events"
            className="text-xs font-semibold text-text-secondary hover:text-primary inline-flex items-center gap-1"
          >
            <ArrowLeft className="w-3 h-3" /> All cohorts
          </Link>
        </div>
        {isAll ? (
          <div className="text-sm text-text-secondary mt-2">
            Everyone from every event you've joined.
          </div>
        ) : (
          event && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-text-secondary mt-2">
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
          )
        )}
      </div>

      {sponsors.length > 0 && (
        <div className="mb-6">
          <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
            Brought to you by
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {sponsors.map((sp) => (
              <SponsorTile key={sp.id} sponsor={sp} />
            ))}
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
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {filtered.map((a) => (
            <AttendeeCard
              key={a.id}
              attendee={a}
              isSaved={savedSet.has(a.id)}
              onToggleSave={toggleSave}
              onOpen={setActive}
              note={notesMap[a.id]}
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
          const nm = {};
          saved.forEach((s) => {
            if (s.note) nm[s.contact_id] = s.note;
          });
          setNotesMap(nm);
        }}
      />
    </div>
  );
}
