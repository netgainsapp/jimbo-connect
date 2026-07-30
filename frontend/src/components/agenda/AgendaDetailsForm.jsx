import { useState } from "react";
import { ChevronDown, ChevronRight, Image as ImageIcon, X } from "lucide-react";

const inputClass =
  "w-full rounded-card border border-border-default px-3 py-2 text-sm text-text-primary " +
  "placeholder:text-text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";

const labelClass = "block text-sm font-medium text-text-secondary mb-1";

function Field({ label, hint, children }) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      {children}
      {hint && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
    </div>
  );
}

// 1MB, matching the backend cap in branding.MAX_UPLOAD_BYTES. Checked here too
// so an oversized file is refused instantly instead of after a round trip.
const MAX_LOGO_BYTES = 1024 * 1024;

export default function AgendaDetailsForm({ agenda, setField, onError }) {
  // Progressive disclosure: the first screen asks only for what an agenda
  // genuinely cannot do without. Everything else is one click away.
  const [showMore, setShowMore] = useState(false);

  const onLogo = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_LOGO_BYTES) {
      onError?.("That file is too large. Logos can be up to 1 MB.");
      event.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setField("logo", reader.result);
    reader.onerror = () => onError?.("That logo could not be read.");
    reader.readAsDataURL(file);
    event.target.value = "";
  };

  const set = (name) => (e) => setField(name, e.target.value);

  return (
    <section className="rounded-card border border-border-default bg-white p-5 shadow-card">
      <h2 className="text-base font-semibold text-text-primary">Event details</h2>
      <p className="mt-1 mb-4 text-sm text-text-muted">
        Just the essentials to start. You can add more at any point.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Field label="Event name">
            <input
              className={inputClass}
              value={agenda.event_name}
              onChange={set("event_name")}
              placeholder="Denver Founders Dinner"
              maxLength={200}
            />
          </Field>
        </div>

        <Field label="Start date">
          <input type="date" className={inputClass} value={agenda.start_date} onChange={set("start_date")} />
        </Field>
        <Field label="End date" hint="Leave empty for a single day event.">
          <input type="date" className={inputClass} value={agenda.end_date} onChange={set("end_date")} />
        </Field>

        <Field label="Start time">
          <input type="time" className={inputClass} value={agenda.start_time} onChange={set("start_time")} />
        </Field>
        <Field label="End time">
          <input type="time" className={inputClass} value={agenda.end_time} onChange={set("end_time")} />
        </Field>

        <div className="sm:col-span-2">
          <Field label="Venue name">
            <input
              className={inputClass}
              value={agenda.venue_name}
              onChange={set("venue_name")}
              placeholder="The Loft"
              maxLength={200}
            />
          </Field>
        </div>
      </div>

      <button
        type="button"
        onClick={() => setShowMore((v) => !v)}
        className="mt-5 flex items-center gap-1 text-sm font-medium text-primary hover:text-primary-hover"
      >
        {showMore ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {showMore ? "Fewer details" : "Add description, organizer, and logo"}
      </button>

      {showMore && (
        <div className="mt-4 grid gap-4 border-t border-border-default pt-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Field label="Description">
              <textarea
                className={`${inputClass} min-h-[80px]`}
                value={agenda.description}
                onChange={set("description")}
                placeholder="An evening for operators building in the mountain west."
                maxLength={5000}
              />
            </Field>
          </div>

          <div className="sm:col-span-2">
            <Field label="Address">
              <input className={inputClass} value={agenda.venue_address} onChange={set("venue_address")} maxLength={400} />
            </Field>
          </div>

          <div className="sm:col-span-2">
            <Field label="Virtual event link" hint="Used when there is no physical venue.">
              <input
                className={inputClass}
                value={agenda.virtual_url}
                onChange={set("virtual_url")}
                placeholder="https://meet.example.com/founders"
                maxLength={2000}
              />
            </Field>
          </div>

          <Field label="Organizer name">
            <input className={inputClass} value={agenda.organizer_name} onChange={set("organizer_name")} maxLength={200} />
          </Field>
          <Field label="Organizer company">
            <input className={inputClass} value={agenda.organizer_company} onChange={set("organizer_company")} maxLength={200} />
          </Field>
          <Field label="Organizer email">
            <input
              type="email"
              className={inputClass}
              value={agenda.organizer_email}
              onChange={set("organizer_email")}
              maxLength={320}
            />
          </Field>
          <Field label="Event website">
            <input className={inputClass} value={agenda.event_website} onChange={set("event_website")} maxLength={2000} />
          </Field>

          <div className="sm:col-span-2">
            <label className={labelClass}>Event logo</label>
            {agenda.logo ? (
              <div className="flex items-center gap-3">
                <img
                  src={agenda.logo}
                  alt="Event logo preview"
                  className="h-12 w-12 rounded-card border border-border-default object-contain"
                />
                <button
                  type="button"
                  onClick={() => setField("logo", null)}
                  className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
                >
                  <X size={14} /> Remove
                </button>
              </div>
            ) : (
              <label className="inline-flex cursor-pointer items-center gap-2 rounded-card border border-border-default px-3 py-2 text-sm text-text-secondary hover:bg-bg-secondary">
                <ImageIcon size={16} />
                Upload a logo
                <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={onLogo} />
              </label>
            )}
            <p className="mt-1 text-xs text-text-muted">PNG, JPEG, or WebP, up to 1 MB.</p>
          </div>
        </div>
      )}
    </section>
  );
}
