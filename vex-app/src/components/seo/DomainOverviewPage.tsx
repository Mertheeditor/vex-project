import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { DataTable, type Column, Pagination, ProgressBar, SeoSummaryCard } from "./SeoUIComponents";
import { SeoProjectSelector } from "./SeoProjectSelector";
import { SeoDomainService } from "../../services/seoDomainService";
import type {
  Competitor,
  CompetitorsResponse,
  DataSourceStatus,
  DataSourceType,
  DataSourcesResponse,
  DomainOverviewResponse,
  KeywordIntent,
  OrganicKeyword,
  OrganicKeywordFilters,
  OrganicKeywordsResponse,
  OrganicPage,
  OrganicPageFilters,
  OrganicPagesResponse,
  PositionChange,
  PositionChangeDirection,
  PositionChangesFilters,
  PositionChangesResponse,
} from "../../types/seoDomain";

type TabType =
  | "overview"
  | "organic-keywords"
  | "organic-pages"
  | "competitors"
  | "position-changes"
  | "data-sources";

type SortState = { column: string; direction: "asc" | "desc" };

const TABS: { id: TabType; label: string; icon: string }[] = [
  { id: "overview", label: "Genel Bakış", icon: "📊" },
  { id: "organic-keywords", label: "Organik Anahtar Kelimeler", icon: "🔑" },
  { id: "organic-pages", label: "En İyi Sayfalar", icon: "📄" },
  { id: "competitors", label: "Rakipler", icon: "🏆" },
  { id: "position-changes", label: "Pozisyon Değişimleri", icon: "📈" },
  { id: "data-sources", label: "Veri Kaynakları", icon: "🔌" },
];

const INTENTS: KeywordIntent[] = [
  "informational",
  "navigational",
  "commercial",
  "transactional",
];

const CHANGE_DIRECTIONS: PositionChangeDirection[] = ["up", "down", "new", "lost", "unchanged"];

interface DomainOverviewPageProps {
  projectId?: string;
}

