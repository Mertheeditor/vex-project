import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchAuditHistory,
  fetchSeoAuditResult,
  pollAuditProgress,
  startSeoAudit,
  type SeoAuditIssue,
  type SeoAuditResult,
} from "../../services/seo";
import { SeoProjectService } from "../../services/seoProjectService";
import type { AuditProgress, SeoProject } from "../../types/seo";
import { SiteAuditPage } from "./SiteAuditPage";

vi.mock("../../services/seo", () => ({
  fetchAuditHistory: vi.fn(),
  compareAudits: vi.fn(),
  downloadAuditCsv: vi.fn(),
  fetchSeoAuditResult: vi.fn(),
  pollAuditProgress: vi.fn(),
  startSeoAudit: vi.fn(),
}));

vi.mock("../../services/seoProjectService", () => ({
  SeoProjectService: {
    listProjects: vi.fn(),
  },
}));

const project = makeProject();

describe("SiteAuditPage", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(SeoProjectService.listProjects).mockResolvedValue([project]);
    vi.mocked(fetchAuditHistory).mockResolvedValue({
      audits: [],
      total: 0,
      page: 1,
      page_size: 10,
      total_pages: 0,
      has_next: false,
      has_prev: false,
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders all six main tabs", async () => {
    render(<SiteAuditPage initialProjectId="project-1" />);

    for (const label of [
      "Genel Bakış",
      "Sorunlar",
      "Taranan Sayfalar",
      "İstatistikler",
      "Audit Geçmişi",
      "Karşılaştırma",
    ]) {
      expect(screen.getByRole("button", { name: label })).toBeVisible();
    }
    await waitFor(() => expect(fetchAuditHistory).toHaveBeenCalled());
  });

  it("shows the existing empty state when no audit is available", () => {
    render(<SiteAuditPage initialProjectId="project-1" />);

    expect(screen.getByRole("heading", { name: "Henüz audit verisi yok" })).toBeVisible();
    expect(screen.getByText("Yeni bir site audit başlatmak için yukarıdaki formu doldurun.")).toBeVisible();
  });

  it("shows project loading state while the service is pending", () => {
    vi.mocked(SeoProjectService.listProjects).mockReturnValue(new Promise(() => undefined));
    render(<SiteAuditPage />);

    expect(screen.getByRole("combobox")).toBeDisabled();
    expect(screen.getByRole("option", { name: "Yükleniyor..." })).toBeVisible();
    expect(screen.getByRole("button", { name: "Genel Bakış" })).toBeDisabled();
  });

  it("shows audit loading state without making a real network request", async () => {
    const user = userEvent.setup();
    vi.mocked(startSeoAudit).mockReturnValue(new Promise(() => undefined));
    render(<SiteAuditPage initialProjectId="project-1" />);

    await user.type(screen.getByPlaceholderText("https://example.com"), "https://vex.test");
    await user.click(screen.getByRole("button", { name: "Site Audit Başlat" }));

    expect(screen.getByRole("button", { name: "Audit Çalışıyor..." })).toBeDisabled();
  });

  it("shows the existing error state when the audit service fails", async () => {
    const user = userEvent.setup();
    vi.mocked(startSeoAudit).mockRejectedValue(new Error("audit service unavailable"));
    render(<SiteAuditPage initialProjectId="project-1" />);

    await user.type(screen.getByPlaceholderText("https://example.com"), "https://vex.test");
    await user.click(screen.getByRole("button", { name: "Site Audit Başlat" }));

    expect(await screen.findByText("✗ Audit başarısız oldu")).toBeVisible();
  });

  it("shows the existing error state when loading the completed audit fails", async () => {
    const user = userEvent.setup();
    stubCompletedAudit(makeAudit());
    vi.mocked(fetchSeoAuditResult).mockRejectedValue(new Error("audit result unavailable"));
    render(<SiteAuditPage initialProjectId="project-1" />);

    await user.type(screen.getByPlaceholderText("https://example.com"), "https://vex.test");
    await user.click(screen.getByRole("button", { name: "Site Audit Başlat" }));

    expect(await screen.findByText("✗ Audit başarısız oldu")).toBeVisible();
  });

  it("loads a completed audit through the SEO service without calling fetch directly", async () => {
    const audit = makeAudit();
    const fetchMock = vi.fn<typeof fetch>();
    const user = userEvent.setup();
    vi.stubGlobal("fetch", fetchMock);
    stubCompletedAudit(audit);
    render(<SiteAuditPage initialProjectId="project-1" />);

    await startAudit(user);

    expect(fetchSeoAuditResult).toHaveBeenCalledWith("http://127.0.0.1:8000/seo/audits");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByText("92/100")).toBeVisible();
  });

  it("renders real audit summary values in the overview cards", async () => {
    const audit = makeAudit();
    const user = userEvent.setup();
    stubCompletedAudit(audit);
    render(<SiteAuditPage initialProjectId="project-1" />);

    await startAudit(user);

    expect(await screen.findByText("92/100")).toBeVisible();
    expect(summaryCard("Taranan Sayfa")).toHaveTextContent("12");
    expect(summaryCard("Toplam Sorun")).toHaveTextContent("6");
    expect(summaryCard("Kritik (P0)")).toHaveTextContent("1");
    expect(summaryCard("Yüksek (P1)")).toHaveTextContent("2");
    expect(summaryCard("Orta (P2)")).toHaveTextContent("3");
  });

  it("renders issue severities with the matching badges", async () => {
    const user = userEvent.setup();
    stubCompletedAudit(makeAudit({
      issues: [makeIssue(1, "P0"), makeIssue(2, "P3")],
    }));
    render(<SiteAuditPage initialProjectId="project-1" />);

    await startAudit(user);
    await user.click(screen.getByRole("button", { name: "Sorunlar" }));

    expect((await screen.findAllByText("P0")).some((element: HTMLElement) => element.classList.contains("issue-badge-p0"))).toBe(true);
    expect(screen.getAllByText("P3").some((element: HTMLElement) => element.classList.contains("issue-badge-p3"))).toBe(true);
  });

  it("preserves pagination boundaries for audit issues", async () => {
    const user = userEvent.setup();
    const issues = Array.from({ length: 21 }, (_, index) => makeIssue(index + 1, "P2"));
    stubCompletedAudit(makeAudit({ issues }));
    render(<SiteAuditPage initialProjectId="project-1" />);

    await startAudit(user);
    await user.click(screen.getByRole("button", { name: "Sorunlar" }));

    const previous = screen.getByRole("button", { name: "Önceki sayfa" });
    const next = screen.getByRole("button", { name: "Sonraki sayfa" });
    expect(previous).toBeDisabled();
    expect(next).toBeEnabled();

    await user.click(next);

    expect(await screen.findByText("ISSUE-21")).toBeVisible();
    expect(previous).toBeEnabled();
    expect(next).toBeDisabled();
  });
});

