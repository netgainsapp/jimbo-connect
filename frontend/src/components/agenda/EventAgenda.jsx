import { CalendarDays } from "lucide-react";

import {
  formatAgendaDate,
  formatAgendaTimeRange,
  groupByDay,
} from "./format.js";

/**
 * The schedule, shown on the event page to everyone who can see the event.
 *
 * This is what makes the conversion CTA honest: it promises attendees can view
 * the agenda, and until this existed they could not. Uses the same grouping and
 * formatting helpers as the builder and the Word export, so all three agree
 * rather than drifting into three slightly different renderings of one thing.
 *
 * Private per-session notes never reach the client; the API strips them.
 */
export default function EventAgenda({ agenda }) {
  if (!agenda || !agenda.items?.length) return null;
  const groups = groupByDay(agenda.items);

  return (
    <section className="mb-6">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-text-muted">
        <CalendarDays className="h-3.5 w-3.5" /> Agenda
      </div>

      <div className="rounded-card border border-border-default bg-white p-5 shadow-card">
        {groups.map(([day, items], index) => (
          <div key={day || "undated"} className={index > 0 ? "mt-6" : ""}>
            <h3 className="mb-2 text-sm font-bold text-primary-hover">
              {day ? formatAgendaDate(day) : "Date not set"}
            </h3>
            <div className="divide-y divide-border-default border-y border-border-default">
              {items.map((item) => (
                <div key={item.id} className="flex gap-4 py-3">
                  <div className="w-32 shrink-0 text-xs font-semibold text-text-secondary">
                    {formatAgendaTimeRange(item.start_time, item.end_time) || "TBD"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-text-primary">
                      {item.title || "Untitled session"}
                    </p>
                    {(item.speaker || item.location) && (
                      <p className="mt-0.5 text-xs text-text-muted">
                        {[item.speaker && `Speaker: ${item.speaker}`, item.location]
                          .filter(Boolean)
                          .join(" | ")}
                      </p>
                    )}
                    {item.description && (
                      <p className="mt-1 whitespace-pre-line text-sm text-text-secondary">
                        {item.description}
                      </p>
                    )}
                    {item.external_url && (
                      <a
                        href={item.external_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1 inline-block break-all text-xs font-medium text-primary hover:underline"
                      >
                        {item.external_url}
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
