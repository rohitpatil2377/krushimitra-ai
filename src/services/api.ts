// Tiny fetch wrapper for talking to the FastAPI backend.
// Adds the base URL, a timeout (rural networks are slow/flaky), and clear errors.

import { apiUrl } from '@/config';

const DEFAULT_TIMEOUT_MS = 20000;

// Auth token for the signed-in farmer. Held in a module variable rather than imported from the
// store so that `api.ts` stays dependency-free and every request picks up a login or logout
// immediately, with no re-import and no prop drilling.
let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

function headers(extra: Record<string, string> = {}): Record<string, string> {
  return authToken ? { ...extra, Authorization: `Bearer ${authToken}` } : extra;
}

/** Thrown when the backend rejects the token, so callers can send the farmer back to login. */
export class UnauthorizedError extends Error {}

function raise(path: string, status: number, text: string): never {
  if (status === 401 || status === 403) {
    throw new UnauthorizedError(`${path} unauthorized (${status})`);
  }
  throw new Error(`${path} failed (${status}): ${text}`);
}

async function withTimeout(input: string, init: RequestInit, ms: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

/** POST multipart/form-data (used for image uploads + form fields). */
export async function postForm<T>(path: string, form: FormData, timeout = DEFAULT_TIMEOUT_MS): Promise<T> {
  const res = await withTimeout(`${apiUrl}${path}`, { method: 'POST', body: form, headers: headers() }, timeout);
  if (!res.ok) raise(path, res.status, await res.text());
  return (await res.json()) as T;
}

/** GET JSON, with optional query params (undefined/null params are dropped). */
export async function getJson<T>(
  path: string,
  params: Record<string, string | number | null | undefined> = {},
  timeout = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  const query = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  const url = `${apiUrl}${path}${query ? `?${query}` : ''}`;
  const res = await withTimeout(url, { method: 'GET', headers: headers() }, timeout);
  if (!res.ok) raise(path, res.status, await res.text());
  return (await res.json()) as T;
}

/** POST application/json. */
export async function postJson<T>(path: string, body: unknown, timeout = DEFAULT_TIMEOUT_MS): Promise<T> {
  const res = await withTimeout(
    `${apiUrl}${path}`,
    { method: 'POST', headers: headers({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) },
    timeout,
  );
  if (!res.ok) raise(path, res.status, await res.text());
  return (await res.json()) as T;
}

/** PATCH application/json. */
export async function patchJson<T>(path: string, body: unknown, timeout = DEFAULT_TIMEOUT_MS): Promise<T> {
  const res = await withTimeout(
    `${apiUrl}${path}`,
    { method: 'PATCH', headers: headers({ 'Content-Type': 'application/json' }), body: JSON.stringify(body) },
    timeout,
  );
  if (!res.ok) raise(path, res.status, await res.text());
  return (await res.json()) as T;
}

/** DELETE; returns nothing. */
export async function del(path: string, timeout = DEFAULT_TIMEOUT_MS): Promise<void> {
  const res = await withTimeout(`${apiUrl}${path}`, { method: 'DELETE', headers: headers() }, timeout);
  if (!res.ok && res.status !== 204) raise(path, res.status, await res.text());
}
