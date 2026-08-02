import { useEffect } from "react";

/**
 * Scroll to the element named in the URL hash, after React has rendered it.
 *
 * Why this is needed: the site is a React app, and arriving at "/#faq" from
 * another page (the FAQ link in the blog and news chrome does exactly this)
 * means the browser looks for #faq while the document is still an empty root
 * div. It finds nothing, gives up silently, and the visitor lands at the top of
 * the homepage wondering where the FAQ went. The browser does not retry once
 * the content appears.
 *
 * Runs on mount and on hashchange, so both a cold arrival and a same-page click
 * are covered. rAF gives layout one frame to settle before measuring, which
 * matters because sections above the target contain images that change height
 * as they load.
 */
export function useHashScroll() {
  useEffect(() => {
    const jump = () => {
      const id = decodeURIComponent(window.location.hash.replace("#", "")).trim();
      if (!id) return;
      const target = document.getElementById(id);
      if (!target) return;
      requestAnimationFrame(() => {
        // "auto", not "smooth": a cold arrival should already be there, not
        // scroll the whole page in front of someone who just clicked a link.
        target.scrollIntoView({ behavior: "auto", block: "start" });
      });
    };

    jump();
    window.addEventListener("hashchange", jump);
    return () => window.removeEventListener("hashchange", jump);
  }, []);
}
