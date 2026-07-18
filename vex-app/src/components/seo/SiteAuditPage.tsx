import React, { useState, useEffect, useMemo } from "react";
import { createElement } from "react";
import {
  fetchAuditHistory,
  compareAudits,
  downloadAuditCsv,
  fetchSeoAuditResult,
  pollAuditProgress,
  startSeoAudit,
  type SeoAuditResult,
  type SeoAuditIssue,
  type SeoAuditPage,
  type AuditComparison,
  type AuditProgress,
  type AuditListParams,
  type AuditListResponse,
} from "../../services/seo";
import { SeoProjectService } from "../../services/seoProjectService";
import {
  IssueBadge,
  ScoreDisplay,
  ScoreRing,
  PageTypeBadge,
  CategoryBadge,
  MetricItem,
  IssueItem,
  SeoSummaryCard,
  ProgressBar,
  DataTable,
  FilterBar,
  Pagination,
  Column,
} from "./SeoUIComponents";
import { SeoProjectSelector } from "./SeoProjectSelector";
import { IssueSeverity, PageType } from "../../types/seo";

interface SiteAuditPageProps {
  initialProjectId?: string;
}

interface TabState {
  id: string;
  label: string;
}

const TABS: TabState[] = [
  { id: "overview", label: "Genel Bakış" },
  { id: "issues", label: "Sorunlar" },
  { id: "pages", label: "Taranan Sayfalar" },
  { id: "statistics", label: "İstatistikler" },
  { id: "history", label: "Audit Geçmişi" },
  { id: "comparison", label: "Karşılaştırma" },
];

interface IssueFilters {
  severity: string[];
  category: string[];
  pageType: string[];
  status: string[];
}

interface PageFilters {
  pageType: string[];
  status: string[];
}

// Pre-typed column definitions to avoid inference issues
const renderIssueCode = (row: SeoAuditIssue): React.ReactNode =>
  createElement("span", { className: "issue-code" }, String(row.id ?? row.code ?? ""));

const renderIssueMessage = (row: SeoAuditIssue): React.ReactNode =>
  createElement("div", { className: "issue-message" }, String(row.name ?? row.message ?? ""));

const renderIssueUrl = (row: SeoAuditIssue): React.ReactNode => (
  <div className="issue-url" title={row.url || row.page_url || ""}>
    {row.url || row.page_url || ""}
  </div> as React.ReactNode
);

const renderIssuePageType = (row: SeoAuditIssue): React.ReactNode => (
  <PageTypeBadge pageType={(row.page_type as PageType) || "unknown"} size="sm" /> as React.ReactNode
);

const renderIssueSeverity = (row: SeoAuditIssue): React.ReactNode => (
  <IssueBadge severity={row.priority as IssueSeverity} size="sm" /> as React.ReactNode
);

const renderIssueCategory = (row: SeoAuditIssue): React.ReactNode => (
  <CategoryBadge category={row.category || ""} /> as React.ReactNode
);

