import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Palette } from "lucide-react";
import { brandingApi } from "../lib/api.js";
import { useToast } from "../hooks/useToast.jsx";

/**
 * "Your brand" settings card (Pro): logo upload + accent color with a live
 * preview. Free/Starter see the locked state with a plans link. All guardrails
 * are server-side; this card just reflects them.
 */
export default function BrandCard() {
  const [status, setStatus] = useState(null);
  const [accent, setAccent] = useState("#2563eb");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);
  const toast = useToast();

  const load = async () => {
    try {
      const s = await brandingApi.get();
      setStatus(s);
      if (s.accent) setAccent(s.accent);
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!status) return null;

  if (!status.allowed) {
    return (
      <div className="card p-4 flex items-start gap-3">
        <Palette className="w-5 h-5 text-text-muted mt-0.5 shrink-0" />
        <div>
          <div className="text-sm font-bold text-text-primary">Your brand</div>
          <p className="text-sm text-text-secondary mt-1">
            Pro hosts can put their own logo and color on event pages and guest
            emails.
          </p>
          {!status.locked && (
            <Link
              to="/upgrade"
              className="text-sm font-semibold text-primary hover:underline mt-1 inline-block"
            >
              See plans
            </Link>
          )}
        </div>
      </div>
    );
  }

  const saveAccent = async () => {
    setBusy(true);
    try {
      const s = await brandingApi.setAccent(accent);
      setStatus(s);
      toast.show("Color saved. It now shows on your event pages and emails.");
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  const uploadLogo = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const s = await brandingApi.uploadLogo(file);
      setStatus(s);
      toast.show("Logo saved. It now shows on your event pages and emails.");
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const resetAll = async () => {
    setBusy(true);
    try {
      const s = await brandingApi.reset();
      setStatus(s);
      setAccent("#2563eb");
      toast.show("Branding reset to the Intro Connect default.");
    } catch (e) {
      toast.show(e.message, "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-1">
        <Palette className="w-5 h-5 text-primary" />
        <div className="text-sm font-bold text-text-primary">Your brand</div>
        <span className="pill">Pro</span>
      </div>
      <p className="text-sm text-text-secondary mb-4">
        Your logo and color show on your event pages and guest emails, beside
        Intro Connect.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <span className="label">Logo</span>
          <div className="flex items-center gap-3">
            {status.has_logo && status.logo_url ? (
              <img
                src={status.logo_url}
                alt="Your logo"
                className="h-10 max-w-[140px] object-contain border border-border-default rounded-card p-1 bg-white"
              />
            ) : (
              <span className="text-xs text-text-muted">No logo yet</span>
            )}
            <label className="btn-outline cursor-pointer">
              {status.has_logo ? "Replace" : "Upload"}
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                disabled={busy}
                onChange={(e) => uploadLogo(e.target.files?.[0])}
              />
            </label>
          </div>
          <div className="text-xs text-text-muted mt-1.5">
            PNG, JPEG, or WebP, up to 1 MB.
          </div>
        </div>

        <div>
          <label className="label" htmlFor="brand-accent">
            Accent color
          </label>
          <div className="flex items-center gap-2">
            <input
              id="brand-accent"
              type="color"
              value={accent}
              onChange={(e) => setAccent(e.target.value)}
              className="w-10 h-10 rounded-card border border-border-default cursor-pointer bg-white p-1"
              aria-label="Pick accent color"
            />
            <input
              className="input w-28"
              value={accent}
              onChange={(e) => setAccent(e.target.value)}
              aria-label="Accent color hex value"
            />
            <button className="btn-primary" onClick={saveAccent} disabled={busy}>
              Save color
            </button>
          </div>
          {status.accent_dark && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-text-muted">Button preview:</span>
              <span
                className="inline-flex items-center px-4 py-1.5 rounded-pill text-white text-xs font-semibold"
                style={{ background: status.accent_dark }}
              >
                Join the event
              </span>
            </div>
          )}
        </div>
      </div>

      {(status.has_logo || status.accent) && (
        <button
          onClick={resetAll}
          disabled={busy}
          className="text-xs font-semibold text-text-secondary hover:text-red-500 mt-4"
        >
          Reset to Intro Connect default
        </button>
      )}
    </div>
  );
}
