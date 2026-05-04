import { useState } from "react";
import { Link } from "react-router-dom";
import { Copy } from "lucide-react";
import { authApi } from "../lib/api.js";
import { copyToClipboard } from "../lib/utils.js";
import { useToast } from "../hooks/useToast.jsx";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [resetUrl, setResetUrl] = useState("");
  const toast = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await authApi.forgotPassword(email);
      setSubmitted(true);
      // Until automated email is configured, the API returns the URL
      // so the user (or admin) can use/share it directly.
      if (res?.reset_url) setResetUrl(res.reset_url);
    } catch (err) {
      toast.show(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const copyLink = async () => {
    await copyToClipboard(resetUrl);
    toast.show("Reset link copied");
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-bg-secondary">
      <div className="card p-8 w-full max-w-md">
        <h1 className="text-xl font-bold text-text-primary mb-1">
          Reset your password
        </h1>
        <p className="text-sm text-text-secondary mb-6">
          Enter your email and we'll generate a one-time reset link.
        </p>

        {!submitted ? (
          <form onSubmit={submit} className="flex flex-col gap-4">
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? "Generating…" : "Send reset link"}
            </button>
          </form>
        ) : (
          <div className="flex flex-col gap-3">
            <div className="text-sm text-text-secondary">
              If an account exists for <b>{email}</b>, a reset link has been
              generated.
            </div>
            {resetUrl && (
              <div className="card p-3 bg-bg-secondary border-0">
                <div className="text-xs text-text-muted mb-1">
                  Your reset link (transactional email isn't wired up yet —
                  copy and use this directly):
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs break-all bg-white p-2 rounded">
                    {resetUrl}
                  </code>
                  <button onClick={copyLink} className="btn-ghost shrink-0">
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
                <a
                  href={resetUrl.replace(window.location.origin, "")}
                  className="btn-primary w-full mt-3 justify-center"
                >
                  Open link now
                </a>
              </div>
            )}
          </div>
        )}

        <div className="mt-6 text-sm text-text-secondary text-center">
          <Link to="/login" className="text-primary font-semibold">
            ← Back to log in
          </Link>
        </div>
      </div>
    </div>
  );
}
