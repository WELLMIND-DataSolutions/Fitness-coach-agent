// All backend calls go through here. The API base URL is set at build time with VITE_API_URL.
const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "fitcoach_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, auth = true, timeoutMs = 60000 } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${getToken()}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    throw new ApiError(
      err.name === "AbortError"
        ? "The server took too long to answer. Try again."
        : "Can't reach the server. Check your connection and try again.",
      0
    );
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let message = data.detail;
    if (Array.isArray(message)) message = friendlyValidation(message);
    throw new ApiError(message || `Request failed (${res.status}).`, res.status);
  }
  return data;
}

function friendlyValidation(errors) {
  const field = errors[0]?.loc?.at(-1);
  if (field === "username") return "Username must be 3-32 letters, numbers, dots, dashes or underscores (no spaces).";
  if (field === "password") return "Password must be at least 8 characters.";
  if (field === "message") return "That message is too long. Keep it under 2000 characters.";
  return "Some of the details are not valid.";
}

export const api = {
  register: (username, password) =>
    request("/auth/register", {
      method: "POST",
      auth: false,
      body: { username, password, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
    }),
  login: (username, password) => request("/auth/login", { method: "POST", auth: false, body: { username, password } }),
  chat: (message) => request("/chat", { method: "POST", body: { message } }),
  history: () => request("/chat/history"),
  clearHistory: () => request("/chat/history", { method: "DELETE" }),
  notifications: () => request("/notifications", { timeoutMs: 15000 }),
  markRead: (id) => request(`/notifications/${id}/read`, { method: "POST" }),
};