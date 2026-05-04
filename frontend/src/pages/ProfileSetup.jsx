import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { profileApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import Avatar from "../components/Avatar.jsx";
import { Camera } from "lucide-react";

export default function ProfileSetup({ editMode = false }) {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const fileRef = useRef(null);

  const [form, setForm] = useState({
    name: "",
    role: "",
    company: "",
    industry: "",
    bio: "",
    looking_for: "",
    phone: "",
    linkedin: "",
    photo_url: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user?.profile) {
      setForm({ ...form, ...user.profile });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const setField = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handlePhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      toast.show("Image must be under 2MB", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setForm((f) => ({ ...f, photo_url: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.role || !form.company) {
      toast.show("Name, role, and company are required", "error");
      return;
    }
    setSaving(true);
    try {
      await profileApi.update(form);
      await refresh();
      toast.show("Profile saved");
      if (editMode) {
        navigate("/events");
      } else {
        navigate("/events", { replace: true });
      }
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">
        {editMode ? "Edit your profile" : "Set up your profile"}
      </h1>
      <p className="text-sm text-text-secondary mb-8">
        This is what other attendees will see when they browse the directory.
      </p>

      <form onSubmit={submit} className="card p-6 flex flex-col gap-5">
        <div className="flex items-center gap-4">
          <Avatar name={form.name} photoUrl={form.photo_url} size={80} />
          <div>
            <button
              type="button"
              className="btn-outline"
              onClick={() => fileRef.current?.click()}
            >
              <Camera className="w-4 h-4" /> Upload photo
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handlePhoto}
            />
            <div className="text-xs text-text-muted mt-1">PNG or JPG, up to 2MB</div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Full name *</label>
            <input className="input" value={form.name} onChange={setField("name")} required />
          </div>
          <div>
            <label className="label">Role / title *</label>
            <input className="input" value={form.role} onChange={setField("role")} required />
          </div>
          <div>
            <label className="label">Company *</label>
            <input
              className="input"
              value={form.company}
              onChange={setField("company")}
              required
            />
          </div>
          <div>
            <label className="label">Industry</label>
            <input
              className="input"
              value={form.industry}
              onChange={setField("industry")}
              placeholder="e.g. SaaS, CPG, Hardware"
            />
          </div>
        </div>

        <div>
          <label className="label">Bio</label>
          <textarea
            className="input min-h-[90px]"
            value={form.bio}
            onChange={setField("bio")}
            placeholder="A few sentences about you and what you do."
          />
        </div>

        <div>
          <label className="label">What you're looking for</label>
          <textarea
            className="input min-h-[70px]"
            value={form.looking_for}
            onChange={setField("looking_for")}
            placeholder="Hiring? Investors? Customers? Be specific."
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Phone</label>
            <input
              className="input"
              value={form.phone}
              onChange={setField("phone")}
              placeholder="303-555-0100"
            />
          </div>
          <div>
            <label className="label">LinkedIn</label>
            <input
              className="input"
              value={form.linkedin}
              onChange={setField("linkedin")}
              placeholder="linkedin.com/in/you"
            />
          </div>
        </div>

        <div className="flex justify-end gap-2">
          {editMode && (
            <button type="button" className="btn-ghost" onClick={() => navigate(-1)}>
              Cancel
            </button>
          )}
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </form>
    </div>
  );
}
