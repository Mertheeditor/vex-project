import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SeoDomainService } from "../../services/seoDomainService";
import type {
  DataSourcesResponse,
  DomainOverviewResponse,
  OrganicKeyword,
  OrganicPage,
} from "../../types/seoDomain";
import { DomainOverviewPage } from "./DomainOverviewPage";

vi.mock("../../services/seoDomainService", () => ({
  SeoDomainService: {
    getDomainOverview: vi.fn(),
    getOrganicKeywords: vi.fn(),
    getOrganicPages: vi.fn(),
    getCompetitors: vi.fn(),
    getPositionChanges: vi.fn(),
    getDataSources: vi.fn(),
  },
}));

vi.mock("./SeoProjectSelector", () => ({
  SeoProjectSelector: ({
    value,
    onChange,
  }: {
    value?: string;
    onChange?: (projectId: string) => void;
  }) => (
    <select
      aria-label="SEO projesi"
      value={value ?? ""}
      onChange={(event) => onChange?.(event.target.value)}
    >
      <option value="">SEO projesi seç</option>
      <option value="project-1">Vex</option>
    </select>
  ),
}));

const disconnectedSources: DataSourcesResponse = {
  sources: [
    {
      source: "semrush",
      configured: false,
      status: "not_configured",
      last_sync: null,
      quota_remaining: null,
      quota_total: null,
      error_message: null,
      supported_features: ["organic_keywords"],
    },
  ],
  primary_source: null,
};

const overview: DomainOverviewResponse = {
  metrics: {
    domain: "vex.test",
    organic_keywords: 0,
    organic_traffic: 0,
    organic_traffic_cost: 0,
    paid_keywords: 0,
    paid_traffic: 0,
    paid_traffic_cost: 0,
    authority_score: 0,
    backlinks: 0,
    referring_domains: 0,
    traffic_trend: "stable",
    trend_percentage: 0,
    last_updated: "2026-07-17T10:00:00Z",
    data_source: "estimated",
    country: "US",
    language: "en",
  },
  history: [],
  data_sources: disconnectedSources,
  last_refresh: "2026-07-17T10:00:00Z",
};

