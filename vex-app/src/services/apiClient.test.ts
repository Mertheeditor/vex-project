import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiRequest, buildApiUrl, DEFAULT_API_BASE_URL } from "./apiClient";

describe("apiClient", () => {
  let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

  beforeEach(() => {
    fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses a GET JSON response", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ok: true })));

    await expect(apiRequest<{ ok: boolean }>("/health")).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      `${DEFAULT_API_BASE_URL}/health`,
      expect.objectContaining({ method: "GET" })
    );
  });

  it("serializes a POST JSON body and adds its content type", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: "one" })));

    await apiRequest<{ id: string }>("/items", {
      method: "POST",
      body: { name: "Vex" },
    });

    const init = requestInit();
    expect(init.body).toBe(JSON.stringify({ name: "Vex" }));
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("serializes query parameter values safely", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));

    await apiRequest<unknown>("/search", {
      query: { q: "site audit & SEO", page: 2, cached: false },
    });

    const url = new URL(requestUrl());
    expect(url.searchParams.get("q")).toBe("site audit & SEO");
    expect(url.searchParams.get("page")).toBe("2");
    expect(url.searchParams.get("cached")).toBe("false");
  });

  it("omits null and undefined query values", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));

    await apiRequest<unknown>("/search", {
      query: { country: null, language: undefined, page: 1 },
    });

    const url = new URL(requestUrl());
    expect(url.searchParams.has("country")).toBe(false);
    expect(url.searchParams.has("language")).toBe(false);
    expect(url.searchParams.get("page")).toBe("1");
  });

  it("repeats array query values and omits empty entries", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));

    await apiRequest<unknown>("/audits", {
      query: { status: ["running", null, "failed", undefined] },
    });

    expect(new URL(requestUrl()).searchParams.getAll("status")).toEqual(["running", "failed"]);
  });

  it("supports a 204 No Content response", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(apiRequest<void>("/items/one", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("preserves JSON HTTP error details", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: "Invalid project" }), {
      status: 422,
      statusText: "Unprocessable Content",
    }));

    const error = await apiRequest<unknown>("/projects").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      message: "Invalid project",
      status: 422,
      statusText: "Unprocessable Content",
      body: { detail: "Invalid project" },
      url: `${DEFAULT_API_BASE_URL}/projects`,
    });
  });

  it("preserves a text HTTP error body", async () => {
    fetchMock.mockResolvedValue(new Response("Service unavailable", { status: 503 }));

    await expect(apiRequest<unknown>("/health")).rejects.toMatchObject({
      message: "Service unavailable",
      status: 503,
      body: "Service unavailable",
    });
  });

  it("normalizes network failures", async () => {
    const cause = new TypeError("Failed to fetch");
    fetchMock.mockRejectedValue(cause);

    await expect(apiRequest<unknown>("/health")).rejects.toMatchObject({
      name: "ApiError",
      message: "Network request failed: Failed to fetch",
      status: null,
      body: null,
      cause,
    });
  });

  it("forwards an AbortSignal unchanged when no timeout is set", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));
    const controller = new AbortController();

    await apiRequest<unknown>("/slow", { signal: controller.signal });

    expect(requestInit().signal).toBe(controller.signal);
  });

  it("does not set Content-Type for FormData", async () => {
    fetchMock.mockResolvedValue(new Response("{}"));
    const formData = new FormData();
    formData.set("file", new Blob(["data"]), "audit.csv");

    await apiRequest<unknown>("/upload", { method: "POST", body: formData });

    const init = requestInit();
    expect(init.body).toBe(formData);
    expect(new Headers(init.headers).has("Content-Type")).toBe(false);
  });

  it("joins base URLs and paths without duplicate slashes", () => {
    expect(buildApiUrl("/seo/audits", undefined, "https://api.vex.test/")).toBe(
      "https://api.vex.test/seo/audits"
    );
  });

  it.each(["PUT", "PATCH", "DELETE"] as const)(
    "forwards the %s method and custom headers",
    async (method) => {
      fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

      await apiRequest<void>("/items/one", {
        method,
        headers: { "X-Request-ID": "request-one" },
      });

      const init = requestInit();
      expect(init.method).toBe(method);
      expect(new Headers(init.headers).get("X-Request-ID")).toBe("request-one");
      expect(new Headers(init.headers).has("Content-Type")).toBe(false);
    }
  );

  function requestUrl(): string {
    const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(call).toBeDefined();
    return String(call?.[0]);
  }

  function requestInit(): RequestInit {
    const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    expect(call).toBeDefined();
    return call?.[1] ?? {};
  }
});
