import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CalendarPlus,
  UserPlus,
  Image as ImageIcon,
  Mail,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import Modal from "./Modal.jsx";

const STORAGE_KEY = "jimbo_admin_welcome_seen_v1";

export function shouldShowWelcome() {
  try {
    return !localStorage.getItem(STORAGE_KEY);
  } catch {
    return false;
  }
}

export function markWelcomeSeen() {
  try {
    localStorage.setItem(STORAGE_KEY, new Date().toISOString());
  } catch {
    // ignore
  }
}

const STEPS = [
  {
    icon: CalendarPlus,
    title: "Create an event",
    body: "Click Events → New event. Set a name, date, and location. We'll generate an 8-character join code automatically.",
  },
  {
    icon: UserPlus,
    title: "Import your attendee list",
    body: "Right after you create the event, paste names from anywhere — emails one per line, or a CSV from Eventbrite, Mailchimp, or a spreadsheet. We'll create accounts and email-able temp passwords.",
  },
  {
    icon: ImageIcon,
    title: "Add sponsors with a single URL",
    body: "On the event page, paste any sponsor's website URL. We'll fetch their logo, headline, and description automatically. No uploads.",
  },
  {
    icon: Mail,
    title: "Send invitations from email templates",
    body: "Open Templates → pick \"You're in\" or \"Save the date\" → click \"Open in mail\". Your default email client opens with everyone BCC'd and the event details filled in.",
  },
];

export default function WelcomeModal({ open, onClose, hostName }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (open) setStep(0);
  }, [open]);

  const close = () => {
    markWelcomeSeen();
    onClose?.();
  };

  if (!open) return null;
  const last = step === STEPS.length - 1;
  const current = STEPS[step];
  const Icon = current.icon;

  return (
    <Modal open={open} onClose={close} maxWidth="max-w-xl">
      <div className="p-6">
        <div className="flex items-center gap-2 text-primary text-xs font-bold uppercase tracking-wider">
          <Sparkles className="w-4 h-4" /> Welcome
        </div>
        <h2 className="text-2xl font-bold text-text-primary mt-1">
          Hey Jimbo... here's the 60-second tour.
        </h2>
        <p className="text-sm text-text-secondary mt-1">
          Jimbo Connect turns the people at your events into a private,
          searchable directory that lives forever. Free and easy for everyone.
        </p>

        <div className="mt-6 card p-5 bg-bg-secondary border-0">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-card bg-white text-primary flex items-center justify-center shrink-0">
              <Icon className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="text-xs text-text-muted font-semibold">
                Step {step + 1} of {STEPS.length}
              </div>
              <div className="font-bold text-text-primary text-lg">
                {current.title}
              </div>
              <p className="text-sm text-text-secondary mt-1 leading-relaxed">
                {current.body}
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-center gap-1.5 mt-4">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? "w-8 bg-primary" : "w-1.5 bg-border-default"
              }`}
            />
          ))}
        </div>

        <div className="flex items-center justify-between mt-6">
          <button onClick={close} className="btn-ghost text-sm">
            Skip tour
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button onClick={() => setStep(step - 1)} className="btn-ghost">
                Back
              </button>
            )}
            {!last ? (
              <button onClick={() => setStep(step + 1)} className="btn-primary">
                Next
              </button>
            ) : (
              <Link to="/admin/events" onClick={close} className="btn-primary">
                <CheckCircle2 className="w-4 h-4" /> Create my first event
              </Link>
            )}
          </div>
        </div>

        <div className="mt-6 pt-5 border-t border-border-default">
          <div className="text-xs uppercase tracking-wider text-text-muted font-semibold mb-2">
            Try it as an attendee
          </div>
          <p className="text-xs text-text-secondary">
            Log out and log back in with{" "}
            <code className="bg-bg-secondary px-1 py-0.5 rounded">
              ava@example.com
            </code>{" "}
            (or ben/cara/diego/elena @example.com) — password{" "}
            <code className="bg-bg-secondary px-1 py-0.5 rounded">password123</code>{" "}
            — to see the directory from an attendee's eyes.
          </p>
        </div>
      </div>
    </Modal>
  );
}
