// vite.config.js define-replaces process.env.REACT_APP_BACKEND_URL with the
// build-time literal (Render sets it via render.yaml; loadEnv with an empty
// prefix pulls it in). Do NOT wrap this in a `typeof process` runtime guard:
// `process` is undefined in the browser bundle, so the guard is always false
// and the app silently falls back to localhost:8001, breaking every API call.
const BACKEND_URL =
  process.env.REACT_APP_BACKEND_URL || "http://localhost:8001";

// Public blog pages are server-rendered by the backend (and proxied onto the
// marketing domain). Used for the admin "View" link on published posts.
export function blogPublicUrl(slug) {
  return `${BACKEND_URL}/blog/${slug}`;
}

// Auth rides the httpOnly session cookie set by the backend (see
// credentials: "include" below). The token is never kept in localStorage or
// sent as a Bearer header, so a script injection cannot read or exfiltrate it.

// Endpoints where a 401 is a normal outcome for a logged-out visitor (bad
// credentials, cold-start session probe), not an expired session.
const EXPECTED_401_PATHS = new Set([
  "/api/auth/login",
  "/api/auth/register",
  "/api/auth/me",
]);

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const res = await fetch(`${BACKEND_URL}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
  if (!res.ok) {
    if (res.status === 401 && !EXPECTED_401_PATHS.has(path)) {
      // A protected call was rejected: the session cookie expired or is
      // invalid. Tell the app so AuthProvider resets the user, which makes
      // RequireAuth bounce to /login.
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("auth:expired"));
      }
    }
    let detail = "Request failed";
    try {
      const data = await res.json();
      detail = data.detail || JSON.stringify(data);
    } catch {
      detail = res.statusText;
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  get: (path) => request(path, { method: "GET" }),
  post: (path, body) =>
    request(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: (path, body) =>
    request(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: (path) => request(path, { method: "DELETE" }),
};

export const authApi = {
  register: (data) => api.post("/api/auth/register", data),
  login: (data) => api.post("/api/auth/login", data),
  logout: () => api.post("/api/auth/logout"),
  me: () => api.get("/api/auth/me"),
  forgotPassword: (email) => api.post("/api/auth/forgot-password", { email }),
  resetPassword: (token, new_password) =>
    api.post("/api/auth/reset-password", { token, new_password }),
  magicLogin: (token) => api.get(`/api/auth/magic/${token}`),
};

export const profileApi = {
  get: () => api.get("/api/profile"),
  update: (data) => api.put("/api/profile", data),
  uploadPhoto: (photo_data) => api.post("/api/profile/photo", { photo_data }),
  getById: (id) => api.get(`/api/profile/${id}`),
  deleteSelf: () => api.del("/api/profile"),
};

export const eventsApi = {
  create: (data) => api.post("/api/events", data),
  list: () => api.get("/api/events"),
  get: (id) => api.get(`/api/events/${id}`),
  update: (id, data) => api.put(`/api/events/${id}`, data),
  remove: (id) => api.del(`/api/events/${id}`),
  join: (code) => api.post(`/api/events/join/${code}`),
  attendees: (id) => api.get(`/api/events/${id}/attendees`),
  removeAttendee: (eventId, userId) =>
    api.del(`/api/events/${eventId}/attendees/${userId}`),
  leave: (eventId) => api.del(`/api/my-events/${eventId}`),
  myEvents: () => api.get("/api/my-events"),
  myHostedEvents: () => api.get("/api/my-hosted-events"),
  invite: (id, emails) => api.post(`/api/events/${id}/invite`, { emails }),
  allMyAttendees: () => api.get("/api/my-attendees"),
  discover: () => api.get("/api/events/discoverable"),
  requestInvite: (id, message = "") =>
    api.post(`/api/events/${id}/request-invite`, { message }),
};

export const contactsApi = {
  save: (contact_id, note = "") =>
    api.post("/api/contacts/save", { contact_id, note }),
  remove: (contact_id) => api.del(`/api/contacts/${contact_id}`),
  list: () => api.get("/api/contacts"),
  updateNote: (contact_id, note) =>
    api.put(`/api/contacts/${contact_id}/note`, { note }),
  isSaved: (contact_id) => api.get(`/api/contacts/${contact_id}/is-saved`),
};

export const sponsorsApi = {
  list: (eventId) => api.get(`/api/events/${eventId}/sponsors`),
  create: (eventId, data) => api.post(`/api/events/${eventId}/sponsors`, data),
  update: (eventId, sponsorId, data) =>
    api.put(`/api/events/${eventId}/sponsors/${sponsorId}`, data),
  refresh: (eventId, sponsorId) =>
    api.post(`/api/events/${eventId}/sponsors/${sponsorId}/refresh`),
  remove: (eventId, sponsorId) =>
    api.del(`/api/events/${eventId}/sponsors/${sponsorId}`),
};

export const messagesApi = {
  send: (to_user_id, text) => api.post("/api/messages", { to_user_id, text }),
  threads: () => api.get("/api/messages/threads"),
  with: (userId) => api.get(`/api/messages/with/${userId}`),
  unreadCount: () => api.get("/api/messages/unread-count"),
};

export const adminApi = {
  stats: () => api.get("/api/admin/stats"),
  analytics: (days = 30) => api.get(`/api/admin/analytics?days=${days}`),
  suppressions: () => api.get("/api/admin/suppressions"),
  eventInsights: (eventId) => api.get(`/api/admin/events/${eventId}/insights`),
  listUsers: () => api.get("/api/admin/users"),
  deleteUser: (id) => api.del(`/api/admin/users/${id}`),
  bulkImport: (rows, event_id, default_password) =>
    api.post("/api/admin/users/bulk-import", {
      rows,
      event_id: event_id || null,
      default_password: default_password || null,
    }),
  checkEmails: (emails) =>
    api.post("/api/admin/users/check-emails", { emails }),
};

export const templatesApi = {
  list: () => api.get("/api/email-templates"),
  update: (id, data) => api.put(`/api/email-templates/${id}`, data),
  reset: (id) => api.post(`/api/email-templates/${id}/reset`),
  reseedAll: () => api.post("/api/admin/reseed-templates"),
};

export const outreachApi = {
  status: () => api.get("/api/admin/outreach/status"),
  list: () => api.get("/api/admin/outreach/leads"),
  add: (leads) => api.post("/api/admin/outreach/leads", { leads }),
  remove: (id) => api.del(`/api/admin/outreach/leads/${id}`),
  push: () => api.post("/api/admin/outreach/push"),
  exportCsv: () => api.get("/api/admin/outreach/leads.csv"),
};

export const blogApi = {
  flags: () => api.get("/api/admin/blog/flags"),
  setFlag: (name, value) => api.put("/api/admin/blog/flags", { name, value }),
  posts: () => api.get("/api/admin/blog/posts"),
  publish: (id) => api.post(`/api/admin/blog/posts/${id}/publish`),
  unpublish: (id) => api.post(`/api/admin/blog/posts/${id}/unpublish`),
  run: () => api.post("/api/admin/blog/run"),
};

export function newsPublicUrl(slug) {
  return `${BACKEND_URL}/news/${slug}`;
}

export const salesTemplatesApi = {
  list: () => api.get("/api/admin/sales-templates"),
  create: (t) => api.post("/api/admin/sales-templates", t),
  update: (id, t) => api.put(`/api/admin/sales-templates/${id}`, t),
  duplicate: (id) => api.post(`/api/admin/sales-templates/${id}/duplicate`),
  remove: (id) => api.del(`/api/admin/sales-templates/${id}`),
};

export const brandingApi = {
  get: () => api.get("/api/branding"),
  setAccent: (accent) => api.put("/api/branding", { accent }),
  reset: () => api.del("/api/branding"),
  // Multipart upload: bypasses the JSON request helper so the browser sets the
  // multipart boundary itself. Session still rides the httpOnly cookie.
  uploadLogo: async (file) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BACKEND_URL}/api/branding/logo`, {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) {
      let detail = "Upload failed";
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        detail = res.statusText;
      }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    return res.json();
  },
};

