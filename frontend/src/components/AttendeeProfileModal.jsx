import { useEffect, useState } from "react";
import { Bookmark, BookmarkCheck, Copy, Mail, Phone, Linkedin } from "lucide-react";
import Modal from "./Modal.jsx";
import Avatar from "./Avatar.jsx";
import { contactsApi } from "../lib/api.js";
import { copyToClipboard } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";

export default function AttendeeProfileModal({ attendee, open, onClose, onSavedChange }) {
  const [saved, setSaved] = useState(false);
  const [note, setNote] = useState("");
  const [editingNote, setEditingNote] = useState(false);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (!attendee || !open) return;
    let active = true;
    contactsApi.isSaved(attendee.id).then((res) => {
      if (!active) return;
      setSaved(Boolean(res.saved));
      setNote(res.note || "");
    });
    return () => {
      active = false;
    };
  }, [attendee, open]);

  if (!attendee) return null;
  const p = attendee.profile || {};

  const toggleSave = async () => {
    setLoading(true);
    try {
      if (saved) {
        await contactsApi.remove(attendee.id);
        setSaved(false);
        setNote("");
        toast.show("Contact removed");
      } else {
        await contactsApi.save(attendee.id, "");
        setSaved(true);
        toast.show("Contact saved");
      }
      onSavedChange?.();
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const saveNote = async () => {
    try {
      if (!saved) {
        await contactsApi.save(attendee.id, note);
        setSaved(true);
      } else {
        await contactsApi.updateNote(attendee.id, note);
      }
      setEditingNote(false);
      toast.show("Note saved");
      onSavedChange?.();
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
    <Modal open={open} onClose={onClose}>
      <div className="p-6">
        <div className="flex items-start gap-4 mb-5">
          <Avatar name={p.name} photoUrl={p.photo_url} size={80} />
          <div className="flex-1 min-w-0">
            <div className="text-xl font-bold text-text-primary truncate">
              {p.name || attendee.email}
            </div>
            <div className="text-sm text-text-secondary mt-0.5">
              {p.role}
              {p.role && p.company && " · "}
              {p.company}
            </div>
            {p.industry && <span className="pill mt-2">{p.industry}</span>}
          </div>
          <button
            onClick={toggleSave}
            disabled={loading}
            className={saved ? "btn-outline" : "btn-primary"}
          >
            {saved ? (
              <>
                <BookmarkCheck className="w-4 h-4" /> Saved
              </>
            ) : (
              <>
                <Bookmark className="w-4 h-4" /> Save
              </>
            )}
          </button>
        </div>

        {p.bio && (
          <div className="mb-5">
            <div className="label">About</div>
            <p className="text-sm text-text-primary whitespace-pre-wrap">{p.bio}</p>
          </div>
        )}

        {p.looking_for && (
          <div className="mb-5">
            <div className="label">Looking for</div>
            <p className="text-sm text-text-primary whitespace-pre-wrap">
              {p.looking_for}
            </p>
          </div>
        )}

        <div className="mb-5">
          <div className="label">Contact</div>
          <div className="flex flex-col gap-2">
            <ContactRow
              icon={<Mail className="w-4 h-4" />}
              label={attendee.email}
              onCopy={() => copy(attendee.email, "Email")}
            />
            {p.phone && (
              <ContactRow
                icon={<Phone className="w-4 h-4" />}
                label={p.phone}
                onCopy={() => copy(p.phone, "Phone")}
              />
            )}
            {p.linkedin && (
              <ContactRow
                icon={<Linkedin className="w-4 h-4" />}
                label={p.linkedin}
                onCopy={() => copy(p.linkedin, "LinkedIn")}
              />
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="label mb-0">Private note</div>
            {!editingNote && (
              <button
                onClick={() => setEditingNote(true)}
                className="text-xs font-semibold text-primary hover:underline"
              >
                {note ? "Edit" : "Add note"}
              </button>
            )}
          </div>
          {editingNote ? (
            <div className="flex flex-col gap-2">
              <textarea
                className="input min-h-[80px]"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Only you can see this note."
              />
              <div className="flex gap-2 justify-end">
                <button
                  className="btn-ghost"
                  onClick={() => setEditingNote(false)}
                >
                  Cancel
                </button>
                <button className="btn-primary" onClick={saveNote}>
                  Save note
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-text-secondary whitespace-pre-wrap min-h-[40px]">
              {note || (
                <span className="text-text-muted italic">
                  No note yet. Only you can see this.
                </span>
              )}
            </p>
          )}
        </div>
      </div>
    </Modal>
  );
}

function ContactRow({ icon, label, onCopy }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-card bg-bg-secondary">
      <div className="text-text-secondary">{icon}</div>
      <div className="flex-1 text-sm text-text-primary truncate">{label}</div>
      <button
        onClick={onCopy}
        className="text-text-secondary hover:text-primary p-1"
        aria-label="Copy"
      >
        <Copy className="w-4 h-4" />
      </button>
    </div>
  );
}
