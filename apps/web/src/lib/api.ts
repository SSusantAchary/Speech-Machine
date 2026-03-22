const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type JwtPayload = {
  exp?: number;
};

const decodeBase64Url = (value: string) => {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  if (typeof window === "undefined") return null;
  try {
    return window.atob(padded);
  } catch {
    return null;
  }
};

export const getTokenPayload = (token: string): JwtPayload | null => {
  const [, payload] = token.split(".");
  if (!payload) return null;
  const decoded = decodeBase64Url(payload);
  if (!decoded) return null;
  try {
    return JSON.parse(decoded) as JwtPayload;
  } catch {
    return null;
  }
};

export const getToken = () => {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("auth_token");
};

export const hasValidToken = () => {
  const token = getToken();
  if (!token) return false;
  const payload = getTokenPayload(token);
  if (!payload) return false;
  if (!payload.exp) return false;
  return payload.exp * 1000 > Date.now();
};

export const setToken = (token: string) => {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("auth_token", token);
};

export const clearToken = () => {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("auth_token");
};

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const message = await response.text();
    let detail = message;
    try {
      const parsed = JSON.parse(message) as { detail?: string };
      detail = parsed.detail || message;
    } catch {
      detail = message;
    }
    if (response.status === 401) {
      clearToken();
      throw new Error("Authentication expired. Sign in again.");
    }
    throw new Error(detail || "Request failed");
  }
  return response.json();
}

export const authApi = {
  signup: (email: string, password: string) =>
    apiFetch<{ access_token: string }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  login: (email: string, password: string) =>
    apiFetch<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => apiFetch("/auth/logout", { method: "POST" }),
};
