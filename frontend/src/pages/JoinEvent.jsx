import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { profileComplete } from "../lib/utils.js";

export default function JoinEvent() {
  const { code } = useParams();
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [status, setStatus] = useState("Joining…");
  const [form, setForm] = useState({ name: "", linkedin: "" });
  const [joining, setJoining] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    if (loading || !user || ran.current) return;
    ran.current = true;
    if (!profileComplete(user.profile) && !user.is_admin) {
      sessionStorage.setItem("pending_join_code", code);
      navigate("/profile/setup", { replace: true });
      return;
    }
    eventsApi
      .join(code)
      .then((ev) => {
        toast.show(`Joined ${ev.name}`);
        navigate(`/events/${ev.id}`, { replace: true });
      })
      .catch((e) => {
        toast.show(e.message, "error");
        setStatus(e.message);
      });
  }, [code, user, loading, navigate, toast]);

  const joinAsGuest = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.show("Your name is all we need", "error");
      return;
    }
    setJoining(true);
    try {
      const res = await eventsApi.guestJoin(code, {
        name: form.name.trim(),
        linkedin: form.linkedin.trim(),
      });
      // The cookie is already set; pull the session into the auth context so
      // every protected route sees the new guest immediately.
      await refresh();
      toast.show(`Joined ${res.event.name}`);
      navigate(`/events/${res.event.id}`, { replace: true });
    } catch (err) {
      toast.show(err.message, "error");
      setJoining(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted">
        Loading…
      </div>
    );
  }

  if (!user) {
    // Join-by-code never forces account creation: a name gets you in the
    // door, a LinkedIn link makes your card a pointer to your real profile.
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="card p-8 max-w-md w-full">
          <h1 className="text-xl font-bold text-text-primary mb-1">
            Join the event
          </h1>
          <p className="text-sm text-text-secondary mb-6">
            No account needed. Tell the room who you are and you're in.
          </p>
          <form onSubmit={joinAsGuest} className="flex flex-col gap-4">
            <div>
              <label className="label" htmlFor="guest-name">
                Your name *
              </label>
              <input
                id="guest-name"
                className="input"
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                autoFocus
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="guest-linkedin">
                LinkedIn
              </label>
              <input
                id="guest-linkedin"
                className="input"
                value={form.linkedin}
                onChange={(e) =>
                  setForm((f) => ({ ...f, linkedin: e.target.value }))
                }
                placeholder="linkedin.com/in/you"
              />
              <p className="mt-1 text-xs text-text-muted">
                Optional. One link and people can reach you after tonight.
              </p>
            </div>
            <button type="submit" className="btn-primary" disabled={joining}>
              {joining ? "Joining…" : "Join event"}
            </button>
          </form>
          <p className="text-xs text-text-secondary mt-4 text-center">
            Have an account?{" "}
            <Link
              className="text-primary font-bold"
              to="/login"
              state={{ from: `/join/${code}` }}
              onClick={() =>
                sessionStorage.setItem("pending_join_code", code)
              }
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="card p-8 text-center max-w-md">
        <div className="font-bold text-text-primary mb-2">{status}</div>
        <div className="text-sm text-text-secondary">
          Hold tight — we're getting you into the event.
        </div>
      </div>
    </div>
  );
}
