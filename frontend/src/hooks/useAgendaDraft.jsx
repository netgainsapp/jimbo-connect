import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { byStartTime } from "../components/agenda/format.js";
import { agendaApi } from "../lib/api.js";
import { useAuth } from "./useAuth.jsx";

// Phase 1 keeps the whole draft on the device. An anonymous visitor never
// creates a database row, so there is nothing to orphan and nothing to clean
// up, and the draft survives a refresh (and later, a signup) for free.
const STORAGE_KEY = "intro-connect:agenda-draft:v1";
const SAVE_DEBOUNCE_MS = 400;

export const EMPTY_AGENDA = {
  // Server id once the agenda is saved to an account. Null while the draft
  // lives only in this browser.
  id: null,
  event_name: "",
  description: "",
  start_date: "",
  end_date: "",
  start_time: "",
  end_time: "",
  venue_name: "",
  venue_address: "",
  virtual_url: "",
  organizer_name: "",
  organizer_company: "",
  organizer_email: "",
  event_website: "",
  logo: null,
  items: [],
};

function newId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return `i${Date.now()}${Math.random().toString(16).slice(2)}`;
}

export function blankItem(date = "") {
  return {
    id: newId(),
    date,
    start_time: "",
    end_time: "",
    title: "",
    description: "",
    location: "",
    speaker: "",
    external_url: "",
    notes: "",
  };
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_AGENDA };
    const parsed = JSON.parse(raw);
    // Merge onto the current shape so a draft saved by an older build never
    // leaves a field undefined and turns an input into an uncontrolled one.
    return { ...EMPTY_AGENDA, ...parsed, items: (parsed.items || []).map((i) => ({ ...blankItem(), ...i })) };
  } catch {
    return { ...EMPTY_AGENDA };
  }
}

/** Sessions that overlap another session on the same day. Returns a Set of
 *  item ids. Per spec this is a warning only and never blocks anything: back
 *  to back tracks are a legitimate thing to schedule. */
export function overlappingIds(items) {
  const flagged = new Set();
  const byDay = {};
  for (const item of items) {
    if (!item.date || !item.start_time || !item.end_time) continue;
    (byDay[item.date] = byDay[item.date] || []).push(item);
  }
  for (const day of Object.values(byDay)) {
    for (let a = 0; a < day.length; a++) {
      for (let b = a + 1; b < day.length; b++) {
        const x = day[a];
        const y = day[b];
        if (x.start_time < y.end_time && y.start_time < x.end_time) {
          flagged.add(x.id);
          flagged.add(y.id);
        }
      }
    }
  }
  return flagged;
}

/** Item ids whose end time is not after their start time. */
export function invalidTimeIds(items) {
  return new Set(
    items
      .filter((i) => i.start_time && i.end_time && i.end_time <= i.start_time)
      .map((i) => i.id)
  );
}

/** Everything the API accepts. Empty date strings must become null, since the
 *  server models them as optional dates and "" is not one. The logo is
 *  deliberately excluded: autosave must not re-upload a megabyte of image on
 *  every keystroke, and an omitted logo means "leave it alone" server side. */
function toPayload(agenda, { includeLogo = false } = {}) {
  const { id, logo, ...rest } = agenda;
  const payload = {
    ...rest,
    start_date: agenda.start_date || null,
    end_date: agenda.end_date || null,
    items: agenda.items.map((i) => ({ ...i, date: i.date || null })),
  };
  if (includeLogo) payload.logo = logo ?? null;
  return payload;
}

