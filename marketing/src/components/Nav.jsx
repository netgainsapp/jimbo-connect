import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Lockup } from "./Logo.jsx";

const LINKS = [
  { href: "#how", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-40 bg-white/85 backdrop-blur border-b border-line">
      <div className="container-prose h-16 flex items-center justify-between">
        <a href="#" className="flex items-center">
          <Lockup size="sm" />
        </a>
        <div className="hidden md:flex items-center gap-1">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="px-3 py-1.5 rounded-pill text-sm font-semibold text-stone hover:text-ink hover:bg-cream transition"
            >
              {l.label}
            </a>
          ))}
        </div>
        <div className="hidden md:flex items-center gap-2">
          <a
            href="https://jimbo.frontrangedev.co"
            className="btn-ghost"
            target="_blank"
            rel="noopener"
          >
            Log in
          </a>
          <a href="#pricing" className="btn-primary">
            Start for free
          </a>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="md:hidden p-2 rounded-pill hover:bg-cream"
          aria-label="Menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>
      {open && (
        <div className="md:hidden border-t border-line bg-white">
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
              href="https://jimbo.frontrangedev.co"
              target="_blank"
              rel="noopener"
              className="px-3 py-2 rounded-card text-sm font-semibold text-stone hover:bg-cream"
            >
              Log in
            </a>
            <a href="#pricing" className="btn-primary mt-2">
              Start for free
            </a>
          </div>
        </div>
      )}
    </nav>
  );
}
