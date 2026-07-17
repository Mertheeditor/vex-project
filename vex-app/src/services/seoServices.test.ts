import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SeoDomainService } from "./seoDomainService";
import { SeoProjectService } from "./seoProjectService";
import { startSeoAudit } from "./seo";

describe("migrated SEO service contracts", () => {
  let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

  beforeEach(() => {
    fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("SeoProjectService calls the existing project endpoint", async () => {
    fetchMock.mockResolvedValue(new Response("[]"));

    await SeoProjectService.listProjects();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/seo/projects",
      expect.objectContaining({ method: "GET" })
    );
  });

  it("SeoDomainService preserves filter and pagination query names", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ items: [] })));

    await SeoDomainService.getOrganicKeywords("project-1", {
      page: 3,
      page_size: 25,
      search: "typed client",
      position_from: 4,
      volume_to: 1000,
      sort_by: "position",
      sort_order: "asc",
      use_cache: false,
    });

    const url = new URL(String(fetchMock.mock.calls[0]?.[0]));
    expect(url.pathname).toBe("/seo/projects/project-1/organic-keywords");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      country: "US",
      language: "en",
      page: "3",
      page_size: "25",
      search: "typed client",
      position_from: "4",
      volume_to: "1000",
      sort_by: "position",
      sort_order: "asc",
      use_cache: "false",
    });
  });

  it("sends the Site Audit start payload to the existing endpoint", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ audit: { id: "audit-42" } })));

    await expect(startSeoAudit({
      url: "https://vex.test",
      country: "TR",
      language: "tr",
      business_description: "Typed client",
      max_pages: 100,
      project_id: "project-1",
    })).resolves.toEqual({
      auditId: "audit-42",
      resultUrl: "http://127.0.0.1:8000/seo/audits",
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("http://127.0.0.1:8000/seo/audits");
    expect(init?.method).toBe("POST");
    expect(init?.body).toBe(JSON.stringify({
      url: "https://vex.test",
      country: "TR",
      language: "tr",
      business_description: "Typed client",
      max_pages: 100,
      project_id: "project-1",
    }));
  });
});
