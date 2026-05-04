const BACKEND_URL =
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_BACKEND_URL) ||
  "http://localhost:8001";

const TOKEN_KEY = "jimbo_token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(t) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignore
  }
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BACKEND_URL}${path}`, {
    credentials: "include",
    ...options,
    headers,
  });
  if (!res.ok) {
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
