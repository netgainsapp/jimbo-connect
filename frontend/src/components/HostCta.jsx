import { ArrowRight } from "lucide-react";

// Product-led growth: attendees already love the directory, so invite them to
// become hosts. Points at the marketing site (update when the brand domain is
// live).
const MARKETING_URL = "https://jimbo-connect.vercel.app";

export default function HostCta() {
  return (
    <div className="mt-8 rounded-card bg-primary text-white p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-5">
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-[0.2em] font-bold text-white/80">
          For hosts
        </div>
        <div className="text-xl font-bold mt-1">Run your own events?</div>
        <p className="text-white/85 text-sm mt-1 max-w-md leading-relaxed">
          Intro Connect turns any event you host into a private directory like
          this one, so your guests stay connected long after the night ends.
        </p>
      </div>
      <a
        href={MARKETING_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-pill bg-white text-primary font-bold hover:bg-white/90 transition shrink-0"
      >
        See how hosting works <ArrowRight className="w-4 h-4" />
      </a>
    </div>
  );
}
