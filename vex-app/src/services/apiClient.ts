export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const API_BASE_URL = normalizeBaseUrl(configuredApiBaseUrl || DEFAULT_API_BASE_URL);

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | readonly QueryValue[]>;
export type ApiResponseType = "json" | "text" | "blob";
export type ApiMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiRequestOptions extends Omit<RequestInit, "body" | "method" | "signal"> {
  method?: ApiMethod;
  query?: QueryParams;
  body?: unknown;
  responseType?: ApiResponseType;
  signal?: AbortSignal;
  timeoutMs?: number;
  baseUrl?: string;
}

interface ApiErrorOptions {
  status: number | null;
  statusText: string;
  body: unknown;
  url: string;
  cause?: unknown;
}

export class ApiError extends Error {
  readonly status: number | null;
  readonly statusText: string;
  readonly body: unknown;
  readonly url: string;
  readonly cause?: unknown;

  constructor(message: string, options: ApiErrorOptions) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.statusText = options.statusText;
    this.body = options.body;
    this.url = options.url;
    this.cause = options.cause;
  }
}

export function buildApiUrl(
  path: string,
  query?: QueryParams,
  baseUrl: string = API_BASE_URL
): string {
  const normalizedPath = path.replace(/^\/+/, "");
  const url = isAbsoluteUrl(path)
    ? new URL(path)
    : new URL(`${normalizeBaseUrl(baseUrl)}/${normalizedPath}`);

  if (query) {
    for (const [key, rawValue] of Object.entries(query)) {
      const values = Array.isArray(rawValue) ? rawValue : [rawValue];
      for (const value of values) {
        if (value !== null && value !== undefined) {
          url.searchParams.append(key, String(value));
        }
      }
    }
  }

  return url.toString();
}

export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const {
    method = "GET",
    query,
    body,
    responseType = "json",
    signal,
    timeoutMs,
    baseUrl = API_BASE_URL,
    headers,
    ...requestInit
  } = options;
  const url = buildApiUrl(path, query, baseUrl);
  const requestHeaders = new Headers(headers);
  const requestBody = serializeBody(body, requestHeaders);
  const timeout = createRequestSignal(signal, timeoutMs);
  let response: Response;

  try {
    response = await fetch(url, {
      ...requestInit,
      method,
      headers: requestHeaders,
      body: requestBody,
      signal: timeout.signal,
    });
  } catch (error: unknown) {
    const message = timeout.didTimeout()
      ? `Request timed out after ${timeoutMs}ms`
      : error instanceof Error
        ? `Network request failed: ${error.message}`
        : "Network request failed";
    throw new ApiError(message, {
      status: null,
      statusText: "",
      body: null,
      url,
      cause: error,
    });
  } finally {
    timeout.cleanup();
  }

  if (!response.ok) {
    const errorBody = await parseErrorBody(response);
    throw new ApiError(errorMessage(response, errorBody), {
      status: response.status,
      statusText: response.statusText,
      body: errorBody,
      url: response.url || url,
    });
  }

  return (await parseSuccessBody(response, responseType)) as T;
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/+$/, "");
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function serializeBody(body: unknown, headers: Headers): BodyInit | undefined {
  if (body === undefined) {
    return undefined;
  }

  if (typeof FormData !== "undefined" && body instanceof FormData) {
    return body;
  }

  if (typeof Blob !== "undefined" && body instanceof Blob) {
    return body;
  }

  if (body instanceof URLSearchParams || typeof body === "string") {
    return body;
  }

  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return JSON.stringify(body);
}

async function parseSuccessBody(response: Response, responseType: ApiResponseType): Promise<unknown> {
  if (response.status === 204 || response.status === 205) {
    return undefined;
  }

  if (responseType === "blob") {
    return response.blob();
  }

  const text = await response.text();
  if (responseType === "text") {
    return text;
  }
  return text ? JSON.parse(text) : undefined;
}

async function parseErrorBody(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => "");
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function errorMessage(response: Response, body: unknown): string {
  if (isRecord(body)) {
    if (typeof body.detail === "string" && body.detail) {
      return body.detail;
    }
    if (typeof body.message === "string" && body.message) {
      return body.message;
    }
  }
  if (typeof body === "string" && body) {
    return body;
  }
  return `HTTP ${response.status}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function createRequestSignal(signal: AbortSignal | undefined, timeoutMs: number | undefined) {
  if (timeoutMs === undefined) {
    return {
      signal,
      didTimeout: () => false,
      cleanup: () => undefined,
    };
  }

  const controller = new AbortController();
  let timedOut = false;
  const forwardAbort = () => controller.abort(signal?.reason);
  if (signal?.aborted) {
    forwardAbort();
  } else {
    signal?.addEventListener("abort", forwardAbort, { once: true });
  }

  const timeoutId = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, Math.max(0, timeoutMs));

  return {
    signal: controller.signal,
    didTimeout: () => timedOut,
    cleanup: () => {
      window.clearTimeout(timeoutId);
      signal?.removeEventListener("abort", forwardAbort);
    },
  };
}