export const billingApi = {
  status: () => api.get("/api/billing/status"),
  // Starts Stripe Checkout for "starter" | "pro" and returns { url }.
  // Caller redirects: const { url } = await billingApi.checkout("pro"); location.href = url;
  checkout: (plan) => api.post("/api/billing/checkout", { plan }),
};

export const newsApi = {
  list: () => api.get("/api/admin/news"),
  create: (article) => api.post("/api/admin/news", article),
  update: (id, article) => api.put(`/api/admin/news/${id}`, article),
  remove: (id) => api.del(`/api/admin/news/${id}`),
  publish: (id) => api.post(`/api/admin/news/${id}/publish`),
  unpublish: (id) => api.post(`/api/admin/news/${id}/unpublish`),
};

export const agendaApi = {
  // Returns a .docx, so it bypasses the JSON request helper. Public: the
  // Agenda Builder works before the visitor has an account, and the endpoint
  // is stateless, so no session is required or sent.
  exportDocx: async (agenda) => {
    const res = await fetch(`${BACKEND_URL}/api/agenda/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(agenda),
    });
    if (!res.ok) {
      let detail = "We could not build that document.";
      try {
        const data = await res.json();
        // FastAPI validation errors arrive as a list of objects; flatten to
        // the first readable message rather than rendering "[object Object]".
        if (Array.isArray(data.detail)) {
          detail = data.detail[0]?.msg || detail;
        } else if (data.detail) {
          detail = data.detail;
        }
      } catch {
        detail = res.statusText || detail;
      }
      const err = new Error(detail);
      err.status = res.status;
      throw err;
    }
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    return { blob: await res.blob(), filename: match ? match[1] : "agenda.docx" };
  },

  // Saved agendas. Signed-in only: an anonymous draft never leaves the browser.
  create: (agenda) => api.post("/api/agenda", agenda),
  list: () => api.get("/api/agenda"),
  get: (id) => api.get(`/api/agenda/${id}`),
  update: (id, agenda) => api.put(`/api/agenda/${id}`, agenda),
  remove: (id) => api.del(`/api/agenda/${id}`),
  // Creates the event from a saved agenda and links the two. Server side in
  // one call so the plan limit and join-code generation stay in one place.
  convert: (id) => api.post(`/api/agenda/${id}/convert`),
  // The schedule as an attendee sees it. Gated on access to the EVENT, not
  // ownership of the agenda, and private notes are stripped server side.
  forEvent: (eventId) => api.get(`/api/events/${eventId}/agenda`),
};
