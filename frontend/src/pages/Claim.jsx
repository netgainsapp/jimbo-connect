import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { claimApi, profileApi } from "../lib/api.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import AttendeeImportModal from "../components/AttendeeImportModal.jsx";
import { MAX_SOURCE_BYTES, shrinkImageFile } from "../lib/image.js";
import { safeNext } from "../lib/nextPath.js";
import {
  claimBody,
  failureView,
  isValidEmail,
  nextStepAfterImport,
  viewFor,
} from "../lib/claimState.js";

const CONTACT_EMAIL = "hello@intro-connect.com";

function Shell({ children }) {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-bg-secondary">
      <div className="card p-8 w-full max-w-md">{children}</div>
    </div>
  );
}

function DeadLink() {
  return (
    <Shell>
      <h1 className="text-xl font-bold text-text-primary mb-2">
        This link is no longer active.
      </h1>
      <p className="text-sm text-text-secondary">
        Write to{" "}
        <a href={`mailto:${CONTACT_EMAIL}`} className="text-primary font-semibold">
          {CONTACT_EMAIL}
        </a>{" "}
        and we will help.
      </p>
    </Shell>
  );
}

function ErrorNote({ message, loginNext }) {
  return (
    <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-card px-3 py-2">
      {message}
      {loginNext && (
        <>
          {" "}
          <Link
            to={`/login?next=${encodeURIComponent(loginNext)}`}
            className="font-semibold underline"
          >
            Log in
          </Link>
        </>
      )}
    </div>
  );
}

function EmailForm({ event, host, onSubmit, submitting, error }) {
  const [form, setForm] = useState({ email: "", name: host?.name || "" });
  const [invalid, setInvalid] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = (e) => {
    e.preventDefault();
    if (!isValidEmail(form.email)) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    onSubmit(claimBody(form));
  };

  return (
    <Shell>
      <h1 className="text-xl font-bold text-text-primary mb-1">{event.name}</h1>
      <p className="text-sm text-text-secondary mb-6">
        Your event page is ready. Enter your email to take it over.
      </p>
      <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
        <div>
          <label className="label" htmlFor="claim-email">Email</label>
          <input
            id="claim-email"
            type="email"
            className="input"
            value={form.email}
            onChange={set("email")}
            autoComplete="email"
            autoFocus
            required
          />
          {invalid && (
            <p className="text-xs text-red-600 mt-1">Enter a valid email address.</p>
          )}
        </div>
        <div>
          <label className="label" htmlFor="claim-name">Your name (optional)</label>
          <input
            id="claim-name"
            className="input"
            value={form.name}
            onChange={set("name")}
            autoComplete="name"
            maxLength={100}
          />
        </div>
        {error && <ErrorNote message={error.message} loginNext={error.loginNext} />}
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Setting things up…" : "Claim my event"}
        </button>
      </form>
    </Shell>
  );
}

function ConfirmClaim({ event, onConfirm, submitting, error }) {
  return (
    <Shell>
      <h1 className="text-xl font-bold text-text-primary mb-1">{event.name}</h1>
      <p className="text-sm text-text-secondary mb-6">
        Your event page is ready. Set it up to add your attendee list.
      </p>
      {error && (
        <div className="mb-4">
          <ErrorNote message={error.message} loginNext={error.loginNext} />
        </div>
      )}
      <button
        type="button"
        className="btn-primary w-full"
        onClick={() => onConfirm({})}
        disabled={submitting}
      >
        {submitting ? "Setting things up…" : "Set up my event"}
      </button>
    </Shell>
  );
}

function PhotoStep({ onDone }) {
  const toast = useToast();
  const { refresh } = useAuth();
  const [uploading, setUploading] = useState(false);

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > MAX_SOURCE_BYTES) {
      toast.show("That file is too large. Try a normal photo.", "error");
      return;
    }
    setUploading(true);
    try {
      await profileApi.uploadPhoto(await shrinkImageFile(file));
      await refresh();
      onDone();
    } catch (err) {
      toast.show(err?.message || "That photo did not upload.", "error");
      setUploading(false);
    }
  };

  return (
    <Shell>
      <h1 className="text-xl font-bold text-text-primary mb-6">
        Add your photo so your guests see you, not us.
      </h1>
      <div className="flex flex-col gap-3">
        <label className={`btn-primary text-center cursor-pointer ${uploading ? "opacity-60 pointer-events-none" : ""}`}>
          {uploading ? "Uploading…" : "Choose a photo"}
          <input type="file" accept="image/*" className="sr-only" onChange={onFile} disabled={uploading} />
        </label>
        <button type="button" className="btn-outline" onClick={onDone} disabled={uploading}>
          Skip for now
        </button>
      </div>
    </Shell>
  );
}

export default function Claim() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [view, setView] = useState({ view: "loading" });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [claimed, setClaimed] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [step, setStep] = useState("import");
  const ran = useRef(false);

  const complete = useCallback(
    async (body) => {
      setSubmitting(true);
      setFormError(null);
      try {
        const res = await claimApi.complete(token, body);
        // The cookie is set server side; pull it into the auth context so
        // RequireAuth on the event page does not bounce to /login.
        await refresh();
        setClaimed(res);
        setImportOpen(true);
      } catch (err) {
        const failed = failureView(err);
        if (failed.view === "dead") {
          setView(failed);
        } else {
          const loginNext = failed.login ? `/claim/${token}` : null;
          setFormError({ message: failed.message, loginNext });
          // The form and the confirm view show the error in place.
          setView((v) => (v.view === "form" || v.view === "confirm" ? v : failed));
        }
      } finally {
        setSubmitting(false);
      }
    },
    [token, refresh],
  );

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    claimApi
      .get(token)
      // Never posts here: the confirm view waits for the host's click.
      .then((res) => setView(viewFor(res)))
      .catch((err) => setView(failureView(err)));
  }, [token]);

  const finish = () => navigate(safeNext(claimed?.redirect), { replace: true });

  const closeImport = async () => {
    setImportOpen(false);
    const me = await refresh();
    if (nextStepAfterImport(me) === "photo") setStep("photo");
    else finish();
  };

  if (claimed) {
    if (step === "photo") return <PhotoStep onDone={finish} />;
    return (
      <>
        <Shell>
          <h1 className="text-xl font-bold text-text-primary mb-2">{claimed.event?.name}</h1>
          <p className="text-sm text-text-secondary">
            This event was set up for you. Add your attendee list to go live.
          </p>
        </Shell>
        <AttendeeImportModal
          open={importOpen}
          onClose={closeImport}
          eventId={claimed.event?.id}
        />
      </>
    );
  }

  if (view.view === "dead") return <DeadLink />;
  if (view.view === "form") {
    return (
      <EmailForm
        event={view.event}
        host={view.host}
        onSubmit={complete}
        submitting={submitting}
        error={formError}
      />
    );
  }
  if (view.view === "confirm") {
    return (
      <ConfirmClaim
        event={view.event}
        onConfirm={complete}
        submitting={submitting}
        error={formError}
      />
    );
  }
  if (view.view === "error") {
    return (
      <Shell>
        <ErrorNote message={view.message} loginNext={formError?.loginNext} />
        <button
          type="button"
          className="btn-outline w-full mt-4"
          onClick={() => window.location.reload()}
        >
          Try again
        </button>
      </Shell>
    );
  }
  return (
    <Shell>
      <p className="text-sm text-text-secondary text-center">
        Loading…
      </p>
    </Shell>
  );
}
