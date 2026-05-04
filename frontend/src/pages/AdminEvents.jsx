import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Copy, Edit2, Trash2, Calendar, MapPin, Users, UserPlus, Eye } from "lucide-react";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { copyToClipboard, formatDate } from "../lib/utils.js";
import Modal from "../components/Modal.jsx";
import BulkImportModal from "../components/BulkImportModal.jsx";

const FRONTEND_URL = window.location.origin;

function defaultStart() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(14, 0, 0, 0);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T14:00`;
}

const empty = () => ({
  name: "",
  date: defaultStart(),
  location: "",
  industry_tags: "",
});

export default function AdminEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { mode: "create" | "edit", event? }
  const [form, setForm] = useState(empty());
  const [saving, setSaving] = useState(false);
  const [importEventId, setImportEventId] = useState(null);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      setEvents(await eventsApi.list());
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openCreate = () => {
    setForm(empty());
    setModal({ mode: "create" });
  };

  const openEdit = (e) => {
    setForm({
      name: e.name,
      date: toDateInput(e.date),
      location: e.location || "",
      industry_tags: (e.industry_tags || []).join(", "),
    });
    setModal({ mode: "edit", event: e });
  };

  const submit = async (ev) => {
    ev.preventDefault();
    if (!form.name || !form.date) {
      toast.show("Name and date are required", "error");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        date: new Date(form.date).toISOString(),
        location: form.location,
        industry_tags: form.industry_tags
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      if (modal.mode === "create") {
        const created = await eventsApi.create(payload);
        toast.show("Event created");
        setModal(null);
        await load();
        setImportEventId(created.id);
        return;
      }
      await eventsApi.update(modal.event.id, payload);
      toast.show("Event updated");
      setModal(null);
      await load();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (e) => {
    if (!confirm(`Delete "${e.name}"? This cannot be undone.`)) return;
    try {
      await eventsApi.remove(e.id);
      toast.show("Event deleted");
      setEvents((prev) => prev.filter((x) => x.id !== e.id));
    } catch (err) {
      toast.show(err.message, "error");
    }
  };

  const copyJoinLink = async (e) => {
    const link = `${FRONTEND_URL}/join/${e.join_code}`;
    await copyToClipboard(link);
    toast.show("Join link copied");
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-end justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Events</h1>
          <p className="text-sm text-text-secondary">
            Create events and share join links with attendees.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setImportEventId("")}
            className="btn-outline"
          >
            <UserPlus className="w-4 h-4" /> Import attendees
          </button>
          <button onClick={openCreate} className="btn-primary">
            <Plus className="w-4 h-4" /> New event
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : events.length === 0 ? (
        <div className="card p-10 text-center text-text-secondary">
          No events yet. Create your first one.
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-bg-secondary text-text-secondary">
              <tr>
                <th className="text-left px-4 py-3 font-semibold">Event</th>
                <th className="text-left px-4 py-3 font-semibold">Date</th>
                <th className="text-left px-4 py-3 font-semibold">Attendees</th>
                <th className="text-left px-4 py-3 font-semibold">Join code</th>
                <th className="text-right px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-t border-border-default">
                  <td className="px-4 py-3">
                    <Link
                      to={`/admin/events/${e.id}`}
                      className="font-bold text-text-primary hover:text-primary"
                    >
                      {e.name}
                    </Link>
                    {e.location && (
                      <div className="flex items-center gap-1 text-xs text-text-secondary mt-0.5">
                        <MapPin className="w-3 h-3" /> {e.location}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    <div className="inline-flex items-center gap-1">
                      <Calendar className="w-4 h-4" /> {formatDate(e.date)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-text-secondary">
                    <div className="inline-flex items-center gap-1">
                      <Users className="w-4 h-4" /> {e.attendee_count}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <code className="bg-bg-secondary px-2 py-1 rounded text-text-primary font-mono text-xs">
                      {e.join_code}
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      <Link
                        to={`/admin/events/${e.id}`}
                        className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                        title="View event"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={() => copyJoinLink(e)}
                        className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                        title="Copy join link"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => openEdit(e)}
                        className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => remove(e)}
                        className="p-2 rounded-full hover:bg-red-50 text-red-500"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal open={Boolean(modal)} onClose={() => setModal(null)} maxWidth="max-w-lg">
        {modal && (
          <form onSubmit={submit} className="p-6 flex flex-col gap-4">
            <h2 className="text-lg font-bold text-text-primary">
              {modal.mode === "create" ? "New event" : "Edit event"}
            </h2>
            <div>
              <label className="label">Name</label>
              <input
                className="input"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Date & start time</label>
              <input
                type="datetime-local"
                className="input"
                value={form.date}
                onChange={(e) => setForm({ ...form, date: e.target.value })}
                required
              />
              <div className="text-xs text-text-muted mt-1">
                Defaults to 2:00 PM tomorrow.
              </div>
            </div>
            <div>
              <label className="label">Location</label>
              <input
                className="input"
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="Denver, CO"
              />
            </div>
            <div>
              <label className="label">Industry tags (comma separated)</label>
              <input
                className="input"
                value={form.industry_tags}
                onChange={(e) =>
                  setForm({ ...form, industry_tags: e.target.value })
                }
                placeholder="SaaS, Hardware, CPG"
              />
            </div>
            <div className="flex justify-end gap-2 mt-2">
              <button
                type="button"
                className="btn-ghost"
                onClick={() => setModal(null)}
              >
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving
                  ? "Saving…"
                  : modal.mode === "create"
                  ? "Create event"
                  : "Save changes"}
              </button>
            </div>
          </form>
        )}
      </Modal>

      <BulkImportModal
        open={importEventId !== null}
        onClose={() => setImportEventId(null)}
        onComplete={load}
        defaultEventId={importEventId || ""}
      />
    </div>
  );
}

function toDateInput(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
    d.getHours()
  )}:${pad(d.getMinutes())}`;
}
