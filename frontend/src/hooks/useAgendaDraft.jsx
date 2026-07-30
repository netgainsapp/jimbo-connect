import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// Phase 1 keeps the whole draft on the device. An anonymous visitor never
// creates a database row, so there is nothing to orphan and nothing to clean
// up, and the draft survives a refresh (and later, a signup) for free.
const STORAGE_KEY = "intro-connect:agenda-draft:v1";
const SAVE_DEBOUNCE_MS = 400;

export const EMPTY_AGENDA = {
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

export function useAgendaDraft() {
  const [agenda, setAgenda] = useState(load);
  const [savedAt, setSavedAt] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(agenda));
        setSavedAt(new Date());
      } catch {
        // Private browsing or a full quota. The tool still works in memory;
        // failing loudly here would be worse than losing autosave.
      }
    }, SAVE_DEBOUNCE_MS);
    return () => timer.current && clearTimeout(timer.current);
  }, [agenda]);

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

  const reset = useCallback(() => {
    setAgenda({ ...EMPTY_AGENDA });
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
    reset,
    savedAt,
    warnings,
  };
}
