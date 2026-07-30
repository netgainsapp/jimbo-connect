import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy,
  GripVertical,
  Trash2,
} from "lucide-react";

const inputClass =
  "w-full rounded-card border border-border-default px-3 py-2 text-sm text-text-primary " +
  "placeholder:text-text-muted focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary";

const iconButton =
  "rounded-card p-1.5 text-text-muted transition hover:bg-bg-secondary hover:text-text-primary " +
  "disabled:cursor-not-allowed disabled:opacity-30";

export default function AgendaItemRow({
  item,
  index,
  count,
  overlapping,
  invalidTime,
  onChange,
  onDuplicate,
  onRemove,
  onMove,
}) {
  const set = (name) => (e) => onChange(item.id, { [name]: e.target.value });

  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: item.id });

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`rounded-card border bg-white p-4 shadow-card ${
        isDragging
          ? "z-10 border-primary opacity-90 shadow-lg"
          : "border-border-default"
      }`}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        {/* Drag is handle-only and never the whole card: this row is mostly
            text inputs, and making the card draggable would break selecting
            and editing text inside it. */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          className="mt-1.5 shrink-0 cursor-grab touch-none rounded-card p-1 text-text-muted hover:bg-bg-secondary hover:text-text-primary active:cursor-grabbing"
          aria-label={`Reorder ${item.title || "session"}`}
          title="Drag to reorder"
        >
          <GripVertical size={16} />
        </button>
        <input
          className={`${inputClass} font-medium`}
          value={item.title}
          onChange={set("title")}
          placeholder="Session title"
          maxLength={300}
        />
        <div className="flex shrink-0 items-center gap-0.5">
          {/* Explicit reorder controls, kept alongside drag and drop. They are
              the accessible path and work everywhere drag is awkward: touch,
              keyboard only, and assistive tech. */}
          <button
            type="button"
            className={iconButton}
            onClick={() => onMove(item.id, -1)}
            disabled={index === 0}
            aria-label="Move session earlier"
            title="Move earlier"
          >
            <ChevronUp size={16} />
          </button>
          <button
            type="button"
            className={iconButton}
            onClick={() => onMove(item.id, 1)}
            disabled={index === count - 1}
            aria-label="Move session later"
            title="Move later"
          >
            <ChevronDown size={16} />
          </button>
          <button
            type="button"
            className={iconButton}
            onClick={() => onDuplicate(item.id)}
            aria-label="Duplicate session"
            title="Duplicate"
          >
            <Copy size={16} />
          </button>
          <button
            type="button"
            className={`${iconButton} hover:text-red-600`}
            onClick={() => onRemove(item.id)}
            aria-label="Delete session"
            title="Delete"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs text-text-muted">Date</label>
          <input type="date" className={inputClass} value={item.date} onChange={set("date")} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-text-muted">Start</label>
          <input type="time" className={inputClass} value={item.start_time} onChange={set("start_time")} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-text-muted">End</label>
          <input
            type="time"
            className={`${inputClass} ${invalidTime ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""}`}
            value={item.end_time}
            onChange={set("end_time")}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-text-muted">Room or location</label>
          <input className={inputClass} value={item.location} onChange={set("location")} maxLength={200} />
        </div>

        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-text-muted">Speaker or host</label>
          <input className={inputClass} value={item.speaker} onChange={set("speaker")} maxLength={200} />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-text-muted">Link (optional)</label>
          <input
            className={inputClass}
            value={item.external_url}
            onChange={set("external_url")}
            placeholder="https://"
            maxLength={2000}
          />
        </div>

        <div className="sm:col-span-4">
          <label className="mb-1 block text-xs text-text-muted">Description</label>
          <textarea
            className={`${inputClass} min-h-[64px]`}
            value={item.description}
            onChange={set("description")}
            maxLength={5000}
          />
        </div>

        <div className="sm:col-span-4">
          <label className="mb-1 block text-xs text-text-muted">
            Private notes (never appear in the download)
          </label>
          <input className={inputClass} value={item.notes} onChange={set("notes")} maxLength={5000} />
        </div>
      </div>

      {invalidTime && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-red-600">
          <AlertTriangle size={14} />
          The end time needs to come after the start time.
        </p>
      )}
      {overlapping && !invalidTime && (
        <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-600">
          <AlertTriangle size={14} />
          This overlaps another session. That is fine if the tracks run at once.
        </p>
      )}
    </li>
  );
}
