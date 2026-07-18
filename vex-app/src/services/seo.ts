import type {
  SeoAuditIssue,
  SeoAuditPage,
  SeoAuditRequest,
  SeoAuditResult,
  SeoIssuePriority,
  AuditComparison,
  AuditProgress,
  AuditListParams,
  AuditListResponse,
  ExportFormat,
  SeoProject,
  SeoCapabilities,
  ProviderStatus,
  SeoIssue,
} from "../types/seo";
import {
  ApiError,
  apiRequest,
  buildApiUrl,
  type ApiRequestOptions,
  type QueryParams,
} from "./apiClient";

// Re-export types for consumers
export type {
  SeoAuditIssue,
  SeoAuditPage,
  SeoAuditRequest,
  SeoAuditResult,
  SeoIssuePriority,
  AuditComparison,
  AuditProgress,
  AuditListParams,
  AuditListResponse,
  ExportFormat,
  SeoProject,
  SeoCapabilities,
  ProviderStatus,
  SeoIssue,
};

const SEO_API_PATH = "/seo/audits";

export interface StartedSeoAudit {
  auditId: string | null;
  resultUrl: string;
}

export async function createSeoAudit(request: SeoAuditRequest): Promise<SeoAuditResult> {
  const data = await requestSeoAudit(request);
  const audit = unwrapBackendAudit(data);
  if (!audit) {
    throw new Error("SEO audit cevabı beklenen formatta değil.");
  }

  return normalizeBackendAudit(audit);
}

export async function startSeoAudit(request: SeoAuditRequest): Promise<StartedSeoAudit> {
  const data = await requestSeoAudit(request);
  const audit = unwrapBackendAudit(data);
  return {
    auditId: audit ? stringValue(audit.id) || null : null,
    resultUrl: buildApiUrl(SEO_API_PATH),
  };
}

export async function fetchSeoAuditResult(resultUrl: string): Promise<SeoAuditResult> {
  const data = await requestWithHttpStatus<unknown>(resultUrl);
  const audit = unwrapBackendAudit(data);
  if (!audit) {
    throw new Error("SEO audit cevabı beklenen formatta değil.");
  }

  return normalizeBackendAudit(audit);
}

async function requestSeoAudit(request: SeoAuditRequest): Promise<unknown> {
  return apiRequest<unknown>(SEO_API_PATH, {
    method: "POST",
    body: {
      url: request.url,
      country: request.country,
      language: request.language,
      business_description: request.business_description,
      max_pages: request.max_pages,
      project_id: request.project_id,
    },
  });
}

