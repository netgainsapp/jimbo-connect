import { useEffect, useState } from "react";
import { Bookmark, Copy, Mail, Phone, Linkedin, Trash2, Edit2 } from "lucide-react";
import { contactsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { copyToClipboard } from "../lib/utils.js";
import Avatar from "../components/Avatar.jsx";
import AttendeeProfileModal from "../components/AttendeeProfileModal.jsx";

export default function SavedContacts() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [draftNote, setDraftNote] = useState("");
  const [active, setActive] = useState(null);
  const toast = useToast();

  const load = async () => {
    setLoading(true);
    try {
      setItems(await contactsApi.list());
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

  const remove = async (item) => {
    try {
      await contactsApi.remove(item.contact_id);
      setItems((prev) => prev.filter((x) => x.id !== item.id));
      toast.show("Contact removed");
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setDraftNote(item.note || "");
  };

  const saveNote = async (item) => {
    try {
      await contactsApi.updateNote(item.contact_id, draftNote);
      setItems((prev) =>
        prev.map((x) => (x.id === item.id ? { ...x, note: draftNote } : x))
      );
      setEditingId(null);
      toast.show("Note saved");
    } catch (e) {
      toast.show(e.message, "error");
    }
  };

  const copy = async (text, label) => {
    if (!text) return;
    await copyToClipboard(text);
    toast.show(`${label} copied`);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">Saved contacts</h1>
      <p className="text-sm text-text-secondary mb-6">
        Your private list. Notes are only visible to you.
      </p>

      {loading ? (
        <div className="text-text-muted">Loading…</div>
      ) : items.length === 0 ? (
        <div className="card p-10 text-center">
          <Bookmark className="w-10 h-10 text-text-muted mx-auto mb-3" />
          <div className="font-bold text-text-primary mb-1">
            No saved contacts yet
          </div>
          <div className="text-sm text-text-secondary">
            Save people from the event directory and they'll show up here.
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => {
            const c = item.contact;
            const p = c.profile || {};
            const isEditing = editingId === item.id;
            return (
              <div key={item.id} className="card p-5">
                <div className="flex items-start gap-4">
                  <button
                    onClick={() => setActive(c)}
                    className="shrink-0"
                    aria-label="View profile"
                  >
                    <Avatar name={p.name} photoUrl={p.photo_url} size={56} />
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <button
                          onClick={() => setActive(c)}
                          className="font-bold text-text-primary text-left hover:text-primary truncate block"
                        >
                          {p.name || c.email}
                        </button>
                        <div className="text-sm text-text-secondary truncate">
                          {p.role}
                          {p.role && p.company && " · "}
                          {p.company}
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => copy(c.email, "Email")}
                          className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                          title="Copy email"
                        >
                          <Mail className="w-4 h-4" />
                        </button>
                        {p.phone && (
                          <button
                            onClick={() => copy(p.phone, "Phone")}
                            className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                            title="Copy phone"
                          >
                            <Phone className="w-4 h-4" />
                          </button>
                        )}
                        {p.linkedin && (
                          <button
                            onClick={() => copy(p.linkedin, "LinkedIn")}
                            className="p-2 rounded-full hover:bg-bg-secondary text-text-secondary"
                            title="Copy LinkedIn"
                          >
                            <Linkedin className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => remove(item)}
                          className="p-2 rounded-full hover:bg-red-50 text-red-500"
                          title="Remove"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 border-t border-border-default pt-3">
                      {isEditing ? (
                        <div className="flex flex-col gap-2">
                          <textarea
                            className="input min-h-[70px]"
                            value={draftNote}
                            onChange={(e) => setDraftNote(e.target.value)}
                            placeholder="Add a private note…"
                            autoFocus
                          />
                          <div className="flex gap-2 justify-end">
                            <button
                              className="btn-ghost"
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </button>
                            <button
                              className="btn-primary"
                              onClick={() => saveNote(item)}
                            >
                              Save note
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="flex items-start gap-2 cursor-pointer group"
                          onClick={() => startEdit(item)}
                        >
                          <div className="flex-1 text-sm text-text-secondary whitespace-pre-wrap">
                            {item.note || (
                              <span className="text-text-muted italic">
                                Click to add a private note
                              </span>
                            )}
                          </div>
                          <Edit2 className="w-3.5 h-3.5 text-text-muted opacity-0 group-hover:opacity-100 mt-1" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <AttendeeProfileModal
        attendee={active}
        open={Boolean(active)}
        onClose={() => setActive(null)}
        onSavedChange={load}
      />
    </div>
  );
}
