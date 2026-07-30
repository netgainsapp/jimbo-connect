// Display helpers for the agenda builder. These intentionally mirror
// backend/agenda/docx.py so the live preview matches the downloaded document.
// Dates and times are treated as wall clock at the venue: an agenda is local to
// its room, so nothing here converts through a timezone.

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const DAYS = [
  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
];

/** "2026-08-01" -> "Saturday, August 1, 2026".
 *  Parsed by hand rather than with `new Date(value)`, which reads a bare
 *  yyyy-mm-dd as UTC midnight and so renders the previous day for anyone west
 *  of Greenwich. */
export function formatAgendaDate(value, { withWeekday = true } = {}) {
  if (!value) return "";
  const [y, m, d] = value.split("-").map(Number);
  if (!y || !m || !d) return "";
  const local = new Date(y, m - 1, d);
  const stem = `${MONTHS[m - 1]} ${d}, ${y}`;
  return withWeekday ? `${DAYS[local.getDay()]}, ${stem}` : stem;
}

/** "09:00" -> "9:00 AM" */
export function formatAgendaTime(value) {
  if (!value) return "";
  const hour = Number(value.slice(0, 2));
  const minute = value.slice(3, 5);
  if (Number.isNaN(hour)) return "";
  const suffix = hour < 12 ? "AM" : "PM";
  return `${hour % 12 || 12}:${minute} ${suffix}`;
}

export function formatAgendaTimeRange(start, end) {
  if (start && end) return `${formatAgendaTime(start)} to ${formatAgendaTime(end)}`;
  return formatAgendaTime(start) || formatAgendaTime(end);
}

/** Items grouped into [date, items] pairs, days chronological and sessions
 *  ordered by start time. Untimed sessions sort last so a placeholder never
 *  displaces a real one. Mirrors schema.group_by_day. */
export function groupByDay(items) {
  const days = new Map();
  for (const item of items) {
    const key = item.date || "";
    if (!days.has(key)) days.set(key, []);
    days.get(key).push(item);
  }
  return [...days.entries()]
    .sort(([a], [b]) => (a === "" ? 1 : b === "" ? -1 : a < b ? -1 : 1))
    .map(([day, list]) => [
      day,
      [...list].sort((x, y) => {
        if (!x.start_time && !y.start_time) return 0;
        if (!x.start_time) return 1;
        if (!y.start_time) return -1;
        return x.start_time < y.start_time ? -1 : x.start_time > y.start_time ? 1 : 0;
      }),
    ]);
}

export function dateRangeLine(agenda) {
  const { start_date: start, end_date: end } = agenda;
  if (start && end && end !== start) {
    return `${formatAgendaDate(start)} to ${formatAgendaDate(end)}`;
  }
  if (start) return formatAgendaDate(start);
  const days = [...new Set(agenda.items.map((i) => i.date).filter(Boolean))].sort();
  if (!days.length) return "";
  if (days.length === 1) return formatAgendaDate(days[0]);
  return `${formatAgendaDate(days[0])} to ${formatAgendaDate(days[days.length - 1])}`;
}

export function locationLine(agenda) {
  const parts = [agenda.venue_name, agenda.venue_address].filter(Boolean);
  return parts.length ? parts.join(", ") : agenda.virtual_url;
}
