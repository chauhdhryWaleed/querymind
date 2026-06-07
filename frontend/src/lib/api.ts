/** Fetch client for the backend: sends the session cookie, echoes the CSRF token
 * on mutations, and surfaces backend `detail` messages as `ApiError`. */

export const API_BASE =
  typeof window !== "undefined"
    ? "/api"
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001");

const CSRF_HEADER = "X-CSRF-Token";

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
  if (typeof window !== "undefined") {
    if (token) window.localStorage.setItem("csrf", token);
    else window.localStorage.removeItem("csrf");
  }
}

export function loadCsrfToken(): string | null {
  if (csrfToken) return csrfToken;
  if (typeof window !== "undefined") {
    csrfToken = window.localStorage.getItem("csrf");
  }
  return csrfToken;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Method = "GET" | "POST" | "PATCH" | "DELETE";

interface RequestOptions {
  method?: Method;
  body?: unknown;
  /** Skip attaching the CSRF header (e.g. login/register before a token exists). */
  noCsrf?: boolean;
}

export async function api<T = unknown>(
  path: string,
  { method = "GET", body, noCsrf = false }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const mutating = method !== "GET";
  if (mutating && !noCsrf) {
    const token = loadCsrfToken();
    if (token) headers[CSRF_HEADER] = token;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    // Never serve auth/session data from the HTTP cache: a stale /me could show outdated profile fields.
    cache: "no-store",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    const detail =
      (data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : null) ?? `Request failed (${res.status})`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
