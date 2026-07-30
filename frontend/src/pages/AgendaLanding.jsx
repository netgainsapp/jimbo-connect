import { Link } from "react-router-dom";
import { ArrowRight, CalendarDays, Download, Users } from "lucide-react";

const STEPS = [
  {
    icon: CalendarDays,
    title: "Add your sessions",
    body: "Enter your event details, then build the schedule one session at a time. Multi day events group by date automatically.",
  },
  {
    icon: Download,
    title: "Download a Word agenda",
    body: "Get a clean, professional document you can edit, print, or send to attendees. It stays fully editable after download.",
  },
  {
    icon: Users,
    title: "Turn it into an event",
    body: "When you are ready, create an Intro Connect event so attendees can find each other and keep in touch afterwards.",
  },
];

export default function AgendaLanding() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12">
      <div className="text-center">
        <span className="rounded-pill bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
          Free tool, no account needed
        </span>
        <h1 className="mt-4 text-3xl font-bold text-text-primary sm:text-4xl">
          Build an event agenda in minutes
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-base text-text-secondary">
          Put your schedule together, preview it as you go, and download a polished Word
          document. Nothing to install and nothing to pay for.
        </p>
        <Link
          to="/agenda/new"
          className="mt-7 inline-flex items-center gap-2 rounded-card bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary-hover"
        >
          Start building an agenda <ArrowRight size={16} />
        </Link>
      </div>

      <div className="mt-14 grid gap-6 sm:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-card border border-border-default bg-white p-5 shadow-card">
            <Icon size={20} className="text-primary" />
            <h2 className="mt-3 text-sm font-semibold text-text-primary">{title}</h2>
            <p className="mt-1.5 text-sm text-text-muted">{body}</p>
          </div>
        ))}
      </div>

      <p className="mt-12 text-center text-sm text-text-muted">
        Already have an agenda started? It is saved on this device.{" "}
        <Link to="/agenda/new" className="font-medium text-primary hover:text-primary-hover">
          Pick up where you left off
        </Link>
      </p>
    </div>
  );
}
