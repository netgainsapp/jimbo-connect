const BACKEND_URL =
  (typeof process !== "undefined" && process.env && process.env.REACT_APP_BACKEND_URL) ||
  "http://localhost:8001";

async function request(path, options = {}) {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
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
};

export const profileApi = {
  get: () => api.get("/api/profile"),
  update: (data) => api.put("/api/profile", data),
  uploadPhoto: (photo_data) => api.post("/api/profile/photo", { photo_data }),
  getById: (id) => api.get(`/api/profile/${id}`),
};

export const eventsApi = {
  create: (data) => api.post("/api/events", data),
  list: () => api.get("/api/events"),
  get: (id) => api.get(`/api/events/${id}`),
  update: (id, data) => api.put(`/api/events/${id}`, data),
  remove: (id) => api.del(`/api/events/${id}`),
  join: (code) => api.post(`/api/events/join/${code}`),
  attendees: (id) => api.get(`/api/events/${id}/attendees`),
  myEvents: () => api.get("/api/my-events"),
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

export const adminApi = {
  stats: () => api.get("/api/admin/stats"),
};
