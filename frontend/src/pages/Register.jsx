import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";

export default function Register() {
  const { register } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, name);
      navigate("/profile/setup", { replace: true });
    } catch (err) {
      setError(err.message || "Registration failed");
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
        <h1 className="text-xl font-bold text-text-primary mb-1">Create account</h1>
        <p className="text-sm text-text-secondary mb-6">
          Pick up where the event left off.
        </p>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <div>
            <label className="label">Full name</label>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
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
              minLength={6}
            />
          </div>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-card px-3 py-2">
              {error}
            </div>
          )}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <div className="mt-5 text-sm text-text-secondary text-center">
          Already have an account?{" "}
          <Link to="/login" className="text-primary font-semibold">
            Log in
          </Link>
        </div>
      </div>
    </div>
  );
}
