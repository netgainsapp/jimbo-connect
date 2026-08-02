import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, ArrowRight, Upload, Users } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { parsePaste, suggestEventName } from "../lib/parseAttendeeCsv.js";
import { profileComplete } from "../lib/utils.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";

/**
 * Start from the roster you already have.
 *
 * The ordinary path put importing last: register, fill in your own job title,
 * create an event, open it, then import. Five steps and three gates between a
 * host and a spreadsheet they already had open. Someone holding a guest list
 * has already decided; this turns that file into the first step instead of the
 * last, and creates the event as a side effect of the upload.
 *
 * Reachable with an incomplete profile on purpose. Asking a host for their own
 * role and company before they can use the thing is friction at exactly the
 * wrong moment, and the profile is still required before they appear in a
 * directory themselves.
 */
export default function StartFromRoster() {
  const [text, setText] = useState("");
  const [name, setName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
  const [date, setDate] = useState("");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);
  const navigate = useNavigate();
  const toast = useToast();
  const { user, refresh } = useAuth();

  // The event page needs a complete profile, so sending a half set up host
  // straight there bounces them to setup with no explanation and no way back.
  // Do the valuable part first, then ask for their details with the event as
  // the destination, so finishing the form lands them exactly where they meant
  // to be.
  const afterImport = (eventId) =>
    profileComplete(user?.profile)
      ? `/events/${eventId}`
      : `/profile/setup?next=${encodeURIComponent(`/events/${eventId}`)}`;

  const parsed = useMemo(() => parsePaste(text), [text]);
  const suggested = useMemo(() => suggestEventName(text), [text]);

  // The file usually names the event. Fill it in, but stop the moment the host
  // types their own, so we never overwrite what they wrote.
  const effectiveName = nameTouched ? name : name || suggested;

  const readFile = (file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ""));
    reader.readAsText(file);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (parsed.rows.length === 0) {
      toast.show("Add a guest list first", "error");
      return;
    }
    if (!effectiveName.trim() || !date) {
      toast.show("Your event needs a name and a date", "error");
      return;
    }
    setBusy(true);
    try {
      const ev = await eventsApi.create({
        name: effectiveName.trim(),
        date: new Date(date).toISOString(),
        location: location.trim(),
      });
      // The event has to exist before anyone can be attached to it, so a
      // failure here leaves a real event with no guests rather than nothing.
      // That is recoverable from the event page; the reverse would not be.
      try {
        await eventsApi.importAttendees(ev.id, parsed.rows);
      } catch (importErr) {
        toast.show(
          `${ev.name} was created, but the guest list did not import: ${importErr.message}`,
          "error"
        );
        navigate(afterImport(ev.id));
        return;
      }
      await refresh();
      toast.show(
        profileComplete(user?.profile)
          ? `${ev.name} is ready with ${parsed.rows.length} guests invited.`
          : `${parsed.rows.length} guests invited. Add your own details so they know who is hosting.`
      );
      navigate(afterImport(ev.id));
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">
        Start with your guest list
      </h1>
      <p className="text-sm text-text-secondary mb-8">
        Upload the list you already have and we will create the event, invite
        everyone, and open the directory. An Eventbrite attendee export works as
        it comes.
      </p>

      <form onSubmit={submit} className="card p-6 flex flex-col gap-5">
        <div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="inline-flex items-center gap-2 rounded-card border border-border-default px-3 py-2 text-sm font-semibold text-text-primary hover:bg-bg-secondary"
            >
              <Upload className="h-4 w-4" /> Upload CSV
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.tsv,.txt,text/csv"
              className="hidden"
              onChange={(e) => readFile(e.target.files?.[0])}
            />
            <span className="text-xs text-text-muted">or paste below</span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={7}
            placeholder={"email,name,company\nava@acme.co,Ava Reynolds,Acme"}
            className="mt-3 w-full rounded-card border border-border-default p-3 font-mono text-sm"
          />
          <div aria-live="polite">
            {parsed.rows.length > 0 && (
              <p className="mt-2 flex items-center gap-2 text-sm font-semibold text-text-primary">
                <Users className="h-4 w-4" />
                {parsed.rows.length} guest{parsed.rows.length === 1 ? "" : "s"}{" "}
                ready
              </p>
            )}
            {parsed.errors.length > 0 && (
              <div className="mt-2 rounded-card bg-amber-50 p-3 text-sm text-amber-900">
                <p className="flex items-center gap-2 font-semibold">
                  <AlertCircle className="h-4 w-4" />
                  {parsed.errors.length} row
                  {parsed.errors.length === 1 ? "" : "s"} will be skipped
                </p>
                <ul className="mt-1 list-inside list-disc">
                  {parsed.errors.slice(0, 5).map((er, i) => (
                    <li key={i}>
                      Line {er.line}: {er.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label htmlFor="ev-name" className="label">
              Event name *
            </label>
            <input
              id="ev-name"
              className="input"
              value={effectiveName}
              onChange={(e) => {
                setNameTouched(true);
                setName(e.target.value);
              }}
              placeholder="Denver Founders Dinner"
            />
            {!nameTouched && suggested && (
              <p className="mt-1 text-xs text-text-muted">
                Taken from your file. Change it if it is wrong.
              </p>
            )}
          </div>
          <div>
            <label htmlFor="ev-date" className="label">
              Date *
            </label>
            <input
              id="ev-date"
              type="datetime-local"
              className="input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="ev-loc" className="label">
              Location
            </label>
            <input
              id="ev-loc"
              className="input"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Denver, CO"
            />
          </div>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-text-muted">
            Everyone on the list gets an invitation with their own sign in link.
          </span>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? "Setting up…" : "Create event and invite"}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
