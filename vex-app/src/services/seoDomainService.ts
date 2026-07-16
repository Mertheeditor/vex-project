// Frontend service for Domain Overview & Organic Research Workspace
// Matches backend app/routes/seo_domain.py (project-scoped endpoints)

import type {
  DomainOverviewResponse,
  OrganicKeywordsResponse,
  OrganicPagesResponse,
  CompetitorsResponse,
  PositionChangesResponse,
  DataSourcesResponse,
  BulkDomainOverviewRequest,
  BulkDomainOverviewResponse,
  ExportDomainOverviewRequest,
  ExportDomainOverviewResponse,
  OrganicKeywordFilters,
  OrganicPageFilters,
  CompetitorFilters,
  PositionChangesFilters,
} from "../types/seoDomain";

const API_BASE = "http://127.0.0.1:8000/seo/projects";

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export const SeoDomainService = {
  // Domain Overview - project-scoped
  async getDomainOverview(
    projectId: string,
    options: {
      country?: string;
      language?: string;
      include_history?: boolean;
      history_days?: number;
      use_cache?: boolean;
    } = {}
  ): Promise<DomainOverviewResponse> {
    const params = new URLSearchParams({
      country: options.country ?? "US",
      language: options.language ?? "en",
      include_history: String(options.include_history ?? true),
      history_days: String(options.history_days ?? 30),
      use_cache: String(options.use_cache ?? true),
    });
    return fetchJson<DomainOverviewResponse>(`${API_BASE}/${projectId}/domain-overview?${params}`);
  },

  // Organic Keywords - project-scoped
  async getOrganicKeywords(
    projectId: string,
    options: {
      country?: string;
      language?: string;
      page?: number;
      page_size?: number;
      search?: string;
      position_from?: number;
      position_to?: number;
      volume_from?: number;
      volume_to?: number;
      difficulty_from?: number;
      difficulty_to?: number;
      intent?: string;
      sort_by?: string;
      sort_order?: "asc" | "desc";
      use_cache?: boolean;
    } = {}
  ): Promise<OrganicKeywordsResponse> {
    const params = new URLSearchParams();
    params.set("country", options.country ?? "US");
    params.set("language", options.language ?? "en");
    params.set("page", String(options.page ?? 1));
    params.set("page_size", String(options.page_size ?? 50));
    if (options.search) params.set("search", options.search);
    if (options.position_from !== undefined) params.set("position_from", String(options.position_from));
    if (options.position_to !== undefined) params.set("position_to", String(options.position_to));
    if (options.volume_from !== undefined) params.set("volume_from", String(options.volume_from));
    if (options.volume_to !== undefined) params.set("volume_to", String(options.volume_to));
    if (options.difficulty_from !== undefined) params.set("difficulty_from", String(options.difficulty_from));
    if (options.difficulty_to !== undefined) params.set("difficulty_to", String(options.difficulty_to));
    if (options.intent) params.set("intent", options.intent);
    params.set("sort_by", options.sort_by ?? "traffic");
    params.set("sort_order", options.sort_order ?? "desc");
    params.set("use_cache", String(options.use_cache ?? true));

    return fetchJson<OrganicKeywordsResponse>(`${API_BASE}/${projectId}/organic-keywords?${params}`);
  },

  // Organic Pages - project-scoped
  async getOrganicPages(
    projectId: string,
    options: {
      country?: string;
      language?: string;
      page?: number;
      page_size?: number;
      search?: string;
      keywords_from?: number;
      keywords_to?: number;
      traffic_from?: number;
      traffic_to?: number;
      page_type?: string;
      sort_by?: string;
      sort_order?: "asc" | "desc";
      use_cache?: boolean;
    } = {}
  ): Promise<OrganicPagesResponse> {
    const params = new URLSearchParams();
    params.set("country", options.country ?? "US");
    params.set("language", options.language ?? "en");
    params.set("page", String(options.page ?? 1));
    params.set("page_size", String(options.page_size ?? 50));
    if (options.search) params.set("search", options.search);
    if (options.keywords_from !== undefined) params.set("keywords_from", String(options.keywords_from));
    if (options.keywords_to !== undefined) params.set("keywords_to", String(options.keywords_to));
    if (options.traffic_from !== undefined) params.set("traffic_from", String(options.traffic_from));
    if (options.traffic_to !== undefined) params.set("traffic_to", String(options.traffic_to));
    if (options.page_type) params.set("page_type", options.page_type);
    params.set("sort_by", options.sort_by ?? "traffic");
    params.set("sort_order", options.sort_order ?? "desc");
    params.set("use_cache", String(options.use_cache ?? true));

    return fetchJson<OrganicPagesResponse>(`${API_BASE}/${projectId}/organic-pages?${params}`);
  },

  // Competitors - project-scoped
  async getCompetitors(
    projectId: string,
    options: {
      country?: string;
      language?: string;
      page?: number;
      page_size?: number;
      search?: string;
      common_keywords_from?: number;
      traffic_from?: number;
      authority_from?: number;
      sort_by?: string;
      sort_order?: "asc" | "desc";
      use_cache?: boolean;
    } = {}
  ): Promise<CompetitorsResponse> {
    const params = new URLSearchParams();
    params.set("country", options.country ?? "US");
    params.set("language", options.language ?? "en");
    params.set("page", String(options.page ?? 1));
    params.set("page_size", String(options.page_size ?? 20));
    if (options.search) params.set("search", options.search);
    if (options.common_keywords_from !== undefined) params.set("common_keywords_from", String(options.common_keywords_from));
    if (options.traffic_from !== undefined) params.set("traffic_from", String(options.traffic_from));
    if (options.authority_from !== undefined) params.set("authority_from", String(options.authority_from));
    params.set("sort_by", options.sort_by ?? "competition_level");
    params.set("sort_order", options.sort_order ?? "desc");
    params.set("use_cache", String(options.use_cache ?? true));

    return fetchJson<CompetitorsResponse>(`${API_BASE}/${projectId}/organic-competitors?${params}`);
  },

  // Position Changes - project-scoped
  async getPositionChanges(
    projectId: string,
    options: {
      country?: string;
      language?: string;
      page?: number;
      page_size?: number;
      search?: string;
      direction?: string;
      change_from?: number;
      volume_from?: number;
      position_from?: number;
      position_to?: number;
      sort_by?: string;
      sort_order?: "asc" | "desc";
      use_cache?: boolean;
    } = {}
  ): Promise<PositionChangesResponse> {
    const params = new URLSearchParams();
    params.set("country", options.country ?? "US");
    params.set("language", options.language ?? "en");
    params.set("page", String(options.page ?? 1));
    params.set("page_size", String(options.page_size ?? 50));
    if (options.search) params.set("search", options.search);
    if (options.direction) params.set("direction", options.direction);
    if (options.change_from !== undefined) params.set("change_from", String(options.change_from));
    if (options.volume_from !== undefined) params.set("volume_from", String(options.volume_from));
    if (options.position_from !== undefined) params.set("position_from", String(options.position_from));
    if (options.position_to !== undefined) params.set("position_to", String(options.position_to));
    params.set("sort_by", options.sort_by ?? "date_detected");
    params.set("sort_order", options.sort_order ?? "desc");
    params.set("use_cache", String(options.use_cache ?? true));

    return fetchJson<PositionChangesResponse>(`${API_BASE}/${projectId}/position-changes?${params}`);
  },

  // Data Sources - project-scoped
  async getDataSources(projectId: string): Promise<DataSourcesResponse> {
    return fetchJson<DataSourcesResponse>(`${API_BASE}/${projectId}/data-sources`);
  },

  // Bulk Operations - not project-scoped
  async bulkDomainOverview(request: BulkDomainOverviewRequest): Promise<BulkDomainOverviewResponse> {
    return fetchJson<BulkDomainOverviewResponse>(`${API_BASE}/bulk-overview`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  // Export - project-scoped
  async exportDomainOverview(
    projectId: string,
    request: ExportDomainOverviewRequest
  ): Promise<ExportDomainOverviewResponse> {
    return fetchJson<ExportDomainOverviewResponse>(`${API_BASE}/${projectId}/export`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  // Capabilities
  async getCapabilities(): Promise<Record<string, any>> {
    return fetchJson<Record<string, any>>(`${API_BASE}/capabilities`);
  },
};

// Helper functions for building filter objects (matching backend filter names)
export function createKeywordFilters(overrides: Partial<OrganicKeywordFilters> = {}): OrganicKeywordFilters {
  return {
    position_min: undefined,
    position_max: undefined,
    volume_min: undefined,
    volume_max: undefined,
    difficulty_min: undefined,
    difficulty_max: undefined,
    intent: undefined,
    serps_feature: undefined,
    url_contains: undefined,
    position_change_min: undefined,
    position_change_max: undefined,
    traffic_min: undefined,
    date_from: undefined,
    date_to: undefined,
    ...overrides,
  };
}

export function createPageFilters(overrides: Partial<OrganicPageFilters> = {}): OrganicPageFilters {
  return {
    keywords_min: undefined,
    keywords_max: undefined,
    traffic_min: undefined,
    traffic_max: undefined,
    page_type: undefined,
    url_contains: undefined,
    date_from: undefined,
    date_to: undefined,
    has_backlinks: undefined,
    ...overrides,
  };
}

export function createCompetitorFilters(overrides: Partial<CompetitorFilters> = {}): CompetitorFilters {
  return {
    common_keywords_min: undefined,
    authority_min: undefined,
    traffic_min: undefined,
    ...overrides,
  };
}

export function createPositionChangeFilters(overrides: Partial<PositionChangesFilters> = {}): PositionChangesFilters {
  return {
    direction: undefined,
    change_min: undefined,
    change_max: undefined,
    volume_min: undefined,
    keyword_contains: undefined,
    date_from: undefined,
    date_to: undefined,
    ...overrides,
  };
}