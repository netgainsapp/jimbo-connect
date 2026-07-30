import { Mark } from "../Logo.jsx";
import { FOOTER_LINKS, TAGLINE } from "./marketingLinks.js";

// Mirrors marketing/src/components/Footer.jsx. Note this deliberately carries
// no Front Range Dev Co credit: that belongs to the app's own footer, and the
// marketing chrome does not include it.
export default function MarketingFooter() {
  return (
    <footer className="border-t border-border-default">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <div className="flex flex-col items-center justify-between gap-6 text-sm sm:flex-row">
          <div className="flex items-center gap-3">
            <Mark size={28} />
            <div className="leading-none">
              <div className="font-extrabold tracking-tight text-text-primary">
                Intro <span className="font-medium">Connect</span>
              </div>
              <div className="mt-1 text-[10px] font-bold uppercase tracking-[0.18em] text-text-muted">
                © 2026 Intro Connect
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-text-muted">
            {FOOTER_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="font-semibold hover:text-text-primary">
                {l.label}
              </a>
            ))}
          </div>
        </div>

        <div className="mt-8 border-t border-border-default pt-6 text-center">
          <div className="text-[10px] font-extrabold uppercase tracking-[0.22em] text-primary">
            {TAGLINE}
          </div>
        </div>
      </div>
    </footer>
  );
}
