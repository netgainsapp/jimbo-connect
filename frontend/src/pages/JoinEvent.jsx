import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { eventsApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { profileComplete } from "../lib/utils.js";

export default function JoinEvent() {
  const { code } = useParams();
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [status, setStatus] = useState("Joining…");
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

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-text-muted">
        Loading…
      </div>
    );
  }
  if (!user) {
    sessionStorage.setItem("pending_join_code", code);
    return <Navigate to={`/login`} state={{ from: `/join/${code}` }} replace />;
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
