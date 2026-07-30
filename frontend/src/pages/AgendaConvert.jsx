import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, CalendarPlus, Loader2 } from "lucide-react";

import {
  dateRangeLine,
  groupByDay,
  locationLine,
} from "../components/agenda/format.js";
import { useAgendaDraft } from "../hooks/useAgendaDraft.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { agendaApi, billingApi } from "../lib/api.js";

/**
 * The confirm step between a finished agenda and a real event.
 *
 * Deliberately not automatic. On the free plan an event is a limited resource,
 * and silently spending someone's only one as a side effect of signing up is a
 * bad surprise. They see exactly what is about to be created first.
 */
export default function AgendaConvert() {
  const { agenda } = useAgendaDraft();
  const [creating, setCreating] = useState(false);
  const [limits, setLimits] = useState(null);
  const navigate = useNavigate();
  const toast = useToast();

  useEffect(() => {
    billingApi.status().then(setLimits).catch(() => setLimits(null));
  }, []);

  const dayCount = useMemo(() => groupByDay(agenda.items).length, [agenda.items]);
  const atLimit =
    limits &&
    limits.event_limit !== null &&
    limits.events_hosted >= limits.event_limit;

  const hasAgenda = agenda.event_name || agenda.items.length > 0;

  const create = async () => {
    if (!agenda.id) {
      toast.show("Your agenda is still saving. Try again in a moment.", "error");
      return;
    }
    setCreating(true);
    try {
      const event = await agendaApi.convert(agenda.id);
      navigate(`/events/${event.id}?fromAgenda=1`, { replace: true });
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setCreating(false);
    }
  };

  if (!hasAgenda) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-16 text-center">
        <h1 className="text-xl font-bold text-text-primary">
          There is no agenda to turn into an event yet
        </h1>
        <Link
          to="/agenda/new"
          className="mt-5 inline-flex rounded-card bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          Build an agenda
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold text-text-primary">
        Create your event
      </h1>
      <p className="mt-2 text-sm text-text-secondary">
        Here is what we will set up from your agenda. Your attendees get a
        private directory so they can find each other after the event.
      </p>

      <section className="mt-6 rounded-card border border-border-default bg-white p-5 shadow-card">
        <dl className="space-y-3 text-sm">
          <Row label="Event name" value={agenda.event_name || "Untitled event"} />
          <Row label="When" value={dateRangeLine(agenda) || "No date set"} />
          <Row label="Where" value={locationLine(agenda) || "Not set"} />
          <Row
            label="Agenda"
            value={`${agenda.items.length} session${
              agenda.items.length === 1 ? "" : "s"
            } across ${dayCount} day${dayCount === 1 ? "" : "s"}`}
          />
          {agenda.organizer_name && (
            <Row label="Organizer" value={agenda.organizer_name} />
          )}
        </dl>
        <p className="mt-4 border-t border-border-default pt-3 text-xs text-text-muted">
          Your full agenda stays attached, and you can keep editing it after the
          event exists.
        </p>
      </section>

      {atLimit && (
        <div className="mt-5 flex gap-3 rounded-card border border-amber-300 bg-amber-50 p-4">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" />
          <div className="text-sm">
            <p className="font-semibold text-amber-900">
              You are at your plan limit
            </p>
            <p className="mt-1 text-amber-800">
              Your {limits.plan} plan includes {limits.event_limit} event
              {limits.event_limit === 1 ? "" : "s"} and you already host{" "}
              {limits.events_hosted}. Your agenda is safe either way, and you can
              still download the Word file.
            </p>
            <Link
              to="/upgrade"
              className="mt-2 inline-block font-semibold text-amber-900 underline"
            >
              See plans
            </Link>
          </div>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={create}
          disabled={creating || atLimit}
          className="inline-flex items-center gap-2 rounded-card bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {creating ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <CalendarPlus size={16} />
          )}
          {creating ? "Creating your event" : "Create Your Event"}
        </button>
        <Link
          to="/agenda/new"
          className="rounded-card border border-border-default px-5 py-2.5 text-sm font-semibold text-text-secondary hover:bg-bg-secondary"
        >
          Back to the agenda
        </Link>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex gap-4">
      <dt className="w-28 shrink-0 text-text-muted">{label}</dt>
      <dd className="min-w-0 flex-1 font-medium text-text-primary">{value}</dd>
    </div>
  );
}
