import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import {
  ArrowDownWideNarrow,
  CalendarPlus,
  Download,
  Eye,
  Loader2,
  Pencil,
  Plus,
} from "lucide-react";

import AgendaDetailsForm from "../components/agenda/AgendaDetailsForm.jsx";
import AgendaItemRow from "../components/agenda/AgendaItemRow.jsx";
import AgendaPreview from "../components/agenda/AgendaPreview.jsx";
import { formatAgendaDate, groupByDay } from "../components/agenda/format.js";
import { useAgendaDraft } from "../hooks/useAgendaDraft.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { agendaApi } from "../lib/api.js";

/** Empty date strings must become null: the API models them as Optional[date]
 *  and "" is not a date. */
function toPayload(agenda) {
  return {
    ...agenda,
    start_date: agenda.start_date || null,
    end_date: agenda.end_date || null,
    items: agenda.items.map((item) => ({ ...item, date: item.date || null })),
  };
}

/** Blocking problems only. Overlaps are a warning and never stop an export. */
function firstBlockingProblem(agenda) {
  if (agenda.items.some((i) => !i.date)) {
    return "Every session needs a date before you can download the agenda.";
  }
  if (agenda.items.some((i) => i.start_time && i.end_time && i.end_time <= i.start_time)) {
    return "Some sessions end before they start. Fix those times and try again.";
  }
  return null;
}

