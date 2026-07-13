import type {
  SeoAuditIssue,
  SeoAuditPage,
  SeoAuditRequest,
  SeoAuditResult,
  SeoIssuePriority,
} from "../types/seo";

const SEO_API_BASE = "http://127.0.0.1:8000/seo/audits";

async function readErrorMessage(response: Response) {
  const text = await response.text().catch(() => "");
  if (!text) {
    return `HTTP ${response.status}`;
  }

  try {
    const parsed: unknown = JSON.parse(text);
    if (isErrorObject(parsed)) {
      return parsed.detail ?? parsed.message ?? `HTTP ${response.status}`;
    }
  } catch {
    return text;
  }

  return text;
}

function isErrorObject(value: unknown): value is { detail?: string; message?: string } {
  return typeof value === "object" && value !== null;
}

export async function createSeoAudit(request: SeoAuditRequest): Promise<SeoAuditResult> {
  const response = await fetch(SEO_API_BASE, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      url: request.url,
      country: request.country,
      language: request.language,
      business_description: request.business_description,
      max_pages: request.max_pages,
    }),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  const data: unknown = await response.json();
  const audit = unwrapBackendAudit(data);
  if (!audit) {
    throw new Error("SEO audit cevabı beklenen formatta değil.");
  }

  return normalizeBackendAudit(audit);
}

export async function downloadSeoAuditExport(auditId: string, format: "markdown" | "json") {
  const response = await fetch(`${SEO_API_BASE}/${encodeURIComponent(auditId)}/export/${format}`);

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  const blob = await response.blob();
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
