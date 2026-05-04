import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { profileComplete } from "../lib/utils.js";

export default function RequireAuth({ children, adminOnly = false, allowIncompleteProfile = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-text-muted">Loading…</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (adminOnly && !user.is_admin) {
    return <Navigate to="/events" replace />;
  }

  if (
    !allowIncompleteProfile &&
    !user.is_admin &&
    !profileComplete(user.profile)
  ) {
    return <Navigate to="/profile/setup" replace />;
  }

  return children;
}
