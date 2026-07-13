import { useMemo, useState } from "react";
import { createSeoAudit, downloadSeoAuditExport } from "../services/seo";
import type {
  SeoAuditIssue,
  SeoAuditPage,
  SeoAuditRequest,
  SeoAuditResult,
  SeoAuditStage,
  SeoAuditStageKey,
  SeoAuditStatus,
} from "../types/seo";

type SeoTab =
  | "overview"
  | "technical"
  | "onPage"
  | "pages"
  | "keywords"
  | "content"
  | "plan";

const stageOrder: Array<{ key: SeoAuditStageKey; label: string }> = [
  { key: "connection", label: "Bağlantı" },
  { key: "robots_sitemap", label: "Robots/Sitemap" },
  { key: "crawl", label: "Crawl" },
  { key: "technical_seo", label: "Teknik SEO" },
  { key: "on_page", label: "On-page" },
  { key: "keyword_content", label: "Keyword/Content" },
  { key: "report_completed", label: "Rapor tamamlandı" },
];

const tabs: Array<{ key: SeoTab; label: string }> = [
  { key: "overview", label: "Genel Bakış" },
  { key: "technical", label: "Teknik SEO" },
  { key: "onPage", label: "Sayfa İçi SEO" },
  { key: "pages", label: "Sayfalar" },
  { key: "keywords", label: "Anahtar Kelimeler" },
  { key: "content", label: "İçerik Önerileri" },
  { key: "plan", label: "Uygulama Planı" },
];

const initialForm: SeoAuditRequest = {
  url: "",
  country: "Türkiye",
  language: "Türkçe",
  business_description: "",
  max_pages: 100,
};

