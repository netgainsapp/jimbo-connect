import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { eventsApi } from "../lib/api.js";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const loggedIn = await login(email, password);
      let fallback = "/events";
      if (loggedIn?.is_admin) {
        fallback = "/admin";
      } else {
        try {
          const myEvents = await eventsApi.myEvents();
          if (myEvents.length > 0) fallback = `/events/${myEvents[0].id}`;
        } catch {
          // ignore — fall back to /events
        }
      }
      const from = location.state?.from || fallback;
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-bg-secondary">
      <div className="card p-8 w-full max-w-md">
        <div className="flex items-center gap-2 mb-6">
          <div className="w-10 h-10 rounded-card bg-primary text-white flex items-center justify-center font-bold text-lg">
            J
          </div>
          <div className="text-2xl font-bold tracking-tight">Jimbo Connect</div>
        </div>
        <h1 className="text-xl font-bold text-text-primary mb-1">Welcome back</h1>
        <p className="text-sm text-text-secondary mb-6">
          Log in to keep the conversation going.
        </p>
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
          <div>
            <label className="label">Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-card px-3 py-2">
              {error}
            </div>
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Logging in…" : "Log in"}
          </button>
        </form>
        <div className="mt-4 text-sm text-text-secondary text-center">
          <Link to="/forgot-password" className="hover:text-primary">
            Forgot your password?
          </Link>
        </div>
        <div className="mt-2 text-sm text-text-secondary text-center">
          New to Jimbo Connect?{" "}
          <Link to="/register" className="text-primary font-semibold">
            Create an account
          </Link>
        </div>
      </div>
    </div>
  );
}
