import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

/**
 * Attendee to host loop. Someone browsing a directory has already felt the
 * product work, which makes them the warmest host prospect we will ever get.
 * Shown only to people who host nothing yet, and it links into the in-app
 * create flow (not the marketing site) so the next click is the event itself.
 */
export default function HostCta({ className = "" }) {
  return (
    <div
      className={`rounded-card bg-primary text-white p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-5 ${className}`}
    >
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-[0.2em] font-bold text-white/80">
          For hosts
        </div>
        <div className="text-xl font-bold mt-1">Run your own events?</div>
        <p className="text-white/85 text-sm mt-1 max-w-md leading-relaxed">
          Intro Connect turns any event you host into a private directory like
          this one, so your guests stay connected long after the night ends.
          Your first event is free.
        </p>
      </div>
      <Link
        to="/events?host=1"
        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-pill bg-white text-primary font-bold hover:bg-white/90 transition shrink-0"
      >
        Host your own event <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
