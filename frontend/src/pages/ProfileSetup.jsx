import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { profileApi } from "../lib/api.js";
import { safeNext } from "../lib/nextPath.js";
import { PHONE_ERROR, formatPhone, isValidPhone } from "../lib/phone.js";
import { useToast } from "../hooks/useToast.jsx";
import { useConfirm } from "../hooks/useConfirm.jsx";
import Avatar from "../components/Avatar.jsx";
import { Camera, Trash2 } from "lucide-react";
import { MAX_SOURCE_BYTES, shrinkImageFile } from "../lib/image.js";

export default function ProfileSetup({ editMode = false }) {
  const [searchParams] = useSearchParams();
  const { user, refresh, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const confirm = useConfirm();
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
      setForm((f) => ({ ...f, ...user.profile }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const setField = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handlePhoto = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > MAX_SOURCE_BYTES) {
      toast.show("That file is enormous. Try a normal photo.", "error");
      return;
    }
    try {
      // Resized before it ever leaves the browser, so any phone photo works and
      // the payload stays small enough for the server to accept.
      const photo_url = await shrinkImageFile(file);
      setForm((f) => ({ ...f, photo_url }));
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      // Let the same file be re-picked if something went wrong.
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.role || !form.company) {
      toast.show("Name, role, and company are required", "error");
      return;
    }
    // The field formats as you type and caps at ten digits, so this is mostly
    // unreachable. It still exists because a value can arrive by paste or
    // autofill without passing through the keystroke handler.
    if (!isValidPhone(form.phone)) {
      toast.show(PHONE_ERROR, "error");
      return;
    }
    setSaving(true);
    try {
      await profileApi.update(form);
      await refresh();
      toast.show("Profile saved");
      const dest = safeNext(searchParams.get("next"), "/events");
      if (editMode) {
        navigate(dest);
      } else {
        navigate(dest, { replace: true });
      }
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <h1 className="text-2xl font-bold text-text-primary mb-1">
        {editMode ? "Edit your profile" : "Set up your profile"}
      </h1>
      <p className="text-sm text-text-secondary mb-8">
        This is what other attendees will see when they browse the directory.
      </p>

      <form onSubmit={submit} className="card p-6 flex flex-col gap-5">
        <div className="flex flex-col items-center text-center gap-3 pb-1">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="relative rounded-full focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
            aria-label={form.photo_url ? "Change profile photo" : "Add a profile photo"}
          >
            <Avatar name={form.name} photoUrl={form.photo_url} size={96} />
            <span className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center border-2 border-white shadow">
              <Camera className="w-4 h-4" />
            </span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={handlePhoto}
          />
          <div>
            <div className="text-sm font-bold text-text-primary">
              {form.photo_url
                ? "Looking good. Tap to change your photo."
                : "Add a photo so people remember you"}
            </div>
            <div className="text-xs text-text-secondary mt-0.5 max-w-xs">
              The directory feels personal when people can put a face to the
              name. JPG or PNG, straight off your phone. We resize it for you.
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="profile-name">Full name *</label>
            <input id="profile-name" className="input" value={form.name} onChange={setField("name")} required />
          </div>
          <div>
            <label className="label" htmlFor="profile-role">Role / title *</label>
            <input id="profile-role" className="input" value={form.role} onChange={setField("role")} required />
          </div>
          <div>
            <label className="label" htmlFor="profile-company">Company *</label>
            <input
              id="profile-company"
              className="input"
              value={form.company}
              onChange={setField("company")}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="profile-industry">Industry</label>
            <input
              id="profile-industry"
              className="input"
              value={form.industry}
              onChange={setField("industry")}
              placeholder="e.g. SaaS, CPG, Hardware"
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="profile-bio">Bio</label>
          <textarea
            id="profile-bio"
            className="input min-h-[90px]"
            value={form.bio}
            onChange={setField("bio")}
            placeholder="A few sentences about you and what you do."
          />
        </div>

        <div>
          <label className="label" htmlFor="profile-looking-for">What you're looking for</label>
          <textarea
            id="profile-looking-for"
            className="input min-h-[70px]"
            value={form.looking_for}
            onChange={setField("looking_for")}
            placeholder="Hiring? Investors? Customers? Be specific."
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="profile-phone">Phone</label>
            <input
              id="profile-phone"
              className="input"
              type="tel"
              inputMode="tel"
              autoComplete="tel-national"
              value={form.phone}
              // Formats as you type. No maxLength on purpose: the browser
              // would truncate a pasted "+1 303 555 0101" into a different,
              // valid looking number. Over-length input stays visible and is
              // refused on save instead.
              onChange={(e) =>
                setForm((f) => ({ ...f, phone: formatPhone(e.target.value) }))
              }
              placeholder="303-555-0100"
              aria-describedby="profile-phone-hint"
              aria-invalid={!isValidPhone(form.phone)}
            />
            <p
              id="profile-phone-hint"
              className={`mt-1 text-xs ${
                isValidPhone(form.phone) ? "text-text-muted" : "text-red-600"
              }`}
            >
              {isValidPhone(form.phone)
                ? "10 digits, like 303-555-0100."
                : PHONE_ERROR}
            </p>
          </div>
          <div>
            <label className="label" htmlFor="profile-linkedin">LinkedIn</label>
            <input
              id="profile-linkedin"
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

      {editMode && !user?.is_admin && (
        <div className="mt-10 pt-6 border-t border-border-default">
          <div className="font-bold text-text-primary mb-1">Danger zone</div>
          <p className="text-sm text-text-secondary mb-3">
            Permanently delete your account, every saved contact, every message,
            and remove yourself from every event. Cannot be undone.
          </p>
          <button
            type="button"
            className="btn-danger"
            onClick={async () => {
              if (
                !(await confirm({
                  title: "Permanently delete your account?",
                  body: "This removes everything: saved contacts, messages, event memberships. You'll be logged out and can't log back in.",
                  confirmLabel: "Delete account",
                  destructive: true,
                }))
              )
                return;
              try {
                await profileApi.deleteSelf();
                await logout().catch(() => {});
                toast.show("Account deleted");
                navigate("/login", { replace: true });
              } catch (err) {
                toast.show(err.message, "error");
              }
            }}
          >
            <Trash2 className="w-4 h-4" /> Delete my account
          </button>
        </div>
      )}
    </div>
  );
}
