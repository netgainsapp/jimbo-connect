import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Globe2, Search, Info } from "lucide-react";

import { directoryApi, contactsApi } from "../lib/api.js";
import AttendeeCard from "../components/AttendeeCard.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";
import { useToast } from "../hooks/useToast.jsx";

/**
 * People from other events who chose to be findable.
 *
 * The only screen in the product that shows someone you were never in a room
 * with, so it states the rules rather than hiding them: entries are opt in per
 * event, no email addresses appear, and messaging needs both sides listed.
 *
 * Reuses AttendeeCard so a person looks the same here as on an event page. That
 * component reads `profile` only, which is exactly what the directory API
 * returns; no email reaches this screen to be rendered by accident.
 */
export default function CrossEventDirectory() {
  const [people, setPeople] = useState([]);
  const [listed, setListed] = useState(true);
  const [blocked, setBlocked] = useState(false);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [industry, setIndustry] = useState("all");
  const [savedSet, setSavedSet] = useState(new Set());
  const [active, setActive] = useState(null);
  const toast = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [res, saved] = await Promise.all([
        directoryApi.browse(),
        contactsApi.list().catch(() => []),
      ]);
      setPeople(res.people || []);
      setListed(Boolean(res.i_am_listed));
      setSavedSet(new Set((saved || []).map((s) => s.contact_id)));
    } catch (e) {
      // 403 is the "you have not attended anything yet" case, which is a
      // different screen rather than an error.
      setBlocked(true);
      if (!/directory is for people/i.test(e?.message || "")) {
        toast.show(e?.message || "Could not load the directory", "error");
      }
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const industries = useMemo(() => {
    const set = new Set(
      people.map((p) => p.profile?.industry).filter(Boolean)
    );
    return ["all", ...[...set].sort()];
  }, [people]);

  // Filtering client side over an already-capped list keeps typing responsive.
  // The server applies the same rules for anyone calling the API directly.
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return people.filter((p) => {
      const prof = p.profile || {};
      if (industry !== "all" && prof.industry !== industry) return false;
      if (!needle) return true;
      return [prof.name, prof.role, prof.company, prof.industry, prof.looking_for]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [people, query, industry]);

  const toggleSave = async (person) => {
    const isSaved = savedSet.has(person.id);
    try {
      if (isSaved) {
        await contactsApi.remove(person.id);
        setSavedSet((prev) => {
          const next = new Set(prev);
          next.delete(person.id);
          return next;
        });
        toast.show("Contact removed");
      } else {
        await contactsApi.save(person.id);
        setSavedSet((prev) => new Set(prev).add(person.id));
        toast.show("Contact saved");
      }
    } catch (e) {
      toast.show(e?.message || "Could not update that contact", "error");
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-6 text-text-muted sm:px-6 sm:py-10">
        Loading...
      </div>
    );
  }

  if (blocked) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <h1 className="text-2xl font-bold text-text-primary">Directory</h1>
        <div className="mt-4 rounded-card border border-border-default bg-white p-6 shadow-card">
          <p className="text-sm text-text-secondary">
            The directory is for people who have been to an event. Join one and
            it opens up.
          </p>
          <Link
            to="/events"
            className="mt-3 inline-block rounded-card bg-primary px-4 py-1.5 text-sm font-bold text-white"
          >
            My events
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
      <h1 className="flex items-center gap-2 text-2xl font-bold text-text-primary">
        <Globe2 className="h-6 w-6" /> Directory
      </h1>
      <p className="mt-1 text-sm text-text-secondary">
        People from across every event who chose to be findable. Email addresses
        are never shown here.
      </p>

      {!listed && (
        <div className="mt-4 flex items-start gap-2 rounded-card border border-border-default bg-bg-secondary p-4">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
          <p className="text-sm text-text-secondary">
            You are not listed yet, so you cannot message people here and they
            cannot find you. Open one of your events and turn on the cross event
            directory to join in.
          </p>
        </div>
      )}

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, role, company or what they are looking for"
            aria-label="Search the directory"
            className="w-full rounded-card border border-border-default py-2 pl-9 pr-3 text-sm"
          />
        </div>
        <select
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          aria-label="Filter by industry"
          className="rounded-card border border-border-default px-3 py-2 text-sm"
        >
          {industries.map((i) => (
            <option key={i} value={i}>
              {i === "all" ? "All industries" : i}
            </option>
          ))}
        </select>
      </div>

      <p className="mt-4 text-sm text-text-muted">
        {shown.length} {shown.length === 1 ? "person" : "people"}
      </p>

      {shown.length === 0 ? (
        <div className="mt-3 rounded-card border border-border-default bg-white p-6 text-sm text-text-secondary shadow-card">
          Nobody matches that yet. The directory fills up as attendees opt in
          from their own events.
        </div>
      ) : (
        <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shown.map((person) => (
            <AttendeeCard
              key={person.id}
              attendee={person}
              isSaved={savedSet.has(person.id)}
              onToggleSave={() => toggleSave(person)}
              onOpen={() => setActive(person)}
            />
          ))}
        </div>
      )}

      {/* The modal owns messaging and note editing itself; it only reports back
          when the saved state changed so this list can restate it. */}
      <AttendeeProfileModal
        attendee={active}
        open={Boolean(active)}
        onClose={() => setActive(null)}
        onSavedChange={async () => {
          const saved = await contactsApi.list().catch(() => []);
          setSavedSet(new Set((saved || []).map((s) => s.contact_id)));
        }}
      />
    </div>
  );
}
