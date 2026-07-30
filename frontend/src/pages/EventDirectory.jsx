import { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { AlertTriangle, ArrowLeft, Calendar, CalendarPlus, MapPin, Search, Users, ChevronDown } from "lucide-react";
import { eventsApi, contactsApi, sponsorsApi, agendaApi, downloadEventIcs } from "../lib/api.js";
import EventAgenda from "../components/agenda/EventAgenda.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { formatDateTime } from "../lib/utils.js";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";
import HostCta from "../components/HostCta.jsx";
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
  const [agenda, setAgenda] = useState(null);

  const addToCalendar = async () => {
    try {
      const { blob, filename } = await downloadEventIcs(id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.show(e.message, "error");
    }
  };
  const [savedSet, setSavedSet] = useState(new Set());
  const [notesMap, setNotesMap] = useState({});
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState("all");
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  // Attendee to host loop: the CTA only makes sense for guests who host nothing.
  const [hostsNothing, setHostsNothing] = useState(false);

  const isAll = id === "all";

  const load = async () => {
    setLoading(true);
    try {
      if (isAll) {
        const [list, saved, mine, hosted] = await Promise.all([
          eventsApi.allMyAttendees(),
          contactsApi.list(),
          eventsApi.myEvents().catch(() => []),
          eventsApi.myHostedEvents().catch(() => []),
        ]);
        setHostsNothing(hosted.length === 0);
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
        const [ev, list, saved, sp, mine, hosted, ag] = await Promise.all([
          eventsApi.get(id),
          eventsApi.attendees(id),
          contactsApi.list(),
          sponsorsApi.list(id).catch(() => []),
          eventsApi.myEvents().catch(() => []),
          eventsApi.myHostedEvents().catch(() => []),
          // 404 is the normal answer for an event with no agenda, which is
          // most of them. Swallow it rather than failing the whole page.
          agendaApi.forEvent(id).catch(() => null),
        ]);
        setAgenda(ag);
        setHostsNothing(hosted.length === 0);
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
    // Reset filters when switching cohorts so a stale industry/search from the
    // previous directory doesn't silently hide everyone in the new one.
    setIndustry("all");
    setQuery("");
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

  // Host branding (Pro): accent recolors this page's primary actions via CSS
  // variables scoped to the container; the logo sits above the cohort header.
  const hb = !isAll ? event?.host_branding : null;
  const brandStyle = hb?.accent_dark
    ? { "--host-accent": hb.accent, "--host-accent-dark": hb.accent_dark }
    : undefined;

  return (
    <div
      className={`max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10 ${brandStyle ? "host-branded" : ""}`}
      style={brandStyle}
    >
      <div className="mb-6">
        {hb?.logo_url && (
          <div className="flex items-center gap-2 mb-3">
            <img
              src={hb.logo_url}
              alt="Event host logo"
              className="h-10 max-w-[200px] object-contain"
            />
            <span className="text-xs text-text-muted font-semibold">
              via Intro Connect
            </span>
          </div>
        )}
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
                <Calendar className="w-4 h-4" /> {formatDateTime(event.date)}
              </span>
              {event.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" /> {event.location}
                </span>
              )}
              <button
                type="button"
                onClick={addToCalendar}
                className="inline-flex items-center gap-1.5 rounded-pill px-2 py-0.5 font-medium text-primary transition hover:bg-primary/10"
                title="Download a calendar file for this event"
              >
                <CalendarPlus className="w-4 h-4" /> Add to calendar
              </button>
              <span className="inline-flex items-center gap-1.5">
                <Users className="w-4 h-4" />
                {/* attendee_limit is only sent to whoever manages the event, so
                    its presence is what marks the host view. An attendee just
                    sees the count. */}
                {event.attendee_limit
                  ? `${event.attendee_count} of ${event.attendee_limit} attendees`
                  : `${event.attendee_count} attendees`}
              </span>
            </div>
          )
        )}
      </div>

      {/* Warn the host as the cap approaches rather than when a guest is
          turned away at the door. Ten percent of headroom, or three seats,
          whichever is larger, so it is useful on a 50 cap and on a 2000 one. */}
      {event.attendee_limit &&
        event.attendee_count >=
          event.attendee_limit - Math.max(3, Math.round(event.attendee_limit * 0.1)) && (
          <div className="mb-6 flex gap-3 rounded-card border border-amber-300 bg-amber-50 p-4">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
            <p className="text-sm text-amber-800">
              {event.attendee_count >= event.attendee_limit ? (
                <>
                  <span className="font-semibold text-amber-900">
                    This event is full.
                  </span>{" "}
                  New guests cannot join until you upgrade.
                </>
              ) : (
                <>
                  <span className="font-semibold text-amber-900">
                    Nearly full.
                  </span>{" "}
                  {event.attendee_limit - event.attendee_count} of{" "}
                  {event.attendee_limit} places left.
                </>
              )}{" "}
              <Link to="/upgrade" className="font-semibold underline">
                See plans
              </Link>
            </p>
          </div>
        )}

      {/* Above the sponsors and the attendee grid: on the day, the schedule is
          what someone opens this page to find. */}
      <EventAgenda agenda={agenda} />

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
            aria-label="Search attendees"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          className="input sm:w-56"
          aria-label="Filter by industry"
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

      {!loading && hostsNothing && <HostCta className="mt-8" />}

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
