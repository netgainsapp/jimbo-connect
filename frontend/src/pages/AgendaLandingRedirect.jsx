import { useEffect } from "react";

import { MARKETING_URL } from "../components/marketing/marketingLinks.js";

/**
 * The canonical landing page for the Agenda Builder is server rendered on the
 * marketing domain (intro-connect.com/agenda) so that crawlers see real copy
 * without running JavaScript. This app route previously rendered its own
 * version of that page, which would have competed with it as duplicate
 * content on a second hostname.
 *
 * There is one landing URL now, and this sends visitors to it. The interactive
 * builder is unaffected and stays at /agenda/new.
 */
export default function AgendaLandingRedirect() {
  useEffect(() => {
    window.location.replace(`${MARKETING_URL}/agenda`);
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-20 text-center">
      <p className="text-text-muted">Taking you to the Agenda Builder…</p>
      <p className="mt-3 text-sm">
        <a
          className="font-semibold text-primary hover:text-primary-hover"
          href={`${MARKETING_URL}/agenda`}
        >
          Continue
        </a>
      </p>
    </div>
  );
}
