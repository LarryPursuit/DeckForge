const BASE = import.meta.env.VITE_API_URL || "";
const TOKEN_KEY = "deckforge_token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.error || `Request failed (${status})`);
    this.status = status;
    this.fields = body?.fields || {};
  }
}

/**
 * One place for every request: attaches the token, parses JSON,
 * and signs the user out when the API answers 401.
 */
export async function apiFetch(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(0, { error: "Can't reach the Deckforge server. Check that it's running." });
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (res.status === 401 && token) {
    window.dispatchEvent(new CustomEvent("deckforge:logout", { detail: data?.error }));
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data;
}
