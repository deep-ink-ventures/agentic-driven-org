const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }
  }

  const doFetch = () =>
    fetch(url, { ...options, credentials: "include", headers });

  let res: Response;
  try {
    res = await doFetch();
  } catch {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (res.status === 503) {
    await new Promise((r) => setTimeout(r, 2000));
    res = await doFetch();
  }

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  getSession: () =>
    request<{ user: import("./types").User | null }>("/api/auth/session/"),

  login: (email: string, password: string) =>
    request<{ user: import("./types").User }>("/api/auth/login/", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  signup: (email: string, password: string, termsAccepted: boolean) =>
    request<{ user: import("./types").User }>("/api/auth/signup/", {
      method: "POST",
      body: JSON.stringify({ email, password, terms_accepted: termsAccepted }),
    }),

  logout: () =>
    request<void>("/api/auth/logout/", { method: "POST" }),
};