export async function downloadSeoAuditExport(auditId: string, format: "markdown" | "json") {
  const blob = await apiRequest<Blob>(`${SEO_API_PATH}/${encodeURIComponent(auditId)}/export/${format}`, {
    responseType: "blob",
  });
  const extension = format === "markdown" ? "md" : "json";
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = `seo-audit-${auditId}.${extension}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

function unwrapBackendAudit(value: unknown): Record<string, unknown> | null {
  if (!isRecord(value)) {
    return null;
  }

  if (isRecord(value.audit)) {
    return value.audit;
  }

  return typeof value.id === "string" ? value : null;
}

function normalizeBackendAudit(audit: Record<string, unknown>): SeoAuditResult {
  const pages = arrayOfRecords(audit.pages).map(normalizePage);
  const issues = arrayOfRecords(audit.issues).map(normalizeIssue);
  const priorityCounts = countPriorities(issues);
  const siteSignals = isRecord(audit.site_signals) ? audit.site_signals : {};

  return {
    audit_id: stringValue(audit.id),
    status: stringValue(audit.status) || "completed",
    summary: {
      score: numberValue(audit.score),
      pages: numberValue(audit.crawled_pages),
      pages_crawled: numberValue(audit.crawled_pages),
      total_pages: numberValue(audit.max_pages),
      discovered_urls: numberValue(siteSignals.discovered_urls),
      skipped_urls: numberValue(siteSignals.skipped_urls),
      blocked_urls: numberValue(siteSignals.blocked_urls),
      errored_urls: numberValue(siteSignals.errored_urls),
      platform: stringValue(siteSignals.platform),
      platform_confidence: stringValue(siteSignals.platform_confidence),
      p0: priorityCounts.P0,
      p1: priorityCounts.P1,
      p2: priorityCounts.P2,
      p3: priorityCounts.P3,
      issues: issues.length,
    },
    crawl_stats: {
      discovered_urls: numberValue(siteSignals.discovered_urls),
      crawled_urls: numberValue(siteSignals.crawled_urls),
      skipped_urls: numberValue(siteSignals.skipped_urls),
      blocked_urls: numberValue(siteSignals.blocked_urls),
      errored_urls: numberValue(siteSignals.errored_urls),
    },
    pages,
    issues,
    keyword_recommendations: pages.map((page) => ({
      page_url: page.url,
      keyword: firstHeading(page) || page.title || "Sayfa ana konusu",
      placement: "SEO title, meta description, H1, ilk paragraf, H2, görsel alt metni ve dahili bağlantı anchor metni",
      recommendation: "Frontend, backend sayfa başlığı ve H1 alanlarından heuristic anahtar kelime yerleşim önerisi türetir.",
      reason: "Bu MVP gerçek arama hacmi, trafik veya sıralama verisi üretmez; öneri backend audit alanlarından türetilir.",
      source: "heuristic",
    })),
    content_recommendations: arrayOfRecords(audit.recommendations).map((item) => ({
      title: stringValue(item.title),
      recommendation: stringValue(item.detail),
      reason: "Frontend, backend deterministik SEO bulgularından etiketli heuristic öneri türetir.",
      source: "heuristic",
      page_url: "",
    })),
    implementation_plan: issues.slice(0, 12).map((issue) => ({
      priority: issue.priority,
      title: issue.name,
      task: issue.recommended,
      impact: stringValue(issue.expected_impact),
      effort: issue.priority === "P0" || issue.priority === "P1" ? "high" : "medium",
      steps: [issue.how_to_fix || "İlgili SEO alanını önerilen değerle güncelle."],
    })),
  };
}

function normalizePage(page: Record<string, unknown>): SeoAuditPage {
  const issues = arrayOfRecords(page.issues).map(normalizeIssue);
  const pageScore = nullableNumberValue(page.page_score);
  return {
    url: stringValue(page.url),
    status: numberValue(page.status_code),
    score: pageScore ?? undefined,
    page_score: pageScore,
    page_type: stringValue(page.page_type),
    platform: stringValue(page.platform),
    score_reasons: stringArray(page.score_reasons),
    title: stringValue(page.title),
    h1: stringArray(page.h1),
    index: booleanValue(page.indexable),
    indexable: booleanValue(page.indexable),
    word_count: numberValue(page.word_count),
    issues,
    meta_description: stringValue(page.meta_description),
    canonical: stringValue(page.canonical),
    robots: stringValue(page.robots),
  };
}

function normalizeIssue(issue: Record<string, unknown>): SeoAuditIssue {
  const priority = stringValue(issue.severity) as SeoIssuePriority;
  return {
    id: stringValue(issue.code),
    priority,
    name: stringValue(issue.message),
    title: stringValue(issue.message),
    url: stringValue(issue.url),
    page_url: stringValue(issue.url),
    current: stringValue(issue.current_value) || "Bulunamadı",
    current_value: stringValue(issue.current_value) || "Bulunamadı",
    recommended: stringValue(issue.recommendation),
    recommendation: stringValue(issue.recommendation),
    explanation: "Bu bulgu teknik ve on-page SEO skorunu düşüren deterministik bir kontrolden geldi.",
    how: stringValue(issue.recommendation),
    how_to_fix: stringValue(issue.recommendation),
    platform: stringValue(issue.platform_hint) || "Bilinmeyen platform",
    category: stringValue(issue.scope) || (stringValue(issue.code).includes("title") || stringValue(issue.code).includes("h1") ? "on_page" : "technical"),
    page_type: stringValue(issue.page_type),
    scope: stringValue(issue.scope),
    expected_impact: priority === "P0" || priority === "P1" ? "Yüksek" : "Orta",
  };
}

function countPriorities(issues: SeoAuditIssue[]): { P0: number; P1: number; P2: number; P3: number } {
  const counts = { P0: 0, P1: 0, P2: 0, P3: 0 };
  for (const issue of issues) {
    if (issue.priority === "P0") counts.P0 += 1;
    if (issue.priority === "P1") counts.P1 += 1;
    if (issue.priority === "P2") counts.P2 += 1;
    if (issue.priority === "P3") counts.P3 += 1;
  }
  return counts;
}

function firstHeading(page: SeoAuditPage) {
  return Array.isArray(page.h1) ? page.h1[0] : page.h1;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function arrayOfRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function stringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function numberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function nullableNumberValue(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function booleanValue(value: unknown) {
  return typeof value === "boolean" ? value : false;
}

// List audits with pagination and filtering
export async function fetchAuditHistory(params: AuditListParams = {}): Promise<AuditListResponse> {
  const query: QueryParams = {
    page: params.page || undefined,
    page_size: params.page_size || undefined,
    status: params.status?.join(","),
    project_id: params.project_id || undefined,
    date_from: params.date_from || undefined,
    date_to: params.date_to || undefined,
    min_score: params.min_score,
    max_score: params.max_score,
    search: params.search || undefined,
    sort_by: params.sort_by,
    sort_order: params.sort_order,
  };

  return requestWithHttpStatus<AuditListResponse>(SEO_API_PATH, { query });
}

// Compare two audits
export async function compareAudits(currentAuditId: string, baselineAuditId: string): Promise<AuditComparison> {
  return requestWithHttpStatus<AuditComparison>(`${SEO_API_PATH}/${currentAuditId}/compare`, {
    query: { baseline_id: baselineAuditId },
  });
}

// Get audit progress for polling
export async function fetchAuditProgress(auditId: string): Promise<AuditProgress> {
  return requestWithHttpStatus<AuditProgress>(`${SEO_API_PATH}/${auditId}/progress`);
}

// Export audit as CSV
export async function exportAuditCsv(
  auditId: string,
  type: "issues" | "pages" | "both" = "issues"
): Promise<string> {
  return requestWithHttpStatus<string>(`${SEO_API_PATH}/${auditId}/export/csv`, {
    query: { type },
    responseType: "text",
  });
}

// Download audit CSV export
export async function downloadAuditCsv(auditId: string, type: "issues" | "pages" | "both" = "issues"): Promise<void> {
  const blob = await requestWithHttpStatus<Blob>(`${SEO_API_PATH}/${auditId}/export/csv`, {
    query: { type },
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `seo-audit-${auditId}-${type}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

async function requestWithHttpStatus<T>(
  path: string,
  options: ApiRequestOptions = {}
): Promise<T> {
  try {
    return await apiRequest<T>(path, options);
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status !== null) {
      throw new Error(`HTTP ${error.status}`);
    }
    throw error;
  }
}

// Poll audit progress until completion
export async function pollAuditProgress(
  auditId: string,
  onProgress: (progress: AuditProgress) => void,
  intervalMs = 2000,
  timeoutMs = 300000
): Promise<AuditProgress> {
  const startTime = Date.now();

  while (true) {
    const progress = await fetchAuditProgress(auditId);
    onProgress(progress);

    if (progress.status === "completed" || progress.status === "failed") {
      return progress;
    }

    if (Date.now() - startTime > timeoutMs) {
      throw new Error("Audit progress polling timeout");
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