describe("DomainOverviewPage", () => {
  beforeEach(() => {
    vi.mocked(SeoDomainService.getDomainOverview).mockResolvedValue(overview);
    vi.mocked(SeoDomainService.getOrganicKeywords).mockResolvedValue(emptyPage());
    vi.mocked(SeoDomainService.getOrganicPages).mockResolvedValue(emptyPage());
    vi.mocked(SeoDomainService.getCompetitors).mockResolvedValue(emptyPage());
    vi.mocked(SeoDomainService.getPositionChanges).mockResolvedValue(emptyPage());
    vi.mocked(SeoDomainService.getDataSources).mockResolvedValue(disconnectedSources);
  });

  it("renders all six main tabs for a selected project", async () => {
    render(<DomainOverviewPage projectId="project-1" />);

    expect(await screen.findByRole("button", { name: /Genel Bakış/ })).toBeVisible();
    for (const label of [
      "Organik Anahtar Kelimeler",
      "En İyi Sayfalar",
      "Rakipler",
      "Pozisyon Değişimleri",
      "Veri Kaynakları",
    ]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeVisible();
    }
  });

  it("explains that the data source is not connected", async () => {
    render(<DomainOverviewPage projectId="project-1" />);

    expect((await screen.findAllByText("Veri kaynağı bağlı değil")).length).toBeGreaterThan(0);
    expect(screen.queryByText("0", { selector: ".summary-value" })).not.toBeInTheDocument();
  });

  it("does not invent keyword rows for an empty backend response", async () => {
    const user = userEvent.setup();
    render(<DomainOverviewPage projectId="project-1" />);

    await user.click(await screen.findByRole("button", { name: /Organik Anahtar Kelimeler/ }));

    expect((await screen.findAllByText("Anahtar kelime veri sağlayıcısı bağlı değil.")).length).toBeGreaterThan(0);
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
  });

  it("shows the competitor empty state", async () => {
    const user = userEvent.setup();
    render(<DomainOverviewPage projectId="project-1" />);

    await user.click(await screen.findByRole("button", { name: /Rakipler/ }));

    expect((await screen.findAllByText("Organik rakip verisi için SERP veya domain araştırma sağlayıcısı bağlanmalıdır.")).length).toBeGreaterThan(0);
  });

  it("shows the position changes empty state", async () => {
    const user = userEvent.setup();
    render(<DomainOverviewPage projectId="project-1" />);

    await user.click(await screen.findByRole("button", { name: /Pozisyon Değişimleri/ }));

    expect((await screen.findAllByText("Karşılaştırma için en az iki veri noktası gerekir.")).length).toBeGreaterThan(0);
  });

  it("renders real technical page rows supplied by Site Audit", async () => {
    const user = userEvent.setup();
    const auditPage: OrganicPage = {
      url: "https://vex.test/technical-page",
      organic_keywords: 0,
      organic_traffic: 0,
      organic_traffic_cost: 0,
      traffic_percentage: 0,
      top_keyword: "",
      top_keyword_position: 0,
      top_keyword_volume: 0,
      backlinks: 0,
      referring_domains: 0,
      page_type: "content_page",
      word_count: 420,
      last_updated: "2026-07-17T10:00:00Z",
      data_source: "custom",
    };
    vi.mocked(SeoDomainService.getOrganicPages).mockResolvedValue(pageWithItems([auditPage]));
    render(<DomainOverviewPage projectId="project-1" />);

    await user.click(await screen.findByRole("button", { name: /En İyi Sayfalar/ }));

    expect(await screen.findByRole("link", { name: auditPage.url })).toHaveAttribute("href", auditPage.url);
    expect(screen.getByText("custom")).toBeVisible();
  });

  it("keeps pagination and resets it when a filter changes", async () => {
    const user = userEvent.setup();
    const keyword = makeKeyword();
    vi.mocked(SeoDomainService.getOrganicKeywords).mockImplementation(async (
      _projectId: string,
      options: NonNullable<Parameters<typeof SeoDomainService.getOrganicKeywords>[1]> = {},
    ) => ({
      ...pageWithItems([keyword]),
      page: options.page ?? 1,
      total: 60,
      total_pages: 2,
      has_next: (options.page ?? 1) === 1,
      has_prev: (options.page ?? 1) === 2,
    }));
    render(<DomainOverviewPage projectId="project-1" />);

    await user.click(await screen.findByRole("button", { name: /Organik Anahtar Kelimeler/ }));
    await user.click(await screen.findByRole("button", { name: "Sonraki sayfa" }));

    await waitFor(() => {
      expect(SeoDomainService.getOrganicKeywords).toHaveBeenLastCalledWith(
        "project-1",
        expect.objectContaining({ page: 2 }),
      );
    });

    await user.type(screen.getByPlaceholderText("Anahtar kelime ara"), "seo");

    await waitFor(() => {
      expect(SeoDomainService.getOrganicKeywords).toHaveBeenLastCalledWith(
        "project-1",
        expect.objectContaining({ page: 1, search: "seo" }),
      );
    });
  });

  it("shows a deterministic loading state", () => {
    vi.mocked(SeoDomainService.getDomainOverview).mockReturnValue(new Promise(() => undefined));
    render(<DomainOverviewPage projectId="project-1" />);

    expect(screen.getByText("Genel bakış yükleniyor...")).toBeVisible();
    expect(screen.getByRole("button", { name: "Yükleniyor..." })).toBeDisabled();
  });

  it("shows the service error state", async () => {
    vi.mocked(SeoDomainService.getDomainOverview).mockRejectedValue(new Error("SEO servisi kullanılamıyor"));
    render(<DomainOverviewPage projectId="project-1" />);

    expect(await screen.findByText("SEO servisi kullanılamıyor")).toBeVisible();
  });
});

function emptyPage<T = never>() {
  return pageWithItems<T>([]);
}

function pageWithItems<T>(items: T[]) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 50,
    total_pages: items.length ? 1 : 0,
    has_next: false,
    has_prev: false,
  };
}

function makeKeyword(): OrganicKeyword {
  return {
    keyword: "seo güvenlik ağı",
    position: 4,
    previous_position: 7,
    position_change: 3,
    url: "https://vex.test/seo",
    search_volume: 100,
    keyword_difficulty: 20,
    cpc: 1.2,
    traffic: 30,
    traffic_percentage: 10,
    traffic_cost: 36,
    intent: "informational",
    serps_features: [],
    results_count: 1000,
    last_updated: "2026-07-17T10:00:00Z",
    data_source: "semrush",
    country: "US",
    language: "en",
  };
}
