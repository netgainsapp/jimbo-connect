import {
  dateRangeLine,
  formatAgendaDate,
  formatAgendaTimeRange,
  groupByDay,
  locationLine,
} from "./format.js";

// Mirrors the layout of backend/agenda/docx.py so what the organizer sees here
// is what lands in the Word file.
export default function AgendaPreview({ agenda }) {
  const groups = groupByDay(agenda.items);
  const dates = dateRangeLine(agenda);
  const place = locationLine(agenda);
  const organizer = [
    agenda.organizer_name,
    agenda.organizer_company,
    agenda.organizer_email,
    agenda.event_website,
  ].filter(Boolean);

  return (
    <div className="rounded-card border border-border-default bg-white p-8 shadow-card">
      <div className="mx-auto max-w-[46rem]">
        {agenda.logo && (
          <img
            src={agenda.logo}
            alt=""
            className="mx-auto mb-4 h-16 w-auto max-w-[8rem] object-contain"
          />
        )}

        <h1 className="text-center text-2xl font-bold text-text-primary">
          {agenda.event_name || "Untitled event"}
        </h1>
        {dates && <p className="mt-1 text-center text-sm text-text-muted">{dates}</p>}
        {place && <p className="text-center text-sm text-text-muted">{place}</p>}

        {agenda.description && (
          <p className="mt-5 whitespace-pre-line text-sm leading-relaxed text-text-primary">
            {agenda.description}
          </p>
        )}

        {groups.length === 0 && (
          <p className="mt-6 text-sm italic text-text-muted">
            No sessions have been added yet.
          </p>
        )}

        {groups.map(([day, items]) => (
          <section key={day || "undated"} className="mt-7">
            <h2 className="mb-2 text-sm font-bold text-primary-hover">
              {day ? formatAgendaDate(day) : "Date not set"}
            </h2>
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
                      <p className="mt-1 break-all text-xs text-text-muted">
                        {item.external_url}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}

        {organizer.length > 0 && (
          <section className="mt-7">
            <h2 className="mb-1 text-sm font-bold text-primary-hover">Organizer</h2>
            {organizer.map((line) => (
              <p key={line} className="text-xs text-text-muted">
                {line}
              </p>
            ))}
          </section>
        )}

        <p className="mt-8 border-t border-border-default pt-3 text-center text-[10px] text-text-muted">
          Agenda created with Intro Connect | intro-connect.com
        </p>
      </div>
    </div>
  );
}
