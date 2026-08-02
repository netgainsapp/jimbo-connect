import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Lockup } from "./Logo.jsx";

const LINKS = [
  { href: "#how", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
  // Anchors to the section, deliberately NOT straight to the PDF: the form is
  // the only place the site captures a lead, and a direct file link would
  // hand over the one pager and skip it.
  { href: "#one-pager", label: "One pager" },
  { href: "#faq", label: "FAQ" },
  // Free tool. A linkable tool page is the strongest organic surface the site
  // has, so it gets a nav slot rather than being buried in the footer.
  { href: "/agenda", label: "Agenda Builder" },
  { href: "/blog", label: "Blog" },
  // News removed 2026-08-02, owner decision: the section is retired. The route
  // and the engine still exist; nothing on the site points at them.
];

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <nav
      aria-label="Main navigation"
      className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-line"
    >
      <div className="container-prose h-16 flex items-center justify-between">
        <a href="#" className="flex items-center">
          <Lockup size="sm" />
        </a>
        <div className="hidden lg:flex items-center gap-1">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="px-3 py-1.5 rounded-pill text-sm font-semibold text-stone hover:text-ink hover:bg-cream whitespace-nowrap transition"
            >
              {l.label}
            </a>
          ))}
        </div>
        <div className="hidden lg:flex items-center gap-2">
          <a
            href="https://app.intro-connect.com"
            className="btn-ghost whitespace-nowrap"
            target="_blank"
            rel="noopener"
          >
            Log in
          </a>
          {/* Plain blue text rather than .btn-primary. A pill with fixed
              padding cannot shrink, so at in-between widths the label wrapped
              inside it and the button rendered as a tall blob. Text has no
              shape to lose. The pill is still right in the hero and pricing,
              where there is room for it. */}
          <a
            href="#pricing"
            className="px-3 py-1.5 text-sm font-bold text-primary hover:text-primary-hover whitespace-nowrap transition"
          >
            Start for free
          </a>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="lg:hidden p-2 rounded-pill hover:bg-cream"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          aria-controls="mobile-menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
      {open && (
        <div id="mobile-menu" className="lg:hidden border-t border-line bg-white">
          <div className="container-prose py-3 flex flex-col gap-1">
            {LINKS.map((l) => (
              <a
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="px-3 py-2 rounded-card text-sm font-semibold text-stone hover:text-ink hover:bg-cream"
              >
                {l.label}
              </a>
            ))}
            <a
              href="https://app.intro-connect.com"
              target="_blank"
              rel="noopener"
              className="px-3 py-2 rounded-card text-sm font-semibold text-stone hover:bg-cream"
            >
              Log in
            </a>
            <a
              href="#pricing"
              className="px-3 py-2 rounded-card text-sm font-bold text-primary hover:bg-cream"
            >
              Start for free
            </a>
          </div>
        </div>
      )}
    </nav>
  );
}
