/**
 * Thin typed fetch wrapper around the backend API.
 *
 * All requests are credentialed (httpOnly cookie carries the access token).
 * Responses are parsed with the matching zod schema at the call site.
 */
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    credentials: "include",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...opts.headers,
    },
    body: opts.body == null ? undefined : JSON.stringify(opts.body),
    signal: opts.signal,
  });
  const text = await res.text();
  const json: unknown = text.length > 0 ? JSON.parse(text) : null;
  if (!res.ok) {
    const env = json as { error?: { code?: string; message?: string; details?: unknown } } | null;
    throw new ApiError(
      res.status,
      env?.error?.code ?? "unknown",
      env?.error?.message ?? res.statusText,
      env?.error?.details,
    );
  }
  return json as T;
}