export function DomainOverviewPage({ projectId }: DomainOverviewPageProps) {
  const [selectedProjectId, setSelectedProjectId] = useState(projectId ?? "");
  const [activeTab, setActiveTab] = useState<TabType>("overview");
  const [country, setCountry] = useState("US");
  const [language, setLanguage] = useState("en");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<DomainOverviewResponse | null>(null);
  const [keywords, setKeywords] = useState<OrganicKeywordsResponse | null>(null);
  const [pages, setPages] = useState<OrganicPagesResponse | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorsResponse | null>(null);
  const [positionChanges, setPositionChanges] = useState<PositionChangesResponse | null>(null);
  const [dataSources, setDataSources] = useState<DataSourcesResponse | null>(null);

  const [keywordFilters, setKeywordFilters] = useState<OrganicKeywordFilters>({});
  const [keywordPage, setKeywordPage] = useState(1);
  const [keywordPageSize, setKeywordPageSize] = useState(50);
  const [keywordSort, setKeywordSort] = useState<SortState>({ column: "traffic", direction: "desc" });

  const [pageFilters, setPageFilters] = useState<OrganicPageFilters>({});
  const [pagePage, setPagePage] = useState(1);
  const [pagePageSize, setPagePageSize] = useState(50);
  const [pageSort, setPageSort] = useState<SortState>({ column: "organic_traffic", direction: "desc" });

  const [competitorPage, setCompetitorPage] = useState(1);
  const [competitorPageSize, setCompetitorPageSize] = useState(20);
  const [competitorSort, setCompetitorSort] = useState<SortState>({ column: "competition_level", direction: "desc" });

  const [positionChangeFilters, setPositionChangeFilters] = useState<PositionChangesFilters>({});
  const [positionChangePage, setPositionChangePage] = useState(1);
  const [positionChangePageSize, setPositionChangePageSize] = useState(50);
  const [positionChangeSort, setPositionChangeSort] = useState<SortState>({ column: "change", direction: "desc" });

  const selectedSourceSummary = dataSources ?? overview?.data_sources ?? null;

  const loadData = useCallback(async () => {
    if (!selectedProjectId) return;

    setLoading(true);
    setError(null);

    try {
      if (activeTab === "overview") {
        const data = await SeoDomainService.getDomainOverview(selectedProjectId, {
          country,
          language,
          include_history: true,
          history_days: 30,
          use_cache: true,
        });
        setOverview(data);
        setDataSources(data.data_sources);
      } else if (activeTab === "organic-keywords") {
        setKeywords(await SeoDomainService.getOrganicKeywords(selectedProjectId, {
          country,
          language,
          page: keywordPage,
          page_size: keywordPageSize,
          search: keywordFilters.keyword,
          position_from: keywordFilters.position_min,
          position_to: keywordFilters.position_max,
          volume_from: keywordFilters.volume_min,
          volume_to: keywordFilters.volume_max,
          difficulty_from: keywordFilters.difficulty_min,
          difficulty_to: keywordFilters.difficulty_max,
          intent: keywordFilters.intent,
          sort_by: keywordSort.column,
          sort_order: keywordSort.direction,
          use_cache: true,
        }));
      } else if (activeTab === "organic-pages") {
        setPages(await SeoDomainService.getOrganicPages(selectedProjectId, {
          country,
          language,
          page: pagePage,
          page_size: pagePageSize,
          search: pageFilters.url_contains,
          keywords_from: pageFilters.keywords_min,
          keywords_to: pageFilters.keywords_max,
          traffic_from: pageFilters.traffic_min,
          traffic_to: pageFilters.traffic_max,
          page_type: pageFilters.page_type,
          sort_by: pageSort.column,
          sort_order: pageSort.direction,
          use_cache: true,
        }));
      } else if (activeTab === "competitors") {
        setCompetitors(await SeoDomainService.getCompetitors(selectedProjectId, {
          country,
          language,
          page: competitorPage,
          page_size: competitorPageSize,
          sort_by: competitorSort.column,
          sort_order: competitorSort.direction,
          use_cache: true,
        }));
      } else if (activeTab === "position-changes") {
        setPositionChanges(await SeoDomainService.getPositionChanges(selectedProjectId, {
          country,
          language,
          page: positionChangePage,
          page_size: positionChangePageSize,
          search: positionChangeFilters.keyword_contains,
          direction: positionChangeFilters.direction,
          change_from: positionChangeFilters.change_min,
          volume_from: positionChangeFilters.volume_min,
          sort_by: positionChangeSort.column,
          sort_order: positionChangeSort.direction,
          use_cache: true,
        }));
      } else {
        setDataSources(await SeoDomainService.getDataSources(selectedProjectId));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Veri yüklenirken hata oluştu");
    } finally {
      setLoading(false);
    }
  }, [
    activeTab,
    competitorPage,
    competitorPageSize,
    competitorSort,
    country,
    keywordFilters,
    keywordPage,
    keywordPageSize,
    keywordSort,
    language,
    pageFilters,
    pagePage,
    pagePageSize,
    pageSort,
    positionChangeFilters,
    positionChangePage,
    positionChangePageSize,
    positionChangeSort,
    selectedProjectId,
  ]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const updateSort = (current: SortState, setter: (sort: SortState) => void, column: string) => {
    setter(current.column === column
      ? { column, direction: current.direction === "asc" ? "desc" : "asc" }
      : { column, direction: "desc" });
  };

  const handleProjectChange = (newProjectId: string) => {
    setSelectedProjectId(newProjectId);
    setOverview(null);
    setKeywords(null);
    setPages(null);
    setCompetitors(null);
    setPositionChanges(null);
    setDataSources(null);
    setKeywordPage(1);
    setPagePage(1);
    setCompetitorPage(1);
    setPositionChangePage(1);
  };

  return (
    <div className="domain-overview-page">
      <header className="page-header">
        <div>
          <h1 className="page-title">Domain Overview</h1>
          <p className="page-subtitle">Organik araştırma ve teknik SEO durumunu tek çalışma alanında izle.</p>
        </div>
        <button className="refresh-btn" onClick={() => void loadData()} disabled={loading || !selectedProjectId}>
          {loading ? "Yükleniyor..." : "Yenile"}
        </button>
      </header>

      <section className="tab-panel domain-context-panel">
        <SeoProjectSelector
          value={selectedProjectId}
          onChange={handleProjectChange}
          includeEmpty
          emptyLabel="SEO projesi seç"
        />
        <div className="domain-selector">
          <label htmlFor="domain-country">Ülke</label>
          <select id="domain-country" value={country} onChange={(event) => setCountry(event.target.value)} className="country-select">
            <option value="US">US</option>
            <option value="TR">TR</option>
            <option value="DE">DE</option>
            <option value="GB">GB</option>
          </select>
          <label htmlFor="domain-language">Dil</label>
          <select id="domain-language" value={language} onChange={(event) => setLanguage(event.target.value)} className="country-select">
            <option value="en">en</option>
            <option value="tr">tr</option>
            <option value="de">de</option>
          </select>
          <span className="seo-muted">Cihaz: desktop · Tarih aralığı: son 30 gün</span>
        </div>
        <SourceBadgeRow sources={selectedSourceSummary} />
      </section>

      {error && <div className="error-banner">{error}</div>}
      {!selectedProjectId && <div className="tab-panel empty">Domain Overview için bir SEO projesi seç.</div>}

      {selectedProjectId && (
        <>
          <div className="tab-navigation">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
              >
                <span className="tab-icon">{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {activeTab === "overview" && <OverviewTab overview={overview} loading={loading} />}
          {activeTab === "organic-keywords" && (
            <OrganicKeywordsTab
              data={keywords}
              loading={loading}
              filters={keywordFilters}
              onFiltersChange={(filters) => { setKeywordFilters(filters); setKeywordPage(1); }}
              page={keywordPage}
              pageSize={keywordPageSize}
              sort={keywordSort}
              onPageChange={setKeywordPage}
              onPageSizeChange={(size) => { setKeywordPageSize(size); setKeywordPage(1); }}
              onSort={(column) => updateSort(keywordSort, setKeywordSort, column)}
            />
          )}
          {activeTab === "organic-pages" && (
            <OrganicPagesTab
              data={pages}
              loading={loading}
              filters={pageFilters}
              onFiltersChange={(filters) => { setPageFilters(filters); setPagePage(1); }}
              page={pagePage}
              pageSize={pagePageSize}
              sort={pageSort}
              onPageChange={setPagePage}
              onPageSizeChange={(size) => { setPagePageSize(size); setPagePage(1); }}
              onSort={(column) => updateSort(pageSort, setPageSort, column)}
            />
          )}
          {activeTab === "competitors" && (
            <CompetitorsTab
              data={competitors}
              loading={loading}
              page={competitorPage}
              pageSize={competitorPageSize}
              sort={competitorSort}
              onPageChange={setCompetitorPage}
              onPageSizeChange={(size) => { setCompetitorPageSize(size); setCompetitorPage(1); }}
              onSort={(column) => updateSort(competitorSort, setCompetitorSort, column)}
            />
          )}
          {activeTab === "position-changes" && (
            <PositionChangesTab
              data={positionChanges}
              loading={loading}
              filters={positionChangeFilters}
              onFiltersChange={(filters) => { setPositionChangeFilters(filters); setPositionChangePage(1); }}
              page={positionChangePage}
              pageSize={positionChangePageSize}
              sort={positionChangeSort}
              onPageChange={setPositionChangePage}
              onPageSizeChange={(size) => { setPositionChangePageSize(size); setPositionChangePage(1); }}
              onSort={(column) => updateSort(positionChangeSort, setPositionChangeSort, column)}
            />
          )}
          {activeTab === "data-sources" && <DataSourcesTab data={dataSources} loading={loading} />}
        </>
      )}
    </div>
  );
}

function OverviewTab({ overview, loading }: { overview: DomainOverviewResponse | null; loading: boolean }) {
  if (loading && !overview) return <div className="tab-panel loading">Genel bakış yükleniyor...</div>;
  if (!overview) return <div className="tab-panel empty">Bu proje için Domain Overview verisi mevcut değil.</div>;

  const { metrics, history } = overview;
  const organicAvailable = hasConnectedOrganicSource(overview.data_sources);
  const historyAvailable = history.length > 0 && organicAvailable;

  return (
    <div className="tab-panel overview-tab">
      <section className="metrics-grid">
        <MetricCard title="Domain" value={metrics.domain} source={metrics.data_source} />
        <MetricCard title="Organik görünürlük" value={null} source="estimated" note="Veri kaynağı bağlı değil" />
        <MetricCard title="Organik anahtar kelime" value={organicAvailable ? metrics.organic_keywords : null} source={metrics.data_source} note="Veri kaynağı bağlı değil" />
        <MetricCard title="Tahmini organik trafik" value={organicAvailable ? metrics.organic_traffic : null} source={metrics.data_source} estimated note="Veri kaynağı bağlı değil" />
        <MetricCard title="İlk 3" value={null} source="estimated" note="Veri mevcut değil" />
        <MetricCard title="İlk 10" value={null} source="estimated" note="Veri mevcut değil" />
        <MetricCard title="İlk 20" value={null} source="estimated" note="Veri mevcut değil" />
        <MetricCard title="İlk 100" value={null} source="estimated" note="Veri mevcut değil" />
        <MetricCard title="Ortalama pozisyon" value={null} source="estimated" note="Veri mevcut değil" />
        <MetricCard title="Search Console tıklamaları" value={null} source="google_search_console" note="Veri kaynağı bağlı değil" />
        <MetricCard title="Search Console gösterimleri" value={null} source="google_search_console" note="Veri kaynağı bağlı değil" />
        <MetricCard title="Search Console CTR" value={null} source="google_search_console" note="Veri kaynağı bağlı değil" />
        <MetricCard title="Search Console ort. pozisyon" value={null} source="google_search_console" note="Veri kaynağı bağlı değil" />
        <MetricCard title="Site Health" value={null} source="custom" note="Bu proje için henüz Site Audit çalıştırılmadı." />
        <MetricCard title="Indexable sayfa" value={null} source="custom" note="Bu proje için henüz Site Audit çalıştırılmadı." />
        <MetricCard title="Son güncellenme" value={formatDateTime(metrics.last_updated)} source={metrics.data_source} />
      </section>

      <section className="charts-section">
        <div className="chart-card">
          <h3>Pozisyon dağılımı</h3>
          <EmptyChart message={organicAvailable ? "Pozisyon dağılımı için gerçek SERP snapshot verisi mevcut değil." : "Anahtar kelime veri sağlayıcısı bağlı değil."} />
        </div>
        <div className="chart-card">
          <h3>Trend</h3>
          {historyAvailable ? <TrendBars history={history} /> : <EmptyChart message="Gerçek zaman serisi verisi mevcut değil." />}
        </div>
      </section>
    </div>
  );
}

function OrganicKeywordsTab(props: ListTabProps<OrganicKeywordsResponse, OrganicKeywordFilters> & { sort: SortState; onSort: (column: string) => void }) {
  const { data, loading, filters, onFiltersChange, page, pageSize, onPageChange, onPageSizeChange, sort, onSort } = props;
  const columns: Column<OrganicKeyword>[] = [
    { key: "keyword", header: "Anahtar kelime", sortable: true },
    { key: "position", header: "Pozisyon", sortable: true, render: (row) => <PositionBadge position={row.position} /> },
    { key: "previous_position", header: "Önceki", render: (row) => row.previous_position ?? "–" },
    { key: "position_change", header: "Değişim", sortable: true, render: (row) => <ChangeValue value={row.position_change} /> },
    { key: "search_volume", header: "Arama hacmi", sortable: true, render: (row) => formatNumber(row.search_volume) },
    { key: "keyword_difficulty", header: "KD", sortable: true, render: (row) => row.keyword_difficulty },
    { key: "intent", header: "Intent", render: (row) => <span className={`intent-badge intent-${row.intent}`}>{row.intent}</span> },
    { key: "url", header: "Landing page", render: (row) => <UrlCell url={row.url} /> },
    { key: "traffic", header: "Tahmini trafik", sortable: true, render: (row) => formatNumber(row.traffic) },
    { key: "cpc", header: "CPC", sortable: true, render: (row) => formatCurrency(row.cpc) },
    { key: "serps_features", header: "SERP özellikleri", render: (row) => row.serps_features.length ? row.serps_features.join(", ") : "–" },
    { key: "data_source", header: "Kaynak", render: (row) => <SourceBadge source={row.data_source} /> },
    { key: "last_updated", header: "Son güncelleme", render: (row) => formatDateTime(row.last_updated) },
  ];

  return (
    <TablePanel
      loading={loading}
      data={data}
      emptyMessage="Anahtar kelime veri sağlayıcısı bağlı değil."
      filters={<>
        <input className="search-input" placeholder="Anahtar kelime ara" value={filters.keyword ?? ""} onChange={(e) => onFiltersChange({ ...filters, keyword: e.target.value || undefined })} />
        <select className="filter-select" value={filters.position_max ?? ""} onChange={(e) => onFiltersChange({ ...filters, position_min: e.target.value ? 1 : undefined, position_max: e.target.value ? Number(e.target.value) : undefined })}>
          <option value="">Tüm pozisyonlar</option>
          <option value="3">Top 3</option>
          <option value="10">Top 10</option>
          <option value="20">Top 20</option>
          <option value="100">Top 100</option>
        </select>
        <select className="filter-select" value={filters.intent ?? ""} onChange={(e) => onFiltersChange({ ...filters, intent: asIntent(e.target.value) })}>
          <option value="">Tüm intentler</option>
          {INTENTS.map((intent) => <option key={intent} value={intent}>{intent}</option>)}
        </select>
      </>}
      table={<DataTable data={data?.items ?? []} columns={columns} keyExtractor={(row) => `${row.keyword}-${row.url}`} sortColumn={sort.column} sortDirection={sort.direction} onSort={onSort} emptyMessage="Anahtar kelime veri sağlayıcısı bağlı değil." />}
      page={page}
      pageSize={pageSize}
      totalItems={data?.total ?? 0}
      totalPages={data?.total_pages ?? 0}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
    />
  );
}

function OrganicPagesTab(props: ListTabProps<OrganicPagesResponse, OrganicPageFilters> & { sort: SortState; onSort: (column: string) => void }) {
  const { data, loading, filters, onFiltersChange, page, pageSize, onPageChange, onPageSizeChange, sort, onSort } = props;
  const columns: Column<OrganicPage>[] = [
    { key: "url", header: "URL", render: (row) => <UrlCell url={row.url} /> },
    { key: "page_type", header: "Sayfa türü", sortable: true },
    { key: "organic_keywords", header: "Organik keyword", sortable: true, render: (row) => formatNumber(row.organic_keywords) },
    { key: "organic_traffic", header: "Tahmini trafik", sortable: true, render: (row) => formatNumber(row.organic_traffic) },
    { key: "top_keyword", header: "En iyi keyword", render: (row) => row.top_keyword || "–" },
    { key: "top_keyword_position", header: "Ort. pozisyon", sortable: true, render: (row) => <PositionBadge position={row.top_keyword_position} /> },
    { key: "backlinks", header: "Backlink", sortable: true, render: (row) => formatNumber(row.backlinks) },
    { key: "referring_domains", header: "Ref. domain", sortable: true, render: (row) => formatNumber(row.referring_domains) },
    { key: "data_source", header: "Kaynak", render: (row) => <SourceBadge source={row.data_source} /> },
    { key: "last_updated", header: "Son audit/veri", render: (row) => formatDateTime(row.last_updated) },
  ];

  return (
    <TablePanel
      loading={loading}
      data={data}
      emptyMessage="Organik sayfa sağlayıcısı bağlı değil. Site Audit çalıştırıldıysa teknik sayfalar burada birleşir."
      filters={<>
        <input className="search-input" placeholder="URL ara" value={filters.url_contains ?? ""} onChange={(e) => onFiltersChange({ ...filters, url_contains: e.target.value || undefined })} />
        <select className="filter-select" value={filters.page_type ?? ""} onChange={(e) => onFiltersChange({ ...filters, page_type: e.target.value || undefined })}>
          <option value="">Tüm sayfa türleri</option>
          <option value="homepage">Ana sayfa</option>
          <option value="blog_article">Blog yazısı</option>
          <option value="product">Ürün</option>
          <option value="category">Kategori</option>
        </select>
      </>}
      table={<DataTable data={data?.items ?? []} columns={columns} keyExtractor={(row) => row.url} sortColumn={sort.column} sortDirection={sort.direction} onSort={onSort} emptyMessage="Organik sayfa sağlayıcısı bağlı değil." />}
      page={page}
      pageSize={pageSize}
      totalItems={data?.total ?? 0}
      totalPages={data?.total_pages ?? 0}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
    />
  );
}

function CompetitorsTab(props: PagingProps & { data: CompetitorsResponse | null; loading: boolean; sort: SortState; onSort: (column: string) => void }) {
  const { data, loading, page, pageSize, onPageChange, onPageSizeChange, sort, onSort } = props;
  const columns: Column<Competitor>[] = [
    { key: "domain", header: "Domain", sortable: true },
    { key: "common_keywords", header: "Ortak keyword", sortable: true, render: (row) => formatNumber(row.common_keywords) },
    { key: "organic_keywords", header: "Toplam keyword", sortable: true, render: (row) => formatNumber(row.organic_keywords) },
    { key: "competition_level", header: "Rekabet", sortable: true, render: (row) => <ProgressBar progress={Math.round(row.competition_level * 100)} variant="default" /> },
    { key: "organic_traffic", header: "Tahmini trafik", sortable: true, render: (row) => formatNumber(row.organic_traffic) },
    { key: "last_updated", header: "Son güncelleme", render: (row) => formatDateTime(row.last_updated) },
    { key: "data_source", header: "Kaynak", render: (row) => <SourceBadge source={row.data_source} /> },
  ];

  return (
    <TablePanel
      loading={loading}
      data={data}
      emptyMessage="Organik rakip verisi için SERP veya domain araştırma sağlayıcısı bağlanmalıdır."
      filters={<span className="seo-muted">Site Audit internal/external link verisi rakip verisi olarak kullanılmaz.</span>}
      table={<DataTable data={data?.items ?? []} columns={columns} keyExtractor={(row) => row.domain} sortColumn={sort.column} sortDirection={sort.direction} onSort={onSort} emptyMessage="Organik rakip verisi için SERP veya domain araştırma sağlayıcısı bağlanmalıdır." />}
      page={page}
      pageSize={pageSize}
      totalItems={data?.total ?? 0}
      totalPages={data?.total_pages ?? 0}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
    />
  );
}

function PositionChangesTab(props: ListTabProps<PositionChangesResponse, PositionChangesFilters> & { sort: SortState; onSort: (column: string) => void }) {
  const { data, loading, filters, onFiltersChange, page, pageSize, onPageChange, onPageSizeChange, sort, onSort } = props;
  const columns: Column<PositionChange>[] = [
    { key: "keyword", header: "Keyword", sortable: true },
    { key: "current_position", header: "Güncel", sortable: true, render: (row) => <PositionBadge position={row.current_position} /> },
    { key: "previous_position", header: "Önceki", render: (row) => row.previous_position ?? "–" },
    { key: "change", header: "Değişim", sortable: true, render: (row) => <ChangeValue value={row.change} /> },
    { key: "url", header: "Landing page", render: (row) => <UrlCell url={row.url} /> },
    { key: "date_detected", header: "Tarih", render: (row) => formatDateTime(row.date_detected) },
    { key: "data_source", header: "Kaynak", render: (row) => <SourceBadge source={row.data_source} /> },
  ];

  return (
    <TablePanel
      loading={loading}
      data={data}
      emptyMessage="Karşılaştırma için en az iki veri noktası gerekir."
      filters={<>
        <input className="search-input" placeholder="Keyword ara" value={filters.keyword_contains ?? ""} onChange={(e) => onFiltersChange({ ...filters, keyword_contains: e.target.value || undefined })} />
        <select className="filter-select" value={filters.direction ?? ""} onChange={(e) => onFiltersChange({ ...filters, direction: asDirection(e.target.value) })}>
          <option value="">Tüm kategoriler</option>
          {CHANGE_DIRECTIONS.map((direction) => <option key={direction} value={direction}>{direction}</option>)}
        </select>
        <select className="filter-select" value={filters.change_min ?? ""} onChange={(e) => onFiltersChange({ ...filters, change_min: e.target.value ? Number(e.target.value) : undefined })}>
          <option value="">Min değişim</option>
          <option value="1">1+</option>
          <option value="3">3+</option>
          <option value="10">10+</option>
        </select>
      </>}
      table={<DataTable data={data?.items ?? []} columns={columns} keyExtractor={(row) => `${row.keyword}-${row.url}-${row.date_detected}`} sortColumn={sort.column} sortDirection={sort.direction} onSort={onSort} emptyMessage="Karşılaştırma için en az iki veri noktası gerekir." />}
      page={page}
      pageSize={pageSize}
      totalItems={data?.total ?? 0}
      totalPages={data?.total_pages ?? 0}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
    />
  );
}

function DataSourcesTab({ data, loading }: { data: DataSourcesResponse | null; loading: boolean }) {
  const sources = useMemo(() => data?.sources ?? [], [data]);
  if (loading && !data) return <div className="tab-panel loading">Veri kaynakları yükleniyor...</div>;

  return (
    <div className="tab-panel data-sources-tab">
      <div className="data-sources-grid">
        {sources.map((source) => <DataSourceCard key={source.source} source={source} />)}
      </div>
      {!sources.length && <div className="seo-empty-text">Veri kaynağı durumu mevcut değil.</div>}
      {data?.primary_source && <div className="primary-source-notice">Birincil veri kaynağı: <strong>{data.primary_source}</strong></div>}
    </div>
  );
}

interface PagingProps {
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

interface ListTabProps<T, F> extends PagingProps {
  data: T | null;
  loading: boolean;
  filters: F;
  onFiltersChange: (filters: F) => void;
}

function TablePanel<T extends { total: number; total_pages: number }>({
  loading,
  data,
  emptyMessage,
  filters,
  table,
  page,
  pageSize,
  totalItems,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: {
  loading: boolean;
  data: T | null;
  emptyMessage: string;
  filters: ReactNode;
  table: ReactNode;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}) {
  if (loading && !data) return <div className="tab-panel loading">Veriler yükleniyor...</div>;
  return (
    <div className="tab-panel">
      <div className="tab-toolbar">
        <div className="toolbar-left">{filters}</div>
        <div className="toolbar-right"><span className="results-count">{totalItems.toLocaleString("tr-TR")} sonuç</span></div>
      </div>
      {table}
      {!loading && data && data.total === 0 && <div className="seo-empty-text">{emptyMessage}</div>}
      {data && totalPages > 1 && (
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          pageSize={pageSize}
          totalItems={totalItems}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}

function MetricCard({ title, value, source, estimated = false, note }: { title: string; value: string | number | null; source: DataSourceType; estimated?: boolean; note?: string }) {
  const displayValue = value === null ? (note ?? "Veri mevcut değil") : typeof value === "number" ? formatNumber(value) : value;
  return (
    <SeoSummaryCard
      title={estimated ? `${title} (Tahmini)` : title}
      value={displayValue}
      subtitle={`Kaynak: ${source}${value === null ? " · Kullanılamıyor" : ""}`}
      className={value === null ? "seo-summary-warning" : ""}
    />
  );
}

function PositionBadge({ position }: { position: number }) {
  const level = position <= 3 ? "top3" : position <= 10 ? "top10" : position <= 20 ? "top20" : "other";
  return <span className={`position-badge pos-${level}`}>{position}</span>;
}

function ChangeValue({ value }: { value: number }) {
  return <span className={`position-change ${value > 0 ? "improved" : value < 0 ? "declined" : "stable"}`}>{value > 0 ? "+" : ""}{value}</span>;
}

function UrlCell({ url }: { url: string }) {
  const label = url.length > 72 ? `${url.slice(0, 72)}...` : url;
  return <a href={url} target="_blank" rel="noopener noreferrer" className="url-link" title={url}>{label}</a>;
}

function SourceBadge({ source }: { source: DataSourceType }) {
  return <span className={`provider-status-badge status-${source}`}>{source}</span>;
}

function SourceBadgeRow({ sources }: { sources: DataSourcesResponse | null }) {
  if (!sources) return <p className="seo-muted">Veri kaynağı durumları yüklenmedi.</p>;
  return (
    <div className="voice-summary-badges">
      {sources.sources.map((source) => (
        <span key={source.source}>{source.source}: {source.status}</span>
      ))}
    </div>
  );
}

function DataSourceCard({ source }: { source: DataSourceStatus }) {
  return (
    <div className={`data-source-card ${source.configured ? "configured" : "not-configured"}`}>
      <div className="source-header">
        <span className={`source-icon source-${source.source}`}>{getSourceIcon(source.source)}</span>
        <div className="source-info">
          <h3>{getSourceLabel(source.source)}</h3>
          <span className={`source-status status-${source.status}`}>{source.status}</span>
        </div>
      </div>
      <div className="source-details">
        <DetailRow label="Configured" value={source.configured ? "Evet" : "Hayır"} />
        <DetailRow label="Available" value={source.status === "active" ? "Evet" : "Hayır"} />
        <DetailRow label="Son başarılı çekme" value={source.last_sync ? formatDateTime(source.last_sync) : "Yok"} />
        <DetailRow label="Son hata" value={source.error_message ?? "Yok"} />
        <div className="detail-row">
          <span className="detail-label">Capability:</span>
          <span className="detail-value">{source.supported_features.length ? source.supported_features.join(", ") : "Yok"}</span>
        </div>
        <DetailRow label="Bu ekrandaki metrikler" value={metricsForSource(source.source)} />
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{label}:</span>
      <span className="detail-value">{value}</span>
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return <div className="chart-placeholder"><p>{message}</p></div>;
}

function TrendBars({ history }: { history: DomainOverviewResponse["history"] }) {
  const maxTraffic = Math.max(...history.map((point) => point.organic_traffic), 1);
  return (
    <div className="mini-chart" aria-label="Gerçek trend serisi">
      {history.slice(-30).map((point) => (
        <div
          key={point.date}
          className="chart-bar"
          style={{ height: `${Math.max(10, (point.organic_traffic / maxTraffic) * 100)}%` }}
          title={`${point.date}: ${formatNumber(point.organic_traffic)} trafik`}
        />
      ))}
    </div>
  );
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Veri mevcut değil";
  return value.toLocaleString("tr-TR");
}

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Veri mevcut değil";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(value);
}

function formatDateTime(value: string): string {
  try {
    return new Date(value).toLocaleString("tr-TR");
  } catch {
    return value;
  }
}

function asIntent(value: string): KeywordIntent | undefined {
  return INTENTS.includes(value as KeywordIntent) ? value as KeywordIntent : undefined;
}

function asDirection(value: string): PositionChangeDirection | undefined {
  return CHANGE_DIRECTIONS.includes(value as PositionChangeDirection) ? value as PositionChangeDirection : undefined;
}

function hasConnectedOrganicSource(sources: DataSourcesResponse): boolean {
  return sources.sources.some((source) => source.configured && source.status === "active" && source.source !== "estimated" && source.source !== "custom");
}

function getSourceIcon(source: DataSourceType): string {
  const icons: Record<DataSourceType, string> = {
    semrush: "🔍",
    ahrefs: "⚡",
    google_search_console: "📊",
    google_analytics: "📈",
    data_for_seo: "🔧",
    custom: "⚙️",
    estimated: "📉",
  };
  return icons[source];
}

function getSourceLabel(source: DataSourceType): string {
  const labels: Record<DataSourceType, string> = {
    semrush: "Keyword provider",
    ahrefs: "SERP provider",
    google_search_console: "Google Search Console",
    google_analytics: "Google Analytics",
    data_for_seo: "PageSpeed / CrUX",
    custom: "Site Audit crawler",
    estimated: "Tahmini veri",
  };
  return labels[source];
}

function metricsForSource(source: DataSourceType): string {
  const metrics: Record<DataSourceType, string> = {
    semrush: "Organik keyword, trafik, pozisyon",
    ahrefs: "SERP/rakip ve backlink metrikleri",
    google_search_console: "Tıklama, gösterim, CTR, ortalama pozisyon",
    google_analytics: "Organik oturum performansı",
    data_for_seo: "PageSpeed ve CrUX hazırlığı",
    custom: "Site Health, indexable sayfalar, teknik sorunlar",
    estimated: "Yalnız gerçek sağlayıcı varsa tahmin etiketi",
  };
  return metrics[source];
}

export default DomainOverviewPage;