export default function AgendaBuilder() {
  const {
    agenda, setField, addItem, updateItem, removeItem,
    duplicateItem, moveItem, reorderItem, sortDayByTime, savedAt, warnings,
  } = useAgendaDraft();
  const [tab, setTab] = useState("edit");
  const [exporting, setExporting] = useState(false);
  const [exported, setExported] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();

  const groups = useMemo(() => groupByDay(agenda.items), [agenda.items]);

  // A small activation distance so a click on the grip still reads as a click,
  // and the keyboard sensor so reordering works without a pointer at all.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = ({ active, over }) => {
    if (over && active.id !== over.id) reorderItem(active.id, over.id);
  };

  const handleExport = async () => {
    const problem = firstBlockingProblem(agenda);
    if (problem) {
      toast.show(problem, "error");
      return;
    }
    setExporting(true);
    try {
      const { blob, filename } = await agendaApi.exportDocx(toPayload(agenda));
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExported(true);
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setExporting(false);
    }
  };

  // Phase 1 sends the organizer to the existing create-event path. The draft
  // stays in localStorage, so nothing is lost; carrying these fields into the
  // event itself is Phase 4 (see docs/AGENDA-BUILDER-PROPOSAL.md).
  const handleCreateEvent = () => navigate(user ? "/events?host=1" : "/register");

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-text-primary">Agenda Builder</h1>
            <span className="rounded-pill bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
              Free
            </span>
          </div>
          <p className="mt-1 text-sm text-text-muted">
            Build your event agenda and download it as a Word document. No account needed.
          </p>
        </div>
        <div className="text-xs text-text-muted">
          {savedAt ? `Saved ${savedAt.toLocaleTimeString()}` : "Saves as you type"}
        </div>
      </header>

      <div className="mb-5 inline-flex rounded-card border border-border-default bg-white p-1">
        <button
          type="button"
          onClick={() => setTab("edit")}
          className={`inline-flex items-center gap-1.5 rounded-card px-3 py-1.5 text-sm font-medium ${
            tab === "edit" ? "bg-primary text-white" : "text-text-secondary hover:bg-bg-secondary"
          }`}
        >
          <Pencil size={14} /> Edit
        </button>
        <button
          type="button"
          onClick={() => setTab("preview")}
          className={`inline-flex items-center gap-1.5 rounded-card px-3 py-1.5 text-sm font-medium ${
            tab === "preview" ? "bg-primary text-white" : "text-text-secondary hover:bg-bg-secondary"
          }`}
        >
          <Eye size={14} /> Preview
        </button>
      </div>

      {tab === "preview" ? (
        <AgendaPreview agenda={agenda} />
      ) : (
        <div className="space-y-6">
          <AgendaDetailsForm
            agenda={agenda}
            setField={setField}
            onError={(m) => toast.show(m, "error")}
          />

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold text-text-primary">Agenda</h2>
              {agenda.items.length > 0 && (
                <button
                  type="button"
                  onClick={() => addItem(agenda.start_date)}
                  className="inline-flex items-center gap-1.5 rounded-card border border-border-default px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-bg-secondary"
                >
                  <Plus size={15} /> Add session
                </button>
              )}
            </div>

            {agenda.items.length === 0 ? (
              // Making the first item obvious is the single most important
              // moment in this tool: an empty builder with no clear next step
              // is where people leave.
              <div className="rounded-card border border-dashed border-border-default bg-bg-secondary p-8 text-center">
                <p className="text-sm font-medium text-text-primary">
                  Add your first session to get started
                </p>
                <p className="mx-auto mt-1 max-w-sm text-sm text-text-muted">
                  A session is anything on your schedule: a welcome, a talk, a break, or dinner.
                </p>
                <button
                  type="button"
                  onClick={() => addItem(agenda.start_date)}
                  className="mt-4 inline-flex items-center gap-1.5 rounded-card bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-hover"
                >
                  <Plus size={16} /> Add your first session
                </button>
              </div>
            ) : (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <div className="space-y-6">
                  {groups.map(([day, items]) => (
                    <div key={day || "undated"}>
                      <div className="mb-2 flex items-center justify-between gap-3">
                        <h3 className="text-sm font-semibold text-text-secondary">
                          {day ? formatAgendaDate(day) : "Date not set"}
                        </h3>
                        {items.length > 1 && (
                          // Time sorting is an explicit choice, never automatic:
                          // sorting behind the organizer's back would throw away
                          // an order they dragged into place.
                          <button
                            type="button"
                            onClick={() => sortDayByTime(day)}
                            className="inline-flex items-center gap-1 text-xs font-medium text-text-muted hover:text-primary"
                          >
                            <ArrowDownWideNarrow size={13} /> Sort by time
                          </button>
                        )}
                      </div>
                      {/* One SortableContext per day: reordering is scoped to a
                          day, since dragging across a boundary would silently
                          change a session's date. */}
                      <SortableContext
                        items={items.map((i) => i.id)}
                        strategy={verticalListSortingStrategy}
                      >
                        <ul className="space-y-3">
                          {items.map((item, index) => (
                            <AgendaItemRow
                              key={item.id}
                              item={item}
                              index={index}
                              count={items.length}
                              overlapping={warnings.overlapping.has(item.id)}
                              invalidTime={warnings.invalidTimes.has(item.id)}
                              onChange={updateItem}
                              onDuplicate={duplicateItem}
                              onRemove={removeItem}
                              onMove={moveItem}
                            />
                          ))}
                        </ul>
                      </SortableContext>
                    </div>
                  ))}
                </div>
              </DndContext>
            )}
          </section>
        </div>
      )}

      {exported ? (
        <section className="mt-8 rounded-card border border-border-default bg-white p-6 text-center shadow-card">
          <h2 className="text-lg font-bold text-text-primary">Your agenda is ready.</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-text-secondary">
            Now turn it into an interactive event experience. Create an Intro Connect event
            so attendees can view the agenda, meet one another, and follow up after the event.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleCreateEvent}
              className="inline-flex items-center gap-2 rounded-card bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover"
            >
              <CalendarPlus size={16} /> Create Your Event
            </button>
            <button
              type="button"
              onClick={handleExport}
              disabled={exporting}
              className="inline-flex items-center gap-2 rounded-card border border-border-default px-5 py-2.5 text-sm font-semibold text-text-secondary hover:bg-bg-secondary disabled:opacity-60"
            >
              <Download size={16} /> Download Word Agenda
            </button>
          </div>
        </section>
      ) : (
        <div className="sticky bottom-0 mt-8 border-t border-border-default bg-white/95 py-4 backdrop-blur">
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-card bg-primary px-5 py-3 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-60 sm:w-auto"
          >
            {exporting ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
            {exporting ? "Building your document" : "Download Word Agenda"}
          </button>
        </div>
      )}
    </div>
  );
}