export function useAgendaDraft() {
  const [agenda, setAgenda] = useState(load);
  const [savedAt, setSavedAt] = useState(null);
  const timer = useRef(null);
  const { user } = useAuth();

  // Which logo value we last persisted, so the logo is only sent when it has
  // actually changed rather than on every autosave.
  const syncedLogo = useRef(agenda.logo ?? null);
  const claiming = useRef(false);
  const hydrating = useRef(false);
  const hydrated = useRef(false);

  // Load the saved agenda back from the server.
  //
  // Without this the tool looks like it loses your work: claiming deletes the
  // local copy, so on the next page load there is nothing in localStorage and
  // nothing fetches what the server now owns. The builder came up empty and
  // /agenda/convert reported that there was no agenda at all, while the data
  // was sitting safely in the database the whole time.
  //
  // Only runs when there is nothing local worth keeping. A draft with content
  // and no id belongs to the claim effect below, and must not be overwritten
  // by whatever was saved previously.
  useEffect(() => {
    if (!user || agenda.id || hydrated.current || hydrating.current) return;
    if (agenda.event_name || agenda.items.length > 0) return;
    hydrating.current = true;
    agendaApi
      .list()
      .then(async (rows) => {
        if (rows && rows.length) {
          // Newest first from the server, so the most recently edited agenda
          // is the one an organizer expects to find waiting for them.
          const full = await agendaApi.get(rows[0].id);
          syncedLogo.current = full.logo ?? null;
          setAgenda({
            ...EMPTY_AGENDA,
            ...full,
            items: (full.items || []).map((i) => ({ ...blankItem(), ...i })),
          });
        }
        hydrated.current = true;
      })
      .catch(() => {
        // Leave it un-hydrated so a later render can retry rather than
        // stranding the organizer on an empty builder for good.
        hydrating.current = false;
      });
  }, [user, agenda]);

  // Claim a draft built before signing in. Runs once when a session appears
  // and the draft has no server id yet.
  useEffect(() => {
    if (!user || agenda.id || claiming.current) return;
    const hasContent = agenda.event_name || agenda.items.length > 0;
    if (!hasContent) return;
    claiming.current = true;
    agendaApi
      .create(toPayload(agenda, { includeLogo: true }))
      .then((saved) => {
        syncedLogo.current = agenda.logo ?? null;
        setAgenda((prev) => ({ ...prev, id: saved.id }));
        // Drop the local copy the moment the server owns it. Leaving it behind
        // would hand this draft to the next person who signs in on this
        // browser, which is a privacy bug, not just clutter.
        try {
          localStorage.removeItem(STORAGE_KEY);
        } catch {
          /* nothing to do */
        }
      })
      .catch(() => {
        // Stay local and keep working. A failed claim must never cost the
        // organizer their agenda.
        claiming.current = false;
      });
  }, [user, agenda]);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      // Signed in with a saved agenda: the server is the source of truth, and
      // nothing is mirrored locally so a shared browser leaks nothing.
      if (user && agenda.id) {
        const logoChanged = (agenda.logo ?? null) !== syncedLogo.current;
        agendaApi
          .update(agenda.id, toPayload(agenda, { includeLogo: logoChanged }))
          .then(() => {
            if (logoChanged) syncedLogo.current = agenda.logo ?? null;
            setSavedAt(new Date());
          })
          .catch(() => {
            /* transient; the next edit retries */
          });
        return;
      }
      if (user) return; // claim in flight; do not write a local copy
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(agenda));
        setSavedAt(new Date());
      } catch {
        // Private browsing or a full quota. The tool still works in memory;
        // failing loudly here would be worse than losing autosave.
      }
    }, SAVE_DEBOUNCE_MS);
    return () => timer.current && clearTimeout(timer.current);
  }, [agenda, user]);

  const setField = useCallback((name, value) => {
    setAgenda((prev) => ({ ...prev, [name]: value }));
  }, []);

  const addItem = useCallback((date) => {
    const item = blankItem(date || "");
    setAgenda((prev) => ({ ...prev, items: [...prev.items, item] }));
    return item.id;
  }, []);

  const updateItem = useCallback((id, patch) => {
    setAgenda((prev) => ({
      ...prev,
      items: prev.items.map((i) => (i.id === id ? { ...i, ...patch } : i)),
    }));
  }, []);

  const removeItem = useCallback((id) => {
    setAgenda((prev) => ({ ...prev, items: prev.items.filter((i) => i.id !== id) }));
  }, []);

  const duplicateItem = useCallback((id) => {
    setAgenda((prev) => {
      const index = prev.items.findIndex((i) => i.id === id);
      if (index === -1) return prev;
      const copy = { ...prev.items[index], id: newId() };
      const items = [...prev.items];
      items.splice(index + 1, 0, copy);
      return { ...prev, items };
    });
  }, []);

  /** Move an item one slot within its own day. Ordering inside a day is what
   *  the organizer actually cares about; days themselves stay chronological. */
  const moveItem = useCallback((id, direction) => {
    setAgenda((prev) => {
      const items = [...prev.items];
      const index = items.findIndex((i) => i.id === id);
      if (index === -1) return prev;
      const sameDay = items
        .map((item, at) => ({ item, at }))
        .filter(({ item }) => item.date === items[index].date);
      const position = sameDay.findIndex(({ item }) => item.id === id);
      const target = position + direction;
      if (target < 0 || target >= sameDay.length) return prev;
      const from = sameDay[position].at;
      const to = sameDay[target].at;
      [items[from], items[to]] = [items[to], items[from]];
      return { ...prev, items };
    });
  }, []);

  /** Helper: rewrite one day's items in place, leaving every other day's
   *  positions in the flat array untouched. Both drag reordering and the sort
   *  action need exactly this. */
  const rewriteDay = (items, day, transform) => {
    const slots = items.reduce((acc, item, index) => {
      if (item.date === day) acc.push(index);
      return acc;
    }, []);
    const next = transform(slots.map((index) => items[index]));
    slots.forEach((index, k) => {
      items[index] = next[k];
    });
    return items;
  };

  /** Drop `activeId` onto `overId`'s position. Reordering is scoped to a
   *  single day: dragging across day boundaries would silently change a
   *  session's date, which is a bigger edit than a drag should imply. */
  const reorderItem = useCallback((activeId, overId) => {
    setAgenda((prev) => {
      if (activeId === overId) return prev;
      const active = prev.items.find((i) => i.id === activeId);
      const over = prev.items.find((i) => i.id === overId);
      if (!active || !over || active.date !== over.date) return prev;
      const items = rewriteDay([...prev.items], active.date, (day) => {
        const from = day.findIndex((i) => i.id === activeId);
        const to = day.findIndex((i) => i.id === overId);
        const next = [...day];
        const [moved] = next.splice(from, 1);
        next.splice(to, 0, moved);
        return next;
      });
      return { ...prev, items };
    });
  }, []);

  /** Explicit "Sort by time" for one day. Deliberately an action the organizer
   *  takes rather than something that happens automatically, so a manual
   *  arrangement is never overwritten behind their back. */
  const sortDayByTime = useCallback((day) => {
    setAgenda((prev) => ({
      ...prev,
      items: rewriteDay([...prev.items], day, (list) => [...list].sort(byStartTime)),
    }));
  }, []);

  const reset = useCallback(() => {
    setAgenda({ ...EMPTY_AGENDA });
    syncedLogo.current = null;
    claiming.current = false;
    // Stay hydrated: a deliberate reset means "start a new one", not "go and
    // fetch the old one back".
    hydrated.current = true;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* nothing to do */
    }
  }, []);

  const warnings = useMemo(
    () => ({
      overlapping: overlappingIds(agenda.items),
      invalidTimes: invalidTimeIds(agenda.items),
    }),
    [agenda.items]
  );

  return {
    agenda,
    setField,
    addItem,
    updateItem,
    removeItem,
    duplicateItem,
    moveItem,
    reorderItem,
    sortDayByTime,
    reset,
    savedAt,
    warnings,
  };
}
