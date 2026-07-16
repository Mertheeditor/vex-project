// Frontend service for SEO project management
// Matches backend SeoProjectService API

import type {
  SeoProject,
  SeoCapabilities,
  ProviderStatus,
  ProviderInfo,
  CrawlConfig,
  SeoAuditRequest,
  AuditListParams,
  AuditListResponse,
  SeoAudit,
} from "../types/seo";

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

export const SeoProjectService = {
  // Project CRUD
  async createProject(data: {
    name: string;
    domain: string;
    description?: string;
    max_pages?: number;
    max_depth?: number;
    crawl_config?: Partial<CrawlConfig>;
    country?: string;
    language?: string;
  }): Promise<SeoProject> {
    return fetchJson<SeoProject>(API_BASE, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async listProjects(): Promise<SeoProject[]> {
    return fetchJson<SeoProject[]>(API_BASE);
  },

  async getProject(projectId: string): Promise<SeoProject | null> {
    try {
      return await fetchJson<SeoProject>(`${API_BASE}/${encodeURIComponent(projectId)}`);
    } catch (e) {
      return null;
    }
  },

  async updateProject(
    projectId: string,
    updates: Partial<SeoProject>
  ): Promise<SeoProject | null> {
    try {
      return await fetchJson<SeoProject>(`${API_BASE}/${encodeURIComponent(projectId)}`, {
        method: "PATCH",
        body: JSON.stringify(updates),
      });
    } catch (e) {
      return null;
    }
  },

  async deleteProject(projectId: string): Promise<boolean> {
    try {
      await fetch(`${API_BASE}/${encodeURIComponent(projectId)}`, {
        method: "DELETE",
      });
      return true;
    } catch (e) {
      return false;
    }
  },

  // Project crawl config
  async getProjectCrawlConfig(projectId: string): Promise<CrawlConfig> {
    return fetchJson<CrawlConfig>(`${API_BASE}/${encodeURIComponent(projectId)}/config`);
  },

  // Project audits with pagination and filtering
  async createProjectAudit(projectId: string, request: SeoAuditRequest): Promise<SeoAudit> {
    return fetchJson<SeoAudit>(`${API_BASE}/${encodeURIComponent(projectId)}/audits`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  async listProjectAudits(
    projectId: string,
    params: AuditListParams = {}
  ): Promise<AuditListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set("page", String(params.page));
    if (params.page_size) searchParams.set("page_size", String(params.page_size));
    if (params.status) searchParams.set("status", params.status.join(","));
    if (params.date_from) searchParams.set("date_from", params.date_from);
    if (params.date_to) searchParams.set("date_to", params.date_to);
    if (params.min_score !== undefined) searchParams.set("min_score", String(params.min_score));
    if (params.max_score !== undefined) searchParams.set("max_score", String(params.max_score));
    if (params.search) searchParams.set("search", params.search);
    if (params.sort_by) searchParams.set("sort_by", params.sort_by);
    if (params.sort_order) searchParams.set("sort_order", params.sort_order);

    const url = `${API_BASE}/${encodeURIComponent(projectId)}/audits?${searchParams.toString()}`;
    return fetchJson<AuditListResponse>(url);
  },

  // Capabilities & Provider Status
  async getCapabilities(): Promise<SeoCapabilities> {
    return fetchJson<SeoCapabilities>(`${API_BASE}/capabilities`);
  },

  async getProviderStatus(): Promise<ProviderStatus> {
    return fetchJson<ProviderStatus>(`${API_BASE}/providers/status`);
  },
};

// Type for create project request
export interface CreateProjectRequest {
  name: string;
  domain: string;
  description?: string;
  max_pages?: number;
  max_depth?: number;
  crawl_config?: Partial<CrawlConfig>;
  country?: string;
  language?: string;
}

// Re-export types for components
export type { SeoProject, SeoCapabilities, ProviderStatus, ProviderInfo, CrawlConfig };