import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

// react-snap prerenders this page to static HTML at build time and writes it
// back into dist/index.html, so crawlers and link previews get real content
// instead of an empty <div id="root">. If that prerendered markup is present,
// hydrate onto it instead of wiping and re-rendering from scratch.
const rootElement = document.getElementById("root");
const app = (
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

if (rootElement.hasChildNodes()) {
  ReactDOM.hydrateRoot(rootElement, app);
} else {
  ReactDOM.createRoot(rootElement).render(app);
}
