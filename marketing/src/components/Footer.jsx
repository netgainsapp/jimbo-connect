import { Mark } from "./Logo.jsx";

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="container-prose py-12">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-6 text-sm">
          <div className="flex items-center gap-3">
            <Mark size={28} />
            <div className="leading-none">
              <div className="font-extrabold text-ink tracking-tight">
                Intro <span className="font-medium">Connect</span>
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] font-bold text-stone mt-1">
                © 2026 Intro Connect
              </div>
            </div>
          </div>
          <div className="flex items-center gap-5 text-stone">
            <a href="#features" className="hover:text-ink font-semibold">
              Features
            </a>
            <a href="#pricing" className="hover:text-ink font-semibold">
              Pricing
            </a>
            <a href="#faq" className="hover:text-ink font-semibold">
              FAQ
            </a>
            <a href="/privacy.html" className="hover:text-ink font-semibold">
              Privacy
            </a>
            <a href="/terms.html" className="hover:text-ink font-semibold">
              Terms
            </a>
            <a
              href="mailto:hello@frontrangedev.co"
              className="hover:text-ink font-semibold"
            >
              Contact
            </a>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-line text-center">
          <div className="text-[10px] uppercase tracking-[0.22em] font-extrabold text-primary">
            Host better. Connect deeper. Build what matters.
          </div>
        </div>
      </div>
    </footer>
  );
}