export function SeoExpertPage() {
  const [form, setForm] = useState<SeoAuditRequest>(initialForm);
  const [status, setStatus] = useState<SeoAuditStatus>("initial");
  const [audit, setAudit] = useState<SeoAuditResult | null>(null);
  const [activeTab, setActiveTab] = useState<SeoTab>("overview");
  const [selectedPageUrl, setSelectedPageUrl] = useState<string>("");
  const [errorMessage, setErrorMessage] = useState("");
  const [isDownloading, setIsDownloading] = useState<"markdown" | "json" | null>(null);
  const selectedPage = useMemo(
    () => audit?.pages?.find((page) => page.url === selectedPageUrl) ?? null,
    [audit?.pages, selectedPageUrl],
  );

  const priorityCounts = getPriorityCounts(audit?.summary, audit?.issues ?? []);
  const visibleIssues = audit?.issues ?? [];
  const technicalIssues = visibleIssues.filter((issue) => normalizeCategory(issue).includes("technical"));
  const onPageIssues = visibleIssues.filter((issue) => {
    const category = normalizeCategory(issue);
    return category.includes("on") || category.includes("content") || category.includes("meta");
  });

  async function startAudit() {
    const cleanUrl = form.url.trim();

    if (!isValidHttpUrl(cleanUrl)) {
      setStatus("url_error");
      setErrorMessage("Geçerli bir http veya https URL gir.");
      setAudit(null);
      return;
    }

    setStatus("loading");
    setErrorMessage("");
    setAudit(null);
    setSelectedPageUrl("");
    setActiveTab("overview");

    try {
      const result = await createSeoAudit({ ...form, url: cleanUrl, max_pages: clampMaxPages(form.max_pages) });
      setAudit(result);
      setSelectedPageUrl(result.pages?.[0]?.url ?? "");
      setStatus(resolveUiStatus(result));
    } catch (error) {
      const message = error instanceof Error ? error.message : "SEO audit başlatılamadı.";
      setErrorMessage(message);
      setStatus(message.toLocaleLowerCase("tr-TR").includes("fetch") ? "unreachable" : "backend_error");
    }
  }

  async function handleDownload(format: "markdown" | "json") {
    if (!audit?.audit_id || isDownloading) {
      return;
    }

    setIsDownloading(format);
    try {
      await downloadSeoAuditExport(audit.audit_id, format);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Rapor indirilemedi.");
    } finally {
      setIsDownloading(null);
    }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Organik büyüme modülü</p>
          <h2>SEO Uzmanı</h2>
        </div>
        <div className="topbar-actions">
          <span className={`status-pill seo-status-${status}`}>{getStatusLabel(status)}</span>
          {audit?.audit_id ? <span className="status-pill">Audit: {audit.audit_id}</span> : null}
        </div>
      </header>

      <div className="seo-page">
        <section className="project-form seo-form">
          <div>
            <p className="eyebrow">Yeni audit</p>
            <h3>Siteyi gerçek backend analiziyle tara</h3>
            <p className="seo-muted">Demo veri yok; sonuçlar `/seo/audits` API yanıtından ve frontend’de etiketli heuristic türetimlerden gösterilir.</p>
          </div>

          <div className="form-grid">
            <label>
              URL
              <input
                value={form.url}
                onChange={(event) => setForm((current) => ({ ...current, url: event.target.value }))}
                placeholder="https://example.com"
              />
            </label>
            <label>
              Ülke
              <input
                value={form.country}
                onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))}
                placeholder="Türkiye"
              />
            </label>
            <label>
              Dil
              <input
                value={form.language}
                onChange={(event) => setForm((current) => ({ ...current, language: event.target.value }))}
                placeholder="Türkçe"
              />
            </label>
            <label>
              Max sayfa
              <input
                type="number"
                min="1"
                max="500"
                value={form.max_pages}
                onChange={(event) => setForm((current) => ({ ...current, max_pages: Number(event.target.value) }))}
              />
            </label>
          </div>

          <label>
            Sektör / iş tanımı
            <textarea
              value={form.business_description}
              onChange={(event) => setForm((current) => ({ ...current, business_description: event.target.value }))}
              placeholder="Örn: B2B ambalaj üreticisi, Shopify e-ticaret, lokal hizmet..."
            />
          </label>

          <div className="form-actions seo-form-actions">
            <button className="small-action-button" type="button" onClick={startAudit} disabled={status === "loading" || status === "crawling"}>
              {status === "loading" || status === "crawling" ? "Analiz sürüyor..." : "Start"}
            </button>
            {audit?.audit_id ? (
              <>
                <button className="small-action-button" type="button" onClick={() => handleDownload("markdown")} disabled={isDownloading !== null}>
                  {isDownloading === "markdown" ? "İndiriliyor..." : "Markdown report indir"}
                </button>
                <button className="small-action-button" type="button" onClick={() => handleDownload("json")} disabled={isDownloading !== null}>
                  {isDownloading === "json" ? "İndiriliyor..." : "JSON report indir"}
                </button>
              </>
            ) : null}
          </div>
        </section>

        <section className="seo-stage-strip" aria-label="SEO audit aşamaları">
          {stageOrder.map((stage, index) => {
            const stageStatus = getStageStatus(audit?.stages, stage.key, status, index);
            return (
              <div className={`seo-stage seo-stage-${stageStatus}`} key={stage.key}>
                <span>{index + 1}</span>
                <strong>{stage.label}</strong>
                <small>{stageStatus}</small>
              </div>
            );
          })}
        </section>

        {errorMessage ? (
          <div className="panel-card seo-error-card">
            <strong>{getStatusLabel(status)}</strong>
            <p>{errorMessage}</p>
          </div>
        ) : null}

        {status === "initial" ? (
          <div className="panel-card">
            <strong>Başlamak için URL gir.</strong>
            <p className="panel-label">Audit tamamlanınca skor, sorunlar, sayfalar ve öneriler burada görünecek.</p>
          </div>
        ) : null}

        {status === "loading" || status === "crawling" ? (
          <div className="panel-card">
            <strong>SEO audit çalışıyor.</strong>
            <p className="panel-label">Backend bağlantı, robots/sitemap, crawl ve rapor aşamalarını yürütüyor.</p>
          </div>
        ) : null}

        {audit ? (
          <>
            <section className="seo-summary-grid">
              <SummaryCard label="Skor" value={formatValue(audit.summary?.score)} />
              <SummaryCard label="Taranan" value={formatValue(audit.crawl_stats?.crawled_urls ?? audit.summary?.pages_crawled ?? audit.pages?.length)} />
              <SummaryCard label="Keşfedilen" value={formatValue(audit.crawl_stats?.discovered_urls ?? audit.summary?.discovered_urls)} />
              <SummaryCard label="Atlanan" value={formatValue(audit.crawl_stats?.skipped_urls ?? audit.summary?.skipped_urls)} />
              <SummaryCard label="Engel/Hata" value={`${formatValue(audit.crawl_stats?.blocked_urls ?? audit.summary?.blocked_urls)} / ${formatValue(audit.crawl_stats?.errored_urls ?? audit.summary?.errored_urls)}`} />
              <SummaryCard label="Platform" value={formatValue(audit.summary?.platform)} />
              <SummaryCard label="P0" value={priorityCounts.P0.toString()} tone="critical" />
              <SummaryCard label="P1" value={priorityCounts.P1.toString()} tone="warning" />
              <SummaryCard label="P2" value={priorityCounts.P2.toString()} />
              <SummaryCard label="P3" value={priorityCounts.P3.toString()} />
            </section>

            <section className="seo-results-card">
              <div className="seo-tabs" role="tablist" aria-label="SEO sonuç sekmeleri">
                {tabs.map((tab) => (
                  <button
                    className={`seo-tab ${activeTab === tab.key ? "active" : ""}`}
                    key={tab.key}
                    type="button"
                    onClick={() => setActiveTab(tab.key)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {activeTab === "overview" ? <OverviewTab audit={audit} issues={visibleIssues} /> : null}
              {activeTab === "technical" ? <IssueList issues={technicalIssues.length > 0 ? technicalIssues : visibleIssues} emptyText="Teknik SEO sorunu dönmedi." /> : null}
              {activeTab === "onPage" ? <IssueList issues={onPageIssues.length > 0 ? onPageIssues : visibleIssues} emptyText="Sayfa içi SEO sorunu dönmedi." /> : null}
              {activeTab === "pages" ? (
                <PagesTab
                  pages={audit.pages ?? []}
                  selectedPage={selectedPage}
                  onSelectPage={(page) => setSelectedPageUrl(page.url ?? "")}
                />
              ) : null}
              {activeTab === "keywords" ? <KeywordTab audit={audit} /> : null}
              {activeTab === "content" ? <ContentTab audit={audit} /> : null}
              {activeTab === "plan" ? <PlanTab audit={audit} /> : null}
            </section>
          </>
        ) : null}
      </div>
    </>
  );
}

function SummaryCard({ label, value, tone }: { label: string; value: string; tone?: "critical" | "warning" }) {
  return (
    <div className={`memory-card seo-summary-card ${tone ? `seo-summary-${tone}` : ""}`}>
      <p className="panel-label">{label}</p>
      <h3>{value}</h3>
    </div>
  );
}

function OverviewTab({ audit, issues }: { audit: SeoAuditResult; issues: SeoAuditIssue[] }) {
  return (
    <div className="seo-tab-panel">
      <div className="project-grid">
        <div className="project-card">
          <p className="panel-label">Durum</p>
          <h3>{audit.status}</h3>
          <p className="project-description">Toplam sorun: {issues.length}</p>
        </div>
        <div className="project-card">
          <p className="panel-label">Özet JSON</p>
          <pre className="payload-preview">{JSON.stringify(audit.summary ?? {}, null, 2)}</pre>
        </div>
      </div>
      <IssueList issues={issues.slice(0, 8)} emptyText="API sorun listesi döndürmedi." />
    </div>
  );
}

function PagesTab({ pages, selectedPage, onSelectPage }: { pages: SeoAuditPage[]; selectedPage: SeoAuditPage | null; onSelectPage: (page: SeoAuditPage) => void }) {
  return (
    <div className="seo-tab-panel seo-pages-layout">
      <div className="seo-table-wrap">
        <table className="seo-pages-table">
          <thead>
            <tr>
              <th>URL</th>
              <th>Status</th>
              <th>Score</th>
              <th>Tür</th>
              <th>Title</th>
              <th>H1</th>
              <th>Index</th>
              <th>Word</th>
              <th>Issues</th>
            </tr>
          </thead>
          <tbody>
            {pages.map((page) => (
              <tr key={page.url ?? JSON.stringify(page)} onClick={() => onSelectPage(page)} className={selectedPage?.url === page.url ? "selected" : ""}>
                <td>{page.url ?? "-"}</td>
                <td>{formatValue(page.status)}</td>
                <td>{formatPageScore(page)}</td>
                <td>{formatValue(page.page_type)}</td>
                <td>{page.title ?? "-"}</td>
                <td>{formatH1(page.h1)}</td>
                <td>{formatValue(page.index ?? page.indexable)}</td>
                <td>{formatValue(page.word_count ?? page.words)}</td>
                <td>{formatPageIssueCount(page.issues)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {pages.length === 0 ? <p className="panel-label">Sayfa verisi dönmedi.</p> : null}
      </div>

      <aside className="seo-detail-panel">
        <p className="eyebrow">Sayfa detayı</p>
        {selectedPage ? (
          <>
            <h3>{selectedPage.title ?? selectedPage.url ?? "Seçili sayfa"}</h3>
            <pre className="payload-preview">{JSON.stringify(selectedPage, null, 2)}</pre>
          </>
        ) : (
          <p className="panel-label">Detay görmek için tablodan bir satır seç.</p>
        )}
      </aside>
    </div>
  );
}

function IssueList({ issues, emptyText }: { issues: SeoAuditIssue[]; emptyText: string }) {
  if (issues.length === 0) {
    return <p className="panel-label seo-empty-text">{emptyText}</p>;
  }

  return (
    <div className="seo-issue-list">
      {issues.map((issue, index) => {
        const copyText = buildIssueCopyText(issue);
        return (
          <article className="project-card seo-issue-card" key={issue.id ?? `${issue.url ?? issue.page_url ?? "issue"}-${index}`}>
            <div className="project-card-header">
              <div>
                <p className="panel-label">{issue.priority ?? "P?"} / {issue.category ?? "Genel"}</p>
                <h3>{issue.name ?? issue.title ?? "SEO sorunu"}</h3>
              </div>
              <button className="small-action-button" type="button" onClick={() => navigator.clipboard.writeText(copyText)}>
                Copy
              </button>
            </div>
            <dl className="seo-issue-details">
              <dt>URL</dt><dd>{issue.url ?? issue.page_url ?? "-"}</dd>
              <dt>Mevcut</dt><dd>{issue.current ?? "-"}</dd>
              <dt>Önerilen</dt><dd>{issue.recommended ?? issue.recommendation ?? "-"}</dd>
              <dt>Açıklama</dt><dd>{issue.explanation ?? "-"}</dd>
              <dt>Nasıl yapılır</dt><dd>{issue.how ?? issue.how_to_fix ?? "-"}</dd>
              <dt>Platform</dt><dd>{issue.platform ?? "Genel"}</dd>
            </dl>
          </article>
        );
      })}
    </div>
  );
}

function KeywordTab({ audit }: { audit: SeoAuditResult }) {
  const recommendations = audit.keyword_recommendations ?? [];
  return (
    <div className="seo-tab-panel seo-list-grid">
      {recommendations.map((item, index) => (
        <div className="project-card" key={`${item.keyword ?? "keyword"}-${index}`}>
          <p className="panel-label">{formatSource(item.source)}</p>
          <h3>{item.keyword ?? "Anahtar kelime önerisi"}</h3>
          <p className="project-description">{item.recommendation ?? item.reason ?? "Öneri metni dönmedi."}</p>
          <p className="seo-muted">Yerleşim: {item.placement ?? "Backend belirtmedi"}</p>
          {item.page_url ? <p className="seo-muted">Sayfa: {item.page_url}</p> : null}
        </div>
      ))}
      {recommendations.length === 0 ? <p className="panel-label">Anahtar kelime önerisi dönmedi. Volume/traffic değeri uydurulmaz.</p> : null}
    </div>
  );
}

function ContentTab({ audit }: { audit: SeoAuditResult }) {
  const recommendations = audit.content_recommendations ?? [];
  return (
    <div className="seo-tab-panel seo-list-grid">
      {recommendations.map((item, index) => (
        <div className="project-card" key={`${item.title ?? "content"}-${index}`}>
          <p className="panel-label">{formatSource(item.source)}</p>
          <h3>{item.title ?? "İçerik önerisi"}</h3>
          <p className="project-description">{item.recommendation ?? item.reason ?? "Öneri metni dönmedi."}</p>
          {item.page_url ? <p className="seo-muted">Sayfa: {item.page_url}</p> : null}
        </div>
      ))}
      {recommendations.length === 0 ? <p className="panel-label">İçerik önerisi dönmedi.</p> : null}
    </div>
  );
}

function PlanTab({ audit }: { audit: SeoAuditResult }) {
  const plan = audit.implementation_plan ?? [];
  return (
    <div className="seo-tab-panel seo-list-grid">
      {plan.map((item, index) => (
        <div className="project-card" key={`${item.title ?? item.task ?? "plan"}-${index}`}>
          <p className="panel-label">{item.priority ?? "Öncelik yok"}</p>
          <h3>{item.title ?? item.task ?? "Uygulama adımı"}</h3>
          <p className="project-description">Etki: {item.impact ?? "-"} / Efor: {item.effort ?? "-"}</p>
          {item.steps && item.steps.length > 0 ? (
            <div className="project-section">
              <p className="panel-label">Adımlar</p>
              <ul>{item.steps.map((step, stepIndex) => <li key={`${step}-${stepIndex}`}>{step}</li>)}</ul>
            </div>
          ) : null}
        </div>
      ))}
      {plan.length === 0 ? <p className="panel-label">Uygulama planı dönmedi.</p> : null}
    </div>
  );
}

function getPriorityCounts(summary: SeoAuditResult["summary"], issues: SeoAuditIssue[]) {
  const counts = { P0: Number(summary?.p0 ?? 0), P1: Number(summary?.p1 ?? 0), P2: Number(summary?.p2 ?? 0), P3: Number(summary?.p3 ?? 0) };
  if (counts.P0 + counts.P1 + counts.P2 + counts.P3 > 0) {
    return counts;
  }

  for (const issue of issues) {
    if (issue.priority === "P0") counts.P0 += 1;
    if (issue.priority === "P1") counts.P1 += 1;
    if (issue.priority === "P2") counts.P2 += 1;
    if (issue.priority === "P3") counts.P3 += 1;
  }
  return counts;
}

function getStageStatus(stages: SeoAuditResult["stages"], key: SeoAuditStageKey, status: SeoAuditStatus, index: number) {
  if (status === "initial" || status === "url_error" || status === "backend_error" || status === "unreachable") {
    return "waiting";
  }

  const fromApi = findStage(stages, key)?.status;
  if (fromApi) {
    return fromApi;
  }

  if (status === "completed") return "done";
  if (status === "partial") return index < 6 ? "done" : "partial";
  if (status === "loading" || status === "crawling") return index <= 2 ? "active" : "waiting";
  return "waiting";
}

function findStage(stages: SeoAuditResult["stages"], key: SeoAuditStageKey): SeoAuditStage | null {
  if (!stages) return null;
  if (Array.isArray(stages)) {
    return stages.find((stage) => stage.key === key || stage.name === key) ?? null;
  }
  const stage = stages[key];
  if (typeof stage === "string") return { key, status: stage };
  return stage ?? null;
}

function resolveUiStatus(result: SeoAuditResult): SeoAuditStatus {
  if (!result.pages?.length && !result.issues?.length) return "empty";
  if (result.status === "completed") return "completed";
  if (result.status === "partial") return "partial";
  return "completed";
}

function isValidHttpUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function clampMaxPages(value: number) {
  if (!Number.isFinite(value)) return 100;
  return Math.max(1, Math.min(500, Math.round(value)));
}

function formatValue(value: unknown) {
  if (value === undefined || value === null || value === "") return "-";
  if (typeof value === "boolean") return value ? "Evet" : "Hayır";
  return String(value);
}

function formatH1(value: SeoAuditPage["h1"]) {
  if (Array.isArray(value)) return value.join(" / ") || "-";
  return formatValue(value);
}

function formatPageIssueCount(value: SeoAuditPage["issues"]) {
  if (Array.isArray(value)) return value.length.toString();
  return formatValue(value);
}

function formatPageScore(page: SeoAuditPage) {
  return typeof page.page_score === "number" ? page.page_score.toString() : "Hesaplanmadı";
}

function formatSource(source: unknown) {
  if (source === "ai") return "AI önerisi";
  if (source === "heuristic") return "Heuristic öneri";
  return "Backend önerisi";
}

function normalizeCategory(issue: SeoAuditIssue) {
  return String(issue.category ?? issue.name ?? issue.title ?? "").toLocaleLowerCase("en-US");
}

function buildIssueCopyText(issue: SeoAuditIssue) {
  return [
    `Öncelik: ${issue.priority ?? "-"}`,
    `Sorun: ${issue.name ?? issue.title ?? "-"}`,
    `URL: ${issue.url ?? issue.page_url ?? "-"}`,
    `Mevcut: ${issue.current ?? "-"}`,
    `Önerilen: ${issue.recommended ?? issue.recommendation ?? "-"}`,
    `Açıklama: ${issue.explanation ?? "-"}`,
    `Nasıl: ${issue.how ?? issue.how_to_fix ?? "-"}`,
    `Platform: ${issue.platform ?? "Genel"}`,
  ].join("\n");
}

function getStatusLabel(status: SeoAuditStatus) {
  if (status === "initial") return "Hazır";
  if (status === "loading") return "Başlatılıyor";
  if (status === "crawling") return "Crawl sürüyor";
  if (status === "completed") return "Tamamlandı";
  if (status === "url_error") return "URL hatası";
  if (status === "unreachable") return "Ulaşılamıyor";
  if (status === "partial") return "Kısmi sonuç";
  if (status === "backend_error") return "Backend hatası";
  if (status === "empty") return "Boş sonuç";
  return status;
}
