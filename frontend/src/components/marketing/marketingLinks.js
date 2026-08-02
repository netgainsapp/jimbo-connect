// Chrome for public pages served out of the app (currently the Agenda Builder),
// matching the marketing site at intro-connect.com.
//
// The critical detail: this app is served from app.intro-connect.com, so every
// marketing link has to be ABSOLUTE. A bare "#pricing" or "/blog" here would
// resolve against app.intro-connect.com and 404 or bounce to /login. This is
// the same trap the server rendered /blog and /news chrome hit, where anchors
// had to be rewritten to route through the marketing origin first.
export const MARKETING_URL =
  process.env.REACT_APP_MARKETING_URL || "https://intro-connect.com";

const at = (path) => `${MARKETING_URL}${path}`;

export const NAV_LINKS = [
  { href: at("/#how"), label: "How it works" },
  { href: at("/#features"), label: "Features" },
  { href: at("/#pricing"), label: "Pricing" },
  // Anchors to the section, deliberately NOT to the PDF: the form is the only
  // lead capture the site has. Same reasoning as marketing/Nav.jsx.
  { href: at("/#one-pager"), label: "One pager" },
  { href: at("/#faq"), label: "FAQ" },
  { href: at("/agenda"), label: "Agenda Builder" },
  { href: at("/blog"), label: "Blog" },
  { href: at("/news"), label: "News" },
];

export const FOOTER_LINKS = [
  { href: at("/#features"), label: "Features" },
  { href: at("/#pricing"), label: "Pricing" },
  { href: at("/#faq"), label: "FAQ" },
  { href: at("/agenda"), label: "Agenda Builder" },
  { href: at("/blog"), label: "Blog" },
  { href: at("/news"), label: "News" },
  { href: at("/privacy.html"), label: "Privacy" },
  { href: at("/terms.html"), label: "Terms" },
  { href: "mailto:hello@intro-connect.com", label: "Contact" },
];

export const TAGLINE = "Host better. Connect deeper. Build what matters.";
