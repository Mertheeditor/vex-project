// Frontend service for SEO project management
// Matches backend SeoProjectService API

import type {
  SeoProject,
  SeoCapabilities,
  ProviderStatus,
  ProviderInfo,
  CrawlConfig,
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

  // Project audits
  async createProjectAudit(projectId: string, request: any): Promise<{ audit_id: string }> {
    return fetchJson<{ audit_id: string }>(`${API_BASE}/${encodeURIComponent(projectId)}/audits`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  },

  async listProjectAudits(projectId: string): Promise<any[]> {
    return fetchJson<any[]>(`${API_BASE}/${encodeURIComponent(projectId)}/audits`);
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
}

// Re-export types for components
export type { SeoProject, SeoCapabilities, ProviderStatus, ProviderInfo, CrawlConfig };