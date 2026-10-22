import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { authApi } from "../lib/api.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { magicDestination } from "../lib/magicLink.js";

/**
 * The button in a "message waiting" email lands here. Public by design: the
 * guest has no session yet. The token is single use, so nothing happens until
 * the guest presses the button; a link scanner that opens the page on
 * delivery leaves the token unspent.
 */
export default function MagicLogin() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [dead, setDead] = useState(false);

  const open = async () => {
    setSubmitting(true);
    try {
      await authApi.magicLogin(token);
      // The cookie is set server side; pull it into the auth context so
      // RequireAuth on the messages page does not bounce to /login.
      await refresh();
      navigate(magicDestination(searchParams.get("next")), { replace: true });
    } catch {
      setDead(true);
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-bg-secondary">
      <div className="card p-8 w-full max-w-md">
        {dead ? (
          <>
            <h1 className="text-xl font-bold text-text-primary mb-2">
              This link is no longer active.
            </h1>
            <p className="text-sm text-text-secondary">
              <Link to="/login" className="text-primary font-semibold">
                Log in
              </Link>{" "}
              to read your messages.
            </p>
          </>
        ) : (
          <>
            <h1 className="text-xl font-bold text-text-primary mb-6">
              Someone sent you a message.
            </h1>
            <button
              type="button"
              className="btn-primary w-full"
              onClick={open}
              disabled={submitting}
            >
              {submitting ? "Opening…" : "Open your message"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
