import type { SeoAuditRequest, SeoAuditResult } from "../types/seo";

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
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  const data: unknown = await response.json();
  if (!isSeoAuditResult(data)) {
    throw new Error("SEO audit cevabı beklenen formatta değil.");
  }

  return data;
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

function isSeoAuditResult(value: unknown): value is SeoAuditResult {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const audit = value as { audit_id?: unknown; status?: unknown };
  return typeof audit.audit_id === "string" && typeof audit.status === "string";
}
