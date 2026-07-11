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
