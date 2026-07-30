import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";

import { Mark } from "../Logo.jsx";
import { MARKETING_URL, NAV_LINKS } from "./marketingLinks.js";

const linkClass =
  "px-3 py-1.5 rounded-pill text-sm font-semibold text-text-secondary " +
  "transition hover:text-text-primary hover:bg-bg-secondary";

// Rebuilt against this app's Tailwind tokens rather than copied from
// marketing/src/components/Nav.jsx: that file uses the marketing site's own
// token set (border-line, text-ink, text-stone, container-prose), none of
// which exist in this config. Same chrome, expressed in the local vocabulary.
export default function MarketingNav() {
  const [open, setOpen] = useState(false);

  return (
    <nav
      aria-label="Main navigation"
      className="sticky top-0 z-40 border-b border-border-default bg-white/85 backdrop-blur"
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <a href={MARKETING_URL} className="flex items-center gap-2">
          <Mark size={28} />
          <span className="text-base font-extrabold tracking-tight text-text-primary">
            Intro <span className="font-medium">Connect</span>
          </span>
        </a>

        <div className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className={linkClass}>
              {l.label}
            </a>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          {/* Log in and Start for free stay INTERNAL. The marketing site points
              these at app.intro-connect.com, but we are already there, so an
              absolute link would leave and immediately come back. */}
          <Link
            to="/login"
            className="rounded-pill px-4 py-2 text-sm font-semibold text-text-secondary transition hover:bg-bg-secondary hover:text-text-primary"
          >
            Log in
          </Link>
          <Link
            to="/register"
            className="rounded-pill bg-primary px-4 py-2 text-sm font-semibold text-white transition hover:bg-primary-hover"
          >
            Start for free
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="rounded-pill p-2 hover:bg-bg-secondary md:hidden"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          aria-controls="marketing-mobile-menu"
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {open && (
        <div id="marketing-mobile-menu" className="border-t border-border-default bg-white md:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-3">
            {NAV_LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="rounded-card px-3 py-2 text-sm font-semibold text-text-secondary hover:bg-bg-secondary hover:text-text-primary"
              >
                {l.label}
              </a>
            ))}
            <Link
              to="/login"
              onClick={() => setOpen(false)}
              className="rounded-card px-3 py-2 text-sm font-semibold text-text-secondary hover:bg-bg-secondary"
            >
              Log in
            </Link>
            <Link
              to="/register"
              onClick={() => setOpen(false)}
              className="mt-2 rounded-pill bg-primary px-4 py-2 text-center text-sm font-semibold text-white hover:bg-primary-hover"
            >
              Start for free
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
