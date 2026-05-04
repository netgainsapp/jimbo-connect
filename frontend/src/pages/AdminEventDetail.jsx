import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Calendar,
  MapPin,
  Users,
  Copy,
  Mail,
  Plus,
  UserPlus,
  LayoutGrid,
  List,
  X,
} from "lucide-react";
import { eventsApi, sponsorsApi, adminApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { copyToClipboard, formatDate } from "../lib/utils.js";
import Avatar from "../components/Avatar.jsx";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";
import SponsorTile from "../components/SponsorTile.jsx";

export default function AdminEventDetail() {
  const { id } = useParams();
  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [sponsors, setSponsors] = useState([]);
  const [sponsorUrl, setSponsorUrl] = useState("");
  const [addingSponsor, setAddingSponsor] = useState(false);
  const [attendeeEmail, setAttendeeEmail] = useState("");
  const [addingAttendee, setAddingAttendee] = useState(false);
  const [attendeeView, setAttendeeView] = useState("tiles"); // "tiles" | "list"
  const [attendeeSort, setAttendeeSort] = useState("name"); // "name" | "company" | "email"
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);
  const toast = useToast();

  useEffect(() => {
    Promise.all([
      eventsApi.get(id),
      eventsApi.attendees(id),
      sponsorsApi.list(id),
    ])
      .then(([ev, list, sp]) => {
        setEvent(ev);
        setAttendees(list);
        setSponsors(sp);
      })
      .catch((e) => toast.show(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const addSponsor = async (e) => {
    e.preventDefault();
    if (!sponsorUrl.trim()) return;
    setAddingSponsor(true);
    try {
      const sp = await sponsorsApi.create(id, { url: sponsorUrl.trim() });
      setSponsors((prev) => [...prev, sp]);
      setSponsorUrl("");
      toast.show("Sponsor added");
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setAddingSponsor(false);
    }
  };

  const toggleSponsorActive = async (sp, active) => {
    try {
      const updated = await sponsorsApi.update(id, sp.id, { active });
      setSponsors((prev) => prev.map((x) => (x.id === sp.id ? updated : x)));
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  const refreshSponsor = async (sp) => {
    try {
      const updated = await sponsorsApi.refresh(id, sp.id);
      setSponsors((prev) => prev.map((x) => (x.id === sp.id ? updated : x)));
      toast.show("Sponsor refreshed");
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  const deleteSponsor = async (sp) => {
    if (!confirm(`Remove sponsor "${sp.title || sp.url}"?`)) return;
    try {
      await sponsorsApi.remove(id, sp.id);
      setSponsors((prev) => prev.filter((x) => x.id !== sp.id));
      toast.show("Sponsor removed");
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  const removeAttendee = async (attendee) => {
    const name = attendee.profile?.name || attendee.email;
    if (!confirm(`Remove ${name} from this event? Their account stays.`)) return;
    try {
      await eventsApi.removeAttendee(id, attendee.id);
      setAttendees((prev) => prev.filter((a) => a.id !== attendee.id));
      toast.show("Removed from event");
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  const addAttendeeByEmail = async (e) => {
    e.preventDefault();
    const email = attendeeEmail.trim().toLowerCase();
    if (!email || !email.includes("@")) {
      toast.show("Enter a valid email", "error");
      return;
    }
    setAddingAttendee(true);
    try {
      const res = await adminApi.bulkImport([{ email }], id, null);
      const refreshed = await eventsApi.attendees(id);
      setAttendees(refreshed);
      setAttendeeEmail("");
      if (res.created > 0) {
        const acct = res.accounts?.[0];
        if (acct?.password) {
          await navigator.clipboard?.writeText(
            `Email: ${acct.email}\nPassword: ${acct.password}\nLogin: ${window.location.origin}`
          );
          toast.show(
            `Created new account — credentials copied to clipboard`
          );
        } else {
          toast.show("New account created and added to event");
        }
      } else if (res.added_to_event > 0) {
        toast.show("Existing user added to event");
      } else {
        toast.show("Already in this event");
      }
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setAddingAttendee(false);
    }
  };

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

  const mailtoEveryone = attendees.length
    ? `mailto:?bcc=${encodeURIComponent(
        attendees.map((a) => a.email).join(",")
      )}&subject=${encodeURIComponent(`You're invited to ${event.name}`)}&body=${encodeURIComponent(
        `Hi,\n\nYou're invited to ${event.name}` +
          (event.location ? ` in ${event.location}` : "") +
          ` on ${formatDate(event.date)}.\n\n` +
          `Log in at ${window.location.origin} to access the attendee directory and save contacts.\n\nJoin code: ${event.join_code}\n`
      )}`
    : "";

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="card p-5 mb-6">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="min-w-0 flex-1">
            <Link
              to="/admin/events"
              className="inline-flex items-center gap-1 text-xs text-text-secondary hover:text-primary"
            >
              <ArrowLeft className="w-3 h-3" /> All events
            </Link>
            <h1 className="text-xl font-bold text-text-primary mt-1 leading-tight">
              {event.name}
            </h1>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-sm text-text-secondary mt-1">
              <span className="inline-flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" /> {formatDate(event.date)}
              </span>
              {event.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" /> {event.location}
                </span>
              )}
              <span className="inline-flex items-center gap-1">
                <Users className="w-3.5 h-3.5" /> {event.attendee_count}
              </span>
              {event.industry_tags?.map((t) => (
                <span
                  key={t}
                  className="text-xs bg-bg-secondary text-text-secondary px-2 py-0.5 rounded-pill"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <button
              onClick={copyCode}
              className="font-mono text-xs bg-bg-secondary px-2.5 py-1.5 rounded-card text-text-primary hover:bg-border-default"
              title="Copy code"
            >
              {event.join_code}
            </button>
            <button onClick={copyLink} className="btn-ghost" title="Copy join link">
              <Copy className="w-4 h-4" /> Link
            </button>
            {mailtoEveryone && (
              <a className="btn-outline" href={mailtoEveryone}>
                <Mail className="w-4 h-4" /> Email all
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-end justify-between gap-2 mb-3 flex-wrap">
        <h2 className="font-bold text-text-primary text-lg">Sponsors</h2>
        <form
          onSubmit={addSponsor}
          className="flex gap-2 w-full sm:w-auto sm:min-w-[420px]"
        >
          <input
            className="input flex-1"
            placeholder="Paste a sponsor URL — we'll build the tile"
            value={sponsorUrl}
            onChange={(e) => setSponsorUrl(e.target.value)}
          />
          <button type="submit" className="btn-primary" disabled={addingSponsor}>
            <Plus className="w-4 h-4" />
            {addingSponsor ? "…" : "Add"}
          </button>
        </form>
      </div>
      {sponsors.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {sponsors.map((sp) => (
            <SponsorTile
              key={sp.id}
              sponsor={sp}
              isAdmin
              onRefresh={refreshSponsor}
              onToggleActive={toggleSponsorActive}
              onDelete={deleteSponsor}
            />
          ))}
        </div>
      )}

      <div className="flex items-end justify-between gap-2 mb-3 flex-wrap">
        <h2 className="font-bold text-text-primary text-lg">Attendees</h2>
        <form
          onSubmit={addAttendeeByEmail}
          className="flex gap-2 w-full sm:w-auto sm:min-w-[420px]"
        >
          <input
            type="email"
            className="input flex-1"
            placeholder="Add attendee by email"
            value={attendeeEmail}
            onChange={(e) => setAttendeeEmail(e.target.value)}
          />
          <button type="submit" className="btn-primary" disabled={addingAttendee}>
            <UserPlus className="w-4 h-4" />
            {addingAttendee ? "…" : "Add"}
          </button>
        </form>
      </div>
      {attendees.length > 0 && (
        <div className="flex items-center justify-between gap-2 mb-3 text-sm">
          <div className="flex items-center gap-2 text-text-secondary">
            <span>Sort by</span>
            <select
              className="border border-border-default rounded-card px-2 py-1 text-text-primary bg-white"
              value={attendeeSort}
              onChange={(e) => setAttendeeSort(e.target.value)}
            >
              <option value="name">Name</option>
              <option value="company">Company</option>
              <option value="email">Email</option>
            </select>
          </div>
          <div className="inline-flex border border-border-default rounded-pill overflow-hidden">
            <button
              type="button"
              onClick={() => setAttendeeView("list")}
              className={`px-3 py-1 inline-flex items-center gap-1 text-xs font-semibold ${
                attendeeView === "list"
                  ? "bg-primary text-white"
                  : "text-text-secondary hover:bg-bg-secondary"
              }`}
              title="List view"
            >
              <List className="w-3.5 h-3.5" /> List
            </button>
            <button
              type="button"
              onClick={() => setAttendeeView("tiles")}
              className={`px-3 py-1 inline-flex items-center gap-1 text-xs font-semibold ${
                attendeeView === "tiles"
                  ? "bg-primary text-white"
                  : "text-text-secondary hover:bg-bg-secondary"
              }`}
              title="Tile view"
            >
              <LayoutGrid className="w-3.5 h-3.5" /> Tiles
            </button>
          </div>
        </div>
      )}
      {attendees.length === 0 ? (
        <div className="card p-8 text-center text-text-secondary">
          No one has joined this event yet. Share the join link.
        </div>
      ) : (
        (() => {
          const sorted = [...attendees].sort((a, b) => {
            const pa = a.profile || {};
            const pb = b.profile || {};
            const va =
              (attendeeSort === "company"
                ? pa.company
                : attendeeSort === "email"
                ? a.email
                : pa.name) || "";
            const vb =
              (attendeeSort === "company"
                ? pb.company
                : attendeeSort === "email"
                ? b.email
                : pb.name) || "";
            return va.localeCompare(vb);
          });
          if (attendeeView === "tiles") {
            return (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {sorted.map((a) => (
                  <div key={a.id} className="relative group">
                    <AttendeeCard attendee={a} hideActions onOpen={setActive} />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeAttendee(a);
                      }}
                      className="absolute top-2 right-2 p-1.5 rounded-full bg-white border border-border-default text-text-secondary hover:bg-red-50 hover:text-red-500 hover:border-red-200 opacity-0 group-hover:opacity-100 transition"
                      title="Remove from event"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            );
          }
          return (
            <div className="card divide-y divide-border-default">
              {sorted.map((a) => {
                const p = a.profile || {};
                return (
                  <div
                    key={a.id}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-bg-secondary transition group"
                  >
                    <button
                      type="button"
                      onClick={() => setActive(a)}
                      className="flex-1 flex items-center gap-4 text-left min-w-0"
                    >
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
                    </button>
                    <button
                      onClick={() => removeAttendee(a)}
                      className="p-1.5 rounded-full text-text-muted hover:bg-red-50 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
                      title="Remove from event"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          );
        })()
      )}

      <AttendeeProfileModal
        attendee={active}
        open={Boolean(active)}
        onClose={() => setActive(null)}
      />
    </div>
  );
}