async function startAudit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByPlaceholderText("https://example.com"), "https://vex.test");
  await user.click(screen.getByRole("button", { name: "Site Audit Başlat" }));
  await screen.findByText("✓ Audit tamamlandı");
}

function stubCompletedAudit(audit: SeoAuditResult) {
  vi.mocked(startSeoAudit).mockResolvedValue({
    auditId: "audit-1",
    resultUrl: "http://127.0.0.1:8000/seo/audits",
  });
  vi.mocked(fetchSeoAuditResult).mockResolvedValue(audit);
  vi.mocked(pollAuditProgress).mockResolvedValue(completedProgress());
}

function summaryCard(title: string) {
  const heading = screen.getByText(title);
  const card = heading.closest(".seo-summary-card");
  expect(card).not.toBeNull();
  return card as HTMLElement;
}

function makeAudit(overrides: Partial<SeoAuditResult> = {}): SeoAuditResult {
  return {
    audit_id: "audit-1",
    status: "completed",
    summary: {
      score: 92,
      pages_crawled: 12,
      discovered_urls: 14,
      p0: 1,
      p1: 2,
      p2: 3,
      p3: 0,
    },
    pages: [],
    issues: [makeIssue(1, "P0")],
    implementation_plan: [],
    keyword_recommendations: [],
    ...overrides,
  };
}

function makeIssue(index: number, priority: "P0" | "P1" | "P2" | "P3"): SeoAuditIssue {
  return {
    id: `ISSUE-${index}`,
    priority,
    category: "technical",
    name: `Teknik sorun ${index}`,
    url: `https://vex.test/page-${index}`,
    page_type: "content_page",
  };
}

function completedProgress(): AuditProgress {
  return {
    audit_id: "audit-1",
    status: "completed",
    progress_pct: 100,
    current_url: "https://vex.test",
    current_depth: 0,
    urls_queued: 0,
    urls_crawled: 12,
    urls_failed: 0,
    urls_skipped: 0,
    elapsed_seconds: 1,
    estimated_remaining_seconds: 0,
    pages_per_second: 12,
    recent_errors: [],
    timestamp: "2026-07-17T10:00:00Z",
  };
}

function makeProject(): SeoProject {
  return {
    id: "project-1",
    name: "Vex",
    domain: "vex.test",
    description: "",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    settings: { max_pages: 100, max_depth: 3 },
    audit_history: [],
    active_audit_id: null,
    last_audit_at: null,
    last_score: null,
  };
}
