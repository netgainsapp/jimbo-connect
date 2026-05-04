import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { authApi, setToken } from "../lib/api.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";

export default function ResetPassword() {
  const { token } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const { refresh } = useAuth();
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [magicSubmitting, setMagicSubmitting] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await authApi.resetPassword(token, password);
      if (res?.token) setToken(res.token);
      await refresh();
      toast.show("Password updated");
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const magicLogin = async () => {
    setError("");
    setMagicSubmitting(true);
    try {
      const res = await authApi.magicLogin(token);
      if (res?.token) setToken(res.token);
      await refresh();
      toast.show("Logged in");
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setMagicSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-bg-secondary">
      <div className="card p-8 w-full max-w-md">
        <h1 className="text-xl font-bold text-text-primary mb-1">
          Set a new password
        </h1>
        <p className="text-sm text-text-secondary mb-6">
          Or skip it — just log me in with this link.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <label className="label">New password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoFocus
            />
          </div>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-card px-3 py-2">
              {error}
            </div>
          )}
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Saving…" : "Save & log in"}
          </button>
          <button
            type="button"
            onClick={magicLogin}
            disabled={magicSubmitting}
            className="btn-outline"
          >
            {magicSubmitting ? "Logging in…" : "Just log me in (skip password)"}
          </button>
        </form>

        <div className="mt-6 text-sm text-text-secondary text-center">
          <Link to="/login" className="text-primary font-semibold">
            ← Back to log in
          </Link>
        </div>
      </div>
    </div>
  );
}
