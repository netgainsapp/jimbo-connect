import { useState } from "react";
import { MailWarning, X } from "lucide-react";
import { useAuth } from "../hooks/useAuth.jsx";
import { authApi } from "../lib/api.js";

// Until this existed, email verification was a flag that got set on signup and
// then never read anywhere: the token and the resend endpoint both worked, but
// nothing in the UI mentioned them. A typo'd address looked like a healthy
// account while every invitation, announcement and password reset silently went
// nowhere. This nudges without gating, so signup stays frictionless.
export default function VerifyEmailBanner() {
  const { user } = useAuth();
  // Session-scoped so it does not nag on every route change, but returns on the
  // next visit. Verifying is what makes it go away for good.
  const [hidden, setHidden] = useState(
    () => sessionStorage.getItem("hideVerifyBanner") === "1"
  );
  const [state, setState] = useState("idle"); // idle | sending | sent | error
  const [error, setError] = useState("");

  // Admins are created server side and never go through the email flow.
  if (!user || user.is_admin || user.email_verified || hidden) return null;

  const dismiss = () => {
    sessionStorage.setItem("hideVerifyBanner", "1");
    setHidden(true);
  };

  const resend = async () => {
    if (state === "sending") return;
    setState("sending");
    setError("");
    try {
      const r = await authApi.resendVerification();
      setState(r?.already_verified ? "sent" : "sent");
    } catch (err) {
      setState("error");
      setError(
        err.status === 429
          ? "That is a few too many for now. Try again in an hour."
          : err.message || "Could not send it. Try again in a moment."
      );
    }
  };

  return (
    <div className="bg-amber-50 border-b border-amber-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-2.5 flex items-center gap-3 text-sm">
        <MailWarning className="w-4 h-4 text-amber-700 shrink-0" />
        <p className="text-amber-900 flex-1 min-w-0">
          {state === "sent" ? (
            <>
              Sent. Check <span className="font-semibold">{user.email}</span> and
              click the link to confirm it is yours.
            </>
          ) : (
            <>
              <span className="font-semibold">Confirm your email.</span> We sent
              a link to {user.email}. Until you click it we cannot be sure we
              can reach you, so invitations and password resets may not arrive.
            </>
          )}
        </p>
        <div className="flex items-center gap-1 shrink-0">
          {state !== "sent" && (
            <button
              onClick={resend}
              disabled={state === "sending"}
              className="px-3 py-1 rounded-pill text-sm font-bold text-amber-900 hover:bg-amber-100 disabled:opacity-60 whitespace-nowrap"
            >
              {state === "sending" ? "Sending…" : "Resend"}
            </button>
          )}
          <button
            onClick={dismiss}
            aria-label="Dismiss"
            className="p-1 rounded-pill text-amber-700 hover:bg-amber-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div aria-live="polite">
        {state === "error" && (
          <p className="max-w-6xl mx-auto px-4 sm:px-6 pb-2 text-sm text-red-700">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
