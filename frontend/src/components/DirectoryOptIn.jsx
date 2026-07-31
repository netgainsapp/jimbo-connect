import { useCallback, useEffect, useState } from "react";
import { Globe2 } from "lucide-react";

import { directoryApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";

/**
 * Per-event opt in to the cross-event directory.
 *
 * One switch per event rather than one per person, because attending a client's
 * conference and attending a neighbourhood meetup are not the same decision.
 * Off by default, and the copy says plainly what turning it on does, since this
 * is the only place in the product where someone becomes visible to people they
 * have never shared a room with.
 */
export default function DirectoryOptIn({ eventId }) {
  const [on, setOn] = useState(null);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const { discoverable } = await directoryApi.getOptIn(eventId);
      setOn(Boolean(discoverable));
    } catch {
      // A host who never joined their own event has no listing to manage, and
      // there is nothing useful to say about that on the event page.
      setOn(null);
    }
  }, [eventId]);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async () => {
    const next = !on;
    setSaving(true);
    // Optimistic, with a rollback: the switch should feel immediate, but it
    // must never end up showing "listed" when the server refused.
    setOn(next);
    try {
      await directoryApi.setOptIn(eventId, next);
      toast.show(
        next
          ? "You are now listed in the directory"
          : "You are no longer listed in the directory"
      );
    } catch (e) {
      setOn(!next);
      toast.show(e?.message || "Could not change that setting", "error");
    } finally {
      setSaving(false);
    }
  };

  if (on === null) return null;

  return (
    <div className="mb-6 rounded-card border border-border-default bg-white p-4 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-sm font-semibold text-text-primary">
            <Globe2 className="h-4 w-4" />
            Cross event directory
          </p>
          <p className="mt-1 text-sm text-text-secondary">
            {on
              ? "You are listed. People from other events can find your profile and message you. Your email address is never shown."
              : "You are not listed. Turn this on to let people from other events find your profile and message you. Your email address is never shown."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="List me in the cross event directory"
          onClick={toggle}
          disabled={saving}
          className={`relative h-6 w-11 shrink-0 rounded-pill transition disabled:opacity-50 ${
            on ? "bg-primary" : "bg-border-default"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-pill bg-white transition-all ${
              on ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      </div>
    </div>
  );
}