const renderPageUrl = (row: SeoAuditPage): React.ReactNode => (
  <div
    className="page-url"
    title={row.url}
    style={{ maxWidth: "320px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
  >
    {row.url}
  </div> as React.ReactNode
);

const renderPageType = (row: SeoAuditPage): React.ReactNode => (
  <PageTypeBadge pageType={(row.page_type as PageType) || "unknown"} size="sm" /> as React.ReactNode
);

const renderPageStatus = (row: SeoAuditPage): React.ReactNode => {
  const status = typeof row.status === "number" ? row.status : parseInt(String(row.status || 0), 10);
  const statusClass =
    status >= 200 && status < 300
      ? "2xx"
      : status >= 300 && status < 400
        ? "3xx"
        : "4xx";
  return (
    <span className={`status-badge status-${statusClass}`}>
      {row.status}
    </span>
  ) as React.ReactNode;
};

const renderPageScore = (row: SeoAuditPage): React.ReactNode => (
  <ScoreDisplay score={row.score || row.page_score || 0} size="sm" showLabel={false} /> as React.ReactNode
);

const renderPageWordCount = (row: SeoAuditPage): React.ReactNode => String(row.word_count || 0) as React.ReactNode;

const renderPageIndexable = (row: SeoAuditPage): React.ReactNode => (
  <span className={row.indexable ? "indexable-yes" : "indexable-no"}>
    {row.indexable ? "Evet" : "Hayır"}
  </span> as React.ReactNode
);

const issueColumnsDef: Column<SeoAuditIssue>[] = [
  {
    key: "severity",
    header: "Önem",
    width: "100px",
    sortable: true,
    render: renderIssueSeverity,
  },
  {
    key: "category",
    header: "Kategori",
    width: "140px",
    sortable: true,
    render: renderIssueCategory,
  },
  {
    key: "code",
    header: "Kod",
    width: "140px",
    sortable: true,
    render: renderIssueCode,
  },
  {
    key: "message",
    header: "Mesaj",
    sortable: true,
    render: renderIssueMessage,
  },
  {
    key: "url",
    header: "URL",
    width: "300px",
    render: renderIssueUrl,
  },
  {
    key: "page_type",
    header: "Sayfa Tipi",
    width: "120px",
    sortable: true,
    render: renderIssuePageType,
  },
];

const pageColumnsDef: Column<SeoAuditPage>[] = [
  {
    key: "url",
    header: "URL",
    width: "350px",
    sortable: true,
    render: renderPageUrl,
  },
  {
    key: "page_type",
    header: "Tip",
    width: "120px",
    sortable: true,
    render: renderPageType,
  },
  {
    key: "status",
    header: "Durum",
    width: "80px",
    sortable: true,
    render: renderPageStatus,
  },
  {
    key: "score",
    header: "Skor",
    width: "80px",
    sortable: true,
    render: renderPageScore,
  },
  {
    key: "word_count",
    header: "Kelime",
    width: "80px",
    sortable: true,
    render: renderPageWordCount,
  },
  {
    key: "indexable",
    header: "İndekslenebilir",
    width: "120px",
    sortable: true,
    render: renderPageIndexable,
  },
];

export function SiteAuditPage({ initialProjectId }: SiteAuditPageProps) {
  // Project state
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(initialProjectId || null);
  const [loadingProjects, setLoadingProjects] = useState(true);

  // Active tab
  const [activeTab, setActiveTab] = useState("overview");

  // Audit state
  const [currentAudit, setCurrentAudit] = useState<SeoAuditResult | null>(null);
  const [auditStatus, setAuditStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [auditProgress, setAuditProgress] = useState<AuditProgress | null>(null);

  // Audit form state
  const [auditForm, setAuditForm] = useState({
    url: "",
    country: "TR",
    language: "tr",
    business_description: "",
    max_pages: 100,
  });

  // Issues tab state
  const [issuesFilters, setIssuesFilters] = useState<IssueFilters>({
    severity: [],
    category: [],
    pageType: [],
    status: [],
  });
  const [issuesPage, setIssuesPage] = useState(1);
  const [issuesPageSize, setIssuesPageSize] = useState(20);
  const [issuesSort, setIssuesSort] = useState<{ column: string; direction: "asc" | "desc" }>({
    column: "severity",
    direction: "desc",
  });
  const [filteredIssues, setFilteredIssues] = useState<SeoAuditIssue[]>([]);
  const [issuesTotal, setIssuesTotal] = useState(0);

  // Pages tab state
  const [pagesFilters, setPagesFilters] = useState<PageFilters>({
    pageType: [],
    status: [],
  });
  const [pagesPage, setPagesPage] = useState(1);
  const [pagesPageSize, setPagesPageSize] = useState(20);
  const [pagesSort, setPagesSort] = useState<{ column: string; direction: "asc" | "desc" }>({
    column: "url",
    direction: "asc",
  });
  const [filteredPages, setFilteredPages] = useState<SeoAuditPage[]>([]);
  const [pagesTotal, setPagesTotal] = useState(0);
  const [selectedPage, setSelectedPage] = useState<SeoAuditPage | null>(null);

  // History tab state
  const [auditHistory, setAuditHistory] = useState<AuditListResponse | null>(null);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyPageSize, setHistoryPageSize] = useState(10);
  const [historyFilters, setHistoryFilters] = useState<AuditListParams>({
    page: 1,
    page_size: 10,
    sort_by: "created_at",
    sort_order: "desc",
  });

  // Comparison tab state
  const [comparison, setComparison] = useState<AuditComparison | null>(null);
  const [baselineAuditId, setBaselineAuditId] = useState<string>("");
  const [comparisonAuditId, setComparisonAuditId] = useState<string>("");
  const [comparisonLoading, setComparisonLoading] = useState(false);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProjectId) {
      loadAuditHistory();
    }
  }, [selectedProjectId]);

  // Load projects
  const loadProjects = async () => {
    try {
      const result = await SeoProjectService.listProjects();
      if (result.length > 0 && !selectedProjectId) {
        setSelectedProjectId(result[0].id);
      }
    } catch (error) {
      console.error("Failed to load projects:", error);
    } finally {
      setLoadingProjects(false);
    }
  };

  // Load audit history
  const loadAuditHistory = async () => {
    if (!selectedProjectId) return;
    try {
      const params: AuditListParams = {
        page: historyPage,
        page_size: historyPageSize,
        project_id: selectedProjectId,
        ...historyFilters,
      };
      const result = await fetchAuditHistory(params);
      setAuditHistory(result);
    } catch (error) {
      console.error("Failed to load audit history:", error);
    }
  };

  // Handle audit with progress polling
  const handleStartAuditWithProgress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProjectId || !auditForm.url) return;

    setAuditStatus("running");
    setCurrentAudit(null);
    setAuditProgress(null);

    try {
      const response = await startSeoAudit({
        ...auditForm,
        project_id: selectedProjectId,
      });
      const auditId = response.auditId;

      if (auditId) {
        // Start polling
        const result = await pollAuditProgress(
          auditId,
          (progress) => setAuditProgress(progress),
          2000,
          300000
        );

        if (result.status === "completed") {
          const auditResult = await fetchSeoAuditResult(response.resultUrl);
          setCurrentAudit(auditResult);
          setAuditStatus("completed");
          loadAuditHistory();
        } else if (result.status === "failed") {
          setAuditStatus("failed");
        }
      }
    } catch (error) {
      console.error("Audit failed:", error);
      setAuditStatus("failed");
    }
  };

  // Compute issues filters from data
  const issuesFilterOptions = useMemo(() => {
    if (!currentAudit?.issues) return { severity: [], category: [], pageType: [], status: [] };

    const severitySet = new Set<string>();
    const categorySet = new Set<string>();
    const pageTypeSet = new Set<string>();

    currentAudit.issues.forEach((issue) => {
      if (issue.priority) severitySet.add(issue.priority);
      if (issue.category) categorySet.add(issue.category);
      if (issue.page_type) pageTypeSet.add(issue.page_type);
    });

    const toOptions = (set: Set<string>) =>
      Array.from(set).map((value) => ({
        value,
        label: value,
        count: currentAudit.issues?.filter((i) =>
          i.priority === value || i.category === value || i.page_type === value
        ).length,
      }));

    return {
      severity: toOptions(severitySet),
      category: toOptions(categorySet),
      pageType: toOptions(pageTypeSet),
      status: [],
    };
  }, [currentAudit?.issues]);

  // Filter and sort issues
  useEffect(() => {
    if (!currentAudit?.issues) {
      setFilteredIssues([]);
      setIssuesTotal(0);
      return;
    }

    let result = [...currentAudit.issues];

    // Apply filters
    if (issuesFilters.severity.length > 0) {
      result = result.filter((i) => issuesFilters.severity.includes(i.priority || ""));
    }
    if (issuesFilters.category.length > 0) {
      result = result.filter((i) => issuesFilters.category.includes(i.category || ""));
    }
    if (issuesFilters.pageType.length > 0) {
      result = result.filter((i) => issuesFilters.pageType.includes(i.page_type || ""));
    }

    // Sort
    result.sort((a: SeoAuditIssue, b: SeoAuditIssue) => {
      const col = issuesSort.column as keyof SeoAuditIssue;
      const aVal = a[col];
      const bVal = b[col];
      const direction = issuesSort.direction === "asc" ? 1 : -1;
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return -1 * direction;
      if (bVal == null) return 1 * direction;
      if (aVal < bVal) return -1 * direction;
      if (aVal > bVal) return 1 * direction;
      return 0;
    });

    setIssuesTotal(result.length);
    const start = (issuesPage - 1) * issuesPageSize;
    setFilteredIssues(result.slice(start, start + issuesPageSize));
  }, [currentAudit?.issues, issuesFilters, issuesPage, issuesPageSize, issuesSort]);

  // Compute pages filters from data
  const pagesFilterOptions = useMemo(() => {
    if (!currentAudit?.pages) return { pageType: [], status: [] };

    const pageTypeSet = new Set<string>();
    const statusSet = new Set<string>();

    currentAudit.pages.forEach((page) => {
      if (page.page_type) pageTypeSet.add(page.page_type);
      if (page.status) statusSet.add(String(page.status));
    });

    const toOptions = (set: Set<string>) =>
      Array.from(set).map((value) => ({
        value,
        label: value,
        count: currentAudit.pages?.filter((p) =>
          p.page_type === value || String(p.status) === value
        ).length,
      }));

    return {
      pageType: toOptions(pageTypeSet),
      status: toOptions(statusSet),
    };
  }, [currentAudit?.pages]);

  // Filter and sort pages
  useEffect(() => {
    if (!currentAudit?.pages) {
      setFilteredPages([]);
      setPagesTotal(0);
      return;
    }

    let result = [...currentAudit.pages];

    if (pagesFilters.pageType.length > 0) {
      result = result.filter((p) => pagesFilters.pageType.includes(p.page_type || ""));
    }
    if (pagesFilters.status.length > 0) {
      result = result.filter((p) => pagesFilters.status.includes(String(p.status)));
    }

    result.sort((a: SeoAuditPage, b: SeoAuditPage) => {
      const col = pagesSort.column as keyof SeoAuditPage;
      const aVal = a[col];
      const bVal = b[col];
      const direction = pagesSort.direction === "asc" ? 1 : -1;
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return -1 * direction;
      if (bVal == null) return 1 * direction;
      if (aVal < bVal) return -1 * direction;
      if (aVal > bVal) return 1 * direction;
      return 0;
    });

    setPagesTotal(result.length);
    const start = (pagesPage - 1) * pagesPageSize;
    setFilteredPages(result.slice(start, start + pagesPageSize));
  }, [currentAudit?.pages, pagesFilters, pagesPage, pagesPageSize, pagesSort]);

  // Issues columns
  const issuesColumns = issueColumnsDef;

  // Pages columns
  const pagesColumns = pageColumnsDef;

  // Handle CSV export for issues
  const handleExportIssuesCsv = async () => {
    if (!currentAudit?.audit_id) return;
    try {
      await downloadAuditCsv(currentAudit.audit_id, "issues");
    } catch (error) {
      console.error("CSV export failed:", error);
    }
  };

  // Handle CSV export for pages
  const handleExportPagesCsv = async () => {
    if (!currentAudit?.audit_id) return;
    try {
      await downloadAuditCsv(currentAudit.audit_id, "pages");
    } catch (error) {
      console.error("CSV export failed:", error);
    }
  };

  // Handle comparison
  const handleCompare = async () => {
    if (!baselineAuditId || !comparisonAuditId) return;
    setComparisonLoading(true);
    try {
      const result = await compareAudits(comparisonAuditId, baselineAuditId);
      setComparison(result);
    } catch (error) {
      console.error("Comparison failed:", error);
    } finally {
      setComparisonLoading(false);
    }
  };

  // Render functions for tabs
  const renderOverviewTab = () => {
    if (!currentAudit) {
      return (
        <div className="audit-empty-state">
          <div className="empty-icon">📊</div>
          <h3>Henüz audit verisi yok</h3>
          <p>Yeni bir site audit başlatmak için yukarıdaki formu doldurun.</p>
        </div>
      );
    }

    const summary = currentAudit.summary ?? { score: 0, p0: 0, p1: 0, p2: 0, p3: 0, pages_crawled: 0, discovered_urls: 0 };
    const p0 = summary.p0 || 0;
    const p1 = summary.p1 || 0;
    const p2 = summary.p2 || 0;
    const p3 = summary.p3 || 0;
    const totalIssues = p0 + p1 + p2 + p3;

    return (
      <div className="site-audit-overview">
        <div className="overview-score-section">
          <ScoreRing score={summary.score || 0} size={140} strokeWidth={8} />
          <div className="overview-score-labels">
            <span className="score-title">Genel SEO Skoru</span>
            <span className="score-value">{summary.score}/100</span>
          </div>
        </div>

        <div className="overview-summary-grid">
          <SeoSummaryCard
            title="Taranan Sayfa"
            value={summary.pages_crawled || 0}
            subtitle={`Keşfedilen: ${summary.discovered_urls || 0}`}
          />
          <SeoSummaryCard
            title="Toplam Sorun"
            value={totalIssues}
            subtitle="Tüm kategorilerde"
            className="seo-summary-warning"
          />
          <SeoSummaryCard
            title="Kritik (P0)"
            value={p0}
            subtitle="Hemen düzeltilmeli"
            className="seo-summary-critical"
          />
          <SeoSummaryCard
            title="Yüksek (P1)"
            value={p1}
            subtitle="Yüksek öncelik"
            className="seo-summary-warning"
          />
          <SeoSummaryCard
            title="Orta (P2)"
            value={p2}
            subtitle="Planlanmalı"
          />
          <SeoSummaryCard
            title="Düşük (P3)"
            value={p3}
            subtitle="İyileştirme"
          />
        </div>

        <div className="overview-sections">
          <div className="overview-section">
            <h3>Uygulama Planı (İlk 12 Öncelikli Görev)</h3>
            <div className="implementation-list">
              {currentAudit.implementation_plan?.slice(0, 12).map((item, idx) => (
                <div key={idx} className={`impl-item priority-${item.priority?.toLowerCase()}`}>
                  <div className="impl-header">
                    <span className="impl-priority">{item.priority}</span>
                    <span className="impl-title">{item.title}</span>
                    <span className="impl-impact">{item.impact}</span>
                  </div>
                  <div className="impl-task">{item.task}</div>
                  <div className="impl-steps">
                    {item.steps?.map((step, si) => (
                      <div key={si} className="impl-step">
                        {si + 1}. {step}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="overview-section">
            <h3>Kategori Bazlı Dağılım</h3>
            <div className="category-breakdown">
              {currentAudit.issues?.reduce((acc, issue) => {
                const cat = issue.category || "other";
                acc[cat] = (acc[cat] || 0) + 1;
                return acc;
              }, {} as Record<string, number>) &&
              Object.entries(
                currentAudit.issues.reduce((acc, issue) => {
                  const cat = issue.category || "other";
                  acc[cat] = (acc[cat] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>)
              ).map(([category, count]) => (
                <div key={category} className="category-row">
                  <CategoryBadge category={category} />
                  <span>{count} sorun</span>
                  <div className="category-bar">
                    <div
                      className="category-bar-fill"
                      style={{ width: `${(count / totalIssues) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="overview-section">
          <h3>Anahtar Kelime Önerileri</h3>
          <div className="keyword-recommendations">
            {currentAudit.keyword_recommendations?.slice(0, 10).map((rec, idx) => (
              <div key={idx} className="keyword-rec">
                <strong>{rec.keyword}</strong> — {rec.page_url}
                <br />
                <small style={{ color: "#8d96aa" }}>{rec.placement}</small>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  const renderIssuesTab = () => {
    if (!currentAudit) {
      return <div className="audit-empty-state">Önce bir audit başlatın.</div>;
    }

    const hasFilters = issuesFilters.severity.length > 0 || issuesFilters.category.length > 0 || issuesFilters.pageType.length > 0;

    return (
      <div className="site-audit-tab">
        <FilterBar
          filters={issuesFilterOptions}
          selected={issuesFilters}
          onChange={(type, value) => {
            const newValue = Array.isArray(value) ? value : [value];
            const current = issuesFilters[type as keyof IssueFilters];
            const arr = current || [];
            const newArr = arr.includes(newValue[0]) ? arr.filter((v) => v !== newValue[0]) : [...arr, newValue[0]];
            setIssuesFilters((prev) => ({ ...prev, [type]: newArr }));
            setIssuesPage(1);
          }}
          onClearAll={() => setIssuesFilters({ severity: [], category: [], pageType: [], status: [] })}
          hasActiveFilters={hasFilters}
        />

        <div className="tab-toolbar">
          <div className="toolbar-left">
            <span>{issuesTotal} sorun</span>
            <button onClick={handleExportIssuesCsv} className="small-action-button">
              📥 CSV İndir
            </button>
          </div>
        </div>

        <DataTable
          data={filteredIssues}
          columns={issuesColumns}
          keyExtractor={(row) => `${row.id}-${row.url}`}
          sortColumn={issuesSort.column}
          sortDirection={issuesSort.direction}
          onSort={(col) =>
            setIssuesSort((prev) => ({
              column: col,
              direction: prev.column === col && prev.direction === "asc" ? "desc" : "asc",
            }))
          }
          className="data-table-container"
        />

        <Pagination
          currentPage={issuesPage}
          totalPages={Math.ceil(issuesTotal / issuesPageSize) || 1}
          pageSize={issuesPageSize}
          totalItems={issuesTotal}
          onPageChange={setIssuesPage}
          onPageSizeChange={(size) => {
            setIssuesPageSize(size);
            setIssuesPage(1);
          }}
        />
      </div>
    );
  };

  const renderPagesTab = () => {
    if (!currentAudit) {
      return <div className="audit-empty-state">Önce bir audit başlatın.</div>;
    }

    const hasFilters = pagesFilters.pageType.length > 0 || pagesFilters.status.length > 0;

    return (
      <div className="site-audit-tab">
        <FilterBar
          filters={pagesFilterOptions}
          selected={pagesFilters}
          onChange={(type, value) => {
            const newValue = Array.isArray(value) ? value : [value];
            const current = pagesFilters[type as keyof PageFilters];
            const arr = current || [];
            const newArr = arr.includes(newValue[0]) ? arr.filter((v) => v !== newValue[0]) : [...arr, newValue[0]];
            setPagesFilters((prev) => ({ ...prev, [type]: newArr }));
            setPagesPage(1);
          }}
          onClearAll={() => setPagesFilters({ pageType: [], status: [] })}
          hasActiveFilters={hasFilters}
        />

        <div className="tab-toolbar">
          <div className="toolbar-left">
            <span>{pagesTotal} sayfa</span>
            <button onClick={handleExportPagesCsv} className="small-action-button">
              📥 CSV İndir
            </button>
          </div>
        </div>

        <DataTable
          data={filteredPages}
          columns={pagesColumns}
          keyExtractor={(row) => row.url || ""}
          onRowClick={setSelectedPage}
          sortColumn={pagesSort.column}
          sortDirection={pagesSort.direction}
          onSort={(col) =>
            setPagesSort((prev) => ({
              column: col,
              direction: prev.column === col && prev.direction === "asc" ? "desc" : "asc",
            }))
          }
          className="data-table-container"
        />

        <Pagination
          currentPage={pagesPage}
          totalPages={Math.ceil(pagesTotal / pagesPageSize) || 1}
          pageSize={pagesPageSize}
          totalItems={pagesTotal}
          onPageChange={setPagesPage}
          onPageSizeChange={(size) => {
            setPagesPageSize(size);
            setPagesPage(1);
          }}
        />

        {selectedPage && (
          <div className="page-detail-panel">
            <h3>Sayfa Detayı: {selectedPage.url}</h3>
            <div className="detail-grid">
              <MetricItem label="Status" value={String(selectedPage.status ?? "—")} />
              <MetricItem label="Skor" value={selectedPage.score ?? selectedPage.page_score ?? 0} />
              <MetricItem label="Tip" value={selectedPage.page_type ?? "unknown"} />
              <MetricItem
                label="İndekslenebilir"
                value={
                  typeof selectedPage.indexable === "boolean"
                    ? selectedPage.indexable
                      ? "Evet"
                      : "Hayır"
                    : selectedPage.indexable === "true"
                      ? "Evet"
                      : selectedPage.indexable === "false"
                        ? "Hayır"
                        : "—"
                }
              />
              <MetricItem label="Kelime Sayısı" value={selectedPage.word_count ?? 0} />
              <MetricItem label="Title" value={String(selectedPage.title ?? "—")} />
              <MetricItem label="Meta Description" value={String(selectedPage.meta_description ?? "—")} />
              <MetricItem label="Canonical" value={String(selectedPage.canonical ?? "—")} />
              <MetricItem label="Robots" value={String(selectedPage.robots ?? "—")} />
            </div>
            {Array.isArray(selectedPage.issues) && selectedPage.issues.length > 0 && (
              <div className="page-issues">
                <h4>Bu Sayfadaki Sorunlar ({selectedPage.issues.length})</h4>
                {selectedPage.issues.map((issue: SeoAuditIssue, idx) => (
                  <IssueItem
                    key={issue.id ?? idx}
                    issue={{
                      severity: (issue.priority as IssueSeverity) ?? "P3",
                      category: issue.category ?? "technical",
                      code: String(issue.id ?? issue.code ?? `issue-${idx}`),
                      message: String(issue.message ?? issue.name ?? issue.title ?? "Bilinmeyen sorun"),
                      url: issue.url ?? issue.page_url,
                      recommendation: issue.recommendation ?? issue.recommended ?? issue.how_to_fix ?? issue.how,
                      current_value: String(issue.current_value ?? issue.current ?? "Bulunamadı"),
                      expected_value: String(issue.expected_value ?? issue.expected ?? ""),
                    }}
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderStatisticsTab = () => {
    if (!currentAudit) {
      return <div className="audit-empty-state">Önce bir audit başlatın.</div>;
    }

    const crawlStats = currentAudit.crawl_stats ?? { discovered_urls: 0, crawled_urls: 0, skipped_urls: 0, blocked_urls: 0, errored_urls: 0 };
    const issues = currentAudit.issues || [];
    const pages = currentAudit.pages || [];

    // Computing stats
    const statusCodes: Record<string, number> = {};
    const pageTypes: Record<string, number> = {};
    const indexableCount = pages.filter((p) => p.indexable).length;
    const avgScore = pages.length > 0 ? Math.round(pages.reduce((s, p) => s + (p.score || p.page_score || 0), 0) / pages.length) : 0;
    const avgWords = pages.length > 0 ? Math.round(pages.reduce((s, p) => s + (p.word_count || 0), 0) / pages.length) : 0;

    pages.forEach((p) => {
      if (p.status) statusCodes[String(p.status)] = (statusCodes[String(p.status)] || 0) + 1;
      if (p.page_type) pageTypes[p.page_type] = (pageTypes[p.page_type] || 0) + 1;
    });

    const severityCounts = issues.reduce(
      (acc, i) => {
        acc[i.priority || "P3"] = (acc[i.priority || "P3"] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    return (
      <div className="site-audit-tab statistics-tab">
        <div className="stats-grid">
          <SeoSummaryCard
            title="Ortalama Sayfa Skoru"
            value={avgScore}
            subtitle="/ 100"
            icon={<ScoreDisplay score={avgScore} size="sm" showLabel={false} />}
          />
          <SeoSummaryCard
            title="Ortalama Kelime Sayısı"
            value={avgWords}
            subtitle="sayfa başına"
          />
          <SeoSummaryCard
            title="İndekslenebilir Sayfa"
            value={indexableCount}
            subtitle={`/${pages.length} toplam`}
          />
          <SeoSummaryCard
            title="Keşfedilen URL"
            value={crawlStats.discovered_urls || 0}
            subtitle={`Taranan: ${crawlStats.crawled_urls || 0}`}
          />
        </div>

        <div className="stats-sections">
          <div className="stat-section">
            <h3>HTTP Durum Kodları</h3>
            <div className="stat-table">
              {Object.entries(statusCodes)
                .sort((a, b) => b[1] - a[1])
                .map(([code, count]) => (
                  <div key={code} className="stat-row">
                    <span className={`status-code status-${code}`}>{code}</span>
                    <span>{count} sayfa</span>
                    <div className="stat-bar">
                      <div className="stat-bar-fill" style={{ width: `${(count / pages.length) * 100}%` }} />
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <div className="stat-section">
            <h3>Sayfa Tipleri</h3>
            <div className="stat-table">
              {Object.entries(pageTypes)
                .sort((a, b) => b[1] - a[1])
                .map(([type, count]) => (
                  <div key={type} className="stat-row">
                    <PageTypeBadge pageType={type as PageType} size="sm" />
                    <span>{count} sayfa</span>
                    <div className="stat-bar">
                      <div className="stat-bar-fill" style={{ width: `${(count / pages.length) * 100}%` }} />
                    </div>
                  </div>
                ))}
            </div>
          </div>

          <div className="stat-section">
            <h3>Sorun Önem Derecesi Dağılımı</h3>
            <div className="severity-breakdown">
              {(["P0", "P1", "P2", "P3"] as const).map((sev) => (
                <div key={sev} className="severity-row">
                  <IssueBadge severity={sev} size="sm" />
                  <span>{severityCounts[sev] || 0} sorun</span>
                  <div className="stat-bar">
                    <div
                      className={`stat-bar-fill severity-${sev.toLowerCase()}`}
                      style={{ width: `${((severityCounts[sev] || 0) / issues.length) * 100 || 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="stat-section">
            <h3>En Yaygın Sorun Kategorileri</h3>
            <div className="stat-table">
              {Object.entries(
                issues.reduce((acc, i) => {
                  const cat = i.category || "other";
                  acc[cat] = (acc[cat] || 0) + 1;
                  return acc;
                }, {} as Record<string, number>)
              )
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([cat, count]) => (
                  <div key={cat} className="stat-row">
                    <CategoryBadge category={cat} />
                    <span>{count} sorun</span>
                    <div className="stat-bar">
                      <div className="stat-bar-fill" style={{ width: `${(count / issues.length) * 100}%` }} />
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderHistoryTab = () => {
    if (!auditHistory) {
      return <div className="audit-empty-state">Audit geçmişi yükleniyor...</div>;
    }

    if (auditHistory.audits.length === 0) {
      return <div className="audit-empty-state">Henüz audit geçmişi yok.</div>;
    }

    return (
      <div className="site-audit-tab history-tab">
        <div className="history-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Tarih</th>
                <th>URL</th>
                <th>Skor</th>
                <th>Sayfa</th>
                <th>Sorun</th>
                <th>Durum</th>
                <th>İşlem</th>
              </tr>
            </thead>
            <tbody>
              {auditHistory.audits.map((audit) => (
                <tr key={audit.id}>
                  <td>{new Date(audit.created_at).toLocaleString("tr-TR")}</td>
                  <td style={{ maxWidth: "250px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {audit.requested_url}
                  </td>
                  <td>
                    <ScoreDisplay score={audit.score} size="sm" showLabel={false} />
                  </td>
                  <td>{audit.crawled_pages}</td>
                  <td>{audit.issues?.length || 0}</td>
                  <td>
                    <span className={`status-badge status-${audit.status}`}>{audit.status}</span>
                  </td>
                  <td>
                    <button
                      className="small-action-button"
                      onClick={() => setComparisonAuditId(audit.id)}
                      disabled={comparisonAuditId === audit.id || baselineAuditId === audit.id}
                    >
                      Karşılaştır
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <Pagination
          currentPage={auditHistory.page}
          totalPages={auditHistory.total_pages}
          pageSize={auditHistory.page_size}
          totalItems={auditHistory.total}
          onPageChange={(page) => {
            setHistoryPage(page);
            setHistoryFilters((prev) => ({ ...prev, page }));
            loadAuditHistory();
          }}
          onPageSizeChange={(size) => {
            setHistoryPageSize(size);
            setHistoryFilters((prev) => ({ ...prev, page_size: size, page: 1 }));
            setHistoryPage(1);
            loadAuditHistory();
          }}
        />
      </div>
    );
  };

  const renderComparisonTab = () => {
    return (
      <div className="site-audit-tab comparison-tab">
        <div className="comparison-selectors">
          <div className="comparison-selector">
            <label>Referans (Eski) Audit</label>
            <select
              value={baselineAuditId}
              onChange={(e) => setBaselineAuditId(e.target.value)}
              className="comparison-select"
            >
              <option value="">Seçiniz...</option>
              {auditHistory?.audits.map((a) => (
                <option key={a.id} value={a.id}>
                  {new Date(a.created_at).toLocaleString("tr-TR")} - {a.requested_url} (Skor: {a.score})
                </option>
              ))}
            </select>
          </div>

          <div className="comparison-selector">
            <label>Karşılaştırılacak (Yeni) Audit</label>
            <select
              value={comparisonAuditId}
              onChange={(e) => setComparisonAuditId(e.target.value)}
              className="comparison-select"
            >
              <option value="">Seçiniz...</option>
              {auditHistory?.audits.map((a) => (
                <option key={a.id} value={a.id}>
                  {new Date(a.created_at).toLocaleString("tr-TR")} - {a.requested_url} (Skor: {a.score})
                </option>
              ))}
            </select>
          </div>

          <button
            className="small-action-button"
            onClick={handleCompare}
            disabled={!baselineAuditId || !comparisonAuditId || comparisonLoading}
          >
            {comparisonLoading ? "Karşılaştırılıyor..." : "Karşılaştır"}
          </button>
        </div>

        {comparison && (
          <div className="comparison-results">
            <div className="comparison-cards">
              <div className="comparison-card">
                <h3>Skor Değişimi</h3>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Referans Skor</span>
                  <span className="comparison-metric-value neutral">{comparison.baseline_date.split("T")[0]}: {comparison.score_change_pct > 0 ? "?" : "?"}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Yeni Skor</span>
                  <span className="comparison-metric-value neutral">{comparison.comparison_date.split("T")[0]}: {comparison.score_change_pct > 0 ? "?" : "?"}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Değişim</span>
                  <span className={`comparison-metric-value ${comparison.score_change >= 0 ? "positive" : "negative"}`}>
                    {comparison.score_change >= 0 ? "+" : ""}{comparison.score_change} ({comparison.score_change_pct >= 0 ? "+" : ""}{comparison.score_change_pct.toFixed(1)}%)
                  </span>
                </div>
              </div>

              <div className="comparison-card">
                <h3>Sorun Değişimleri</h3>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Çözülen</span>
                  <span className="comparison-metric-value positive">{comparison.issues_resolved}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Yeni</span>
                  <span className="comparison-metric-value negative">{comparison.issues_new}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Kötüleşen</span>
                  <span className="comparison-metric-value negative">{comparison.issues_worsened}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">İyileşen</span>
                  <span className="comparison-metric-value positive">{comparison.issues_improved}</span>
                </div>
              </div>

              <div className="comparison-card">
                <h3>Sayfa Değişimleri</h3>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">İyileşen</span>
                  <span className="comparison-metric-value positive">{comparison.pages_improved}</span>
                </div>
                <div className="comparison-metric">
                  <span className="comparison-metric-label">Kötüleşen</span>
                  <span className="comparison-metric-value negative">{comparison.pages_declined}</span>
                </div>
              </div>
            </div>

            {comparison.top_improvements.length > 0 && (
              <div className="comparison-card">
                <h3>En İyi İyileştirmeler</h3>
                <ul className="comparison-list">
                  {comparison.top_improvements.map((imp, i) => (
                    <li key={i}>{imp}</li>
                  ))}
                </ul>
              </div>
            )}

            {comparison.top_regressions.length > 0 && (
              <div className="comparison-card">
                <h3>En Büyük Gerilemeler</h3>
                <ul className="comparison-list">
                  {comparison.top_regressions.map((reg, i) => (
                    <li key={i}>{reg}</li>
                  ))}
                </ul>
              </div>
            )}

            {comparison.category_changes && Object.keys(comparison.category_changes).length > 0 && (
              <div className="comparison-card">
                <h3>Kategori Bazlı Değişim</h3>
                <div className="comparison-metrics-grid">
                  {Object.entries(comparison.category_changes).map(([cat, change]) => (
                    <div key={cat} className="comparison-metric">
                      <CategoryBadge category={cat} />
                      <span className={`comparison-metric-value ${change >= 0 ? "positive" : "negative"}`}>
                        {change >= 0 ? "+" : ""}{change}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case "overview":
        return renderOverviewTab();
      case "issues":
        return renderIssuesTab();
      case "pages":
        return renderPagesTab();
      case "statistics":
        return renderStatisticsTab();
      case "history":
        return renderHistoryTab();
      case "comparison":
        return renderComparisonTab();
      default:
        return null;
    }
  };

  return (
    <div className="site-audit-page">
      <div className="site-audit-header">
        <SeoProjectSelector
          value={selectedProjectId || undefined}
          onChange={setSelectedProjectId}
          onCreateNew={() => {}}
          disabled={loadingProjects}
        />
      </div>

      {selectedProjectId && (
        <div className="audit-form-section">
          <form onSubmit={handleStartAuditWithProgress} className="seo-form">
            <div className="form-grid">
              <div className="form-field">
                <label>Başlangıç URL</label>
                <input
                  type="url"
                  value={auditForm.url}
                  onChange={(e) => setAuditForm((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder="https://example.com"
                  required
                />
              </div>
              <div className="form-field">
                <label>Ülke</label>
                <input
                  type="text"
                  value={auditForm.country}
                  onChange={(e) => setAuditForm((prev) => ({ ...prev, country: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Dil</label>
                <input
                  type="text"
                  value={auditForm.language}
                  onChange={(e) => setAuditForm((prev) => ({ ...prev, language: e.target.value }))}
                />
              </div>
              <div className="form-field">
                <label>Maks Sayfa</label>
                <input
                  type="number"
                  value={auditForm.max_pages}
                  onChange={(e) => setAuditForm((prev) => ({ ...prev, max_pages: Number(e.target.value) }))}
                  min={1}
                  max={500}
                />
              </div>
              <div className="form-field full-width">
                <label>İş Tanımı</label>
                <textarea
                  value={auditForm.business_description}
                  onChange={(e) => setAuditForm((prev) => ({ ...prev, business_description: e.target.value }))}
                  rows={2}
                  placeholder="İşletme hakkında kısa bir açıklama..."
                />
              </div>
            </div>
            <div className="form-actions seo-form-actions">
              <button type="submit" className="voice-primary-action" disabled={auditStatus === "running"}>
                {auditStatus === "running" ? "Audit Çalışıyor..." : "Site Audit Başlat"}
              </button>
              {auditStatus === "running" && auditProgress && (
                <ProgressBar progress={auditProgress.progress_pct} label={auditProgress.current_url} variant="default" />
              )}
              {auditStatus === "completed" && (
                <span className="audit-completed-badge">✓ Audit tamamlandı</span>
              )}
              {auditStatus === "failed" && (
                <span className="audit-failed-badge">✗ Audit başarısız oldu</span>
              )}
            </div>
          </form>
        </div>
      )}

      <div className="site-audit-tabs">
        <div className="seo-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              className={`seo-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              disabled={!selectedProjectId && tab.id !== "history"}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="seo-tab-content">{renderTabContent()}</div>
      </div>
    </div>
  );
}

export default SiteAuditPage;
