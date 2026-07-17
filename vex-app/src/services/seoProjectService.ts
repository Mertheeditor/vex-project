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
import { ApiError, apiRequest, type ApiRequestOptions, type QueryParams } from "./apiClient";

const API_PATH = "/seo/projects";

async function requestJson<T>(path: string, options?: ApiRequestOptions): Promise<T> {
  try {
    return await apiRequest<T>(path, options);
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status !== null) {
      if (isRecord(error.body) && typeof error.body.detail === "string" && error.body.detail) {
        throw new Error(error.body.detail);
      }
      throw new Error(typeof error.body === "string" ? "Unknown error" : `HTTP ${error.status}`);
    }
    throw error;
  }
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
    return requestJson<SeoProject>(API_PATH, {
      method: "POST",
      body: data,
    });
  },

  async listProjects(): Promise<SeoProject[]> {
    return requestJson<SeoProject[]>(API_PATH);
  },

  async getProject(projectId: string): Promise<SeoProject | null> {
    try {
      return await requestJson<SeoProject>(`${API_PATH}/${encodeURIComponent(projectId)}`);
    } catch (e) {
      return null;
    }
  },

  async updateProject(
    projectId: string,
    updates: Partial<SeoProject>
  ): Promise<SeoProject | null> {
    try {
      return await requestJson<SeoProject>(`${API_PATH}/${encodeURIComponent(projectId)}`, {
        method: "PATCH",
        body: updates,
      });
    } catch (e) {
      return null;
    }
  },

  async deleteProject(projectId: string): Promise<boolean> {
    try {
      await apiRequest<void>(`${API_PATH}/${encodeURIComponent(projectId)}`, {
        method: "DELETE",
      });
      return true;
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status !== null) {
        return true;
      }
      return false;
    }
  },

  // Project crawl config
  async getProjectCrawlConfig(projectId: string): Promise<CrawlConfig> {
    return requestJson<CrawlConfig>(`${API_PATH}/${encodeURIComponent(projectId)}/config`);
  },

  // Project audits with pagination and filtering
  async createProjectAudit(projectId: string, request: SeoAuditRequest): Promise<SeoAudit> {
    return requestJson<SeoAudit>(`${API_PATH}/${encodeURIComponent(projectId)}/audits`, {
      method: "POST",
      body: request,
    });
  },

  async listProjectAudits(
    projectId: string,
    params: AuditListParams = {}
  ): Promise<AuditListResponse> {
    const query: QueryParams = {
      page: params.page || undefined,
      page_size: params.page_size || undefined,
      status: params.status?.join(","),
      date_from: params.date_from || undefined,
      date_to: params.date_to || undefined,
      min_score: params.min_score,
      max_score: params.max_score,
      search: params.search || undefined,
      sort_by: params.sort_by,
      sort_order: params.sort_order,
    };

    return requestJson<AuditListResponse>(`${API_PATH}/${encodeURIComponent(projectId)}/audits`, {
      query,
    });
  },

  // Capabilities & Provider Status
  async getCapabilities(): Promise<SeoCapabilities> {
    return requestJson<SeoCapabilities>(`${API_PATH}/capabilities`);
  },

  async getProviderStatus(): Promise<ProviderStatus> {
    return requestJson<ProviderStatus>(`${API_PATH}/providers/status`);
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
