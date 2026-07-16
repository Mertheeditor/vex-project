# VEX-SEO-002: Site Audit Workspace Implementation Plan

## Context

The Vex application currently has an SEO audit system (`SeoExpertPage`) that runs one-off audits without project context. The task is to implement a **SEMrush-style Site Audit workspace** (`SiteAuditPage`) with:

- **Project-based audits** — audits linked to `SeoProject` via `project_id`
- **6 tabs**: Genel Bakış (Overview), Sorunlar (Issues), Taranan Sayfalar (Crawled Pages), İstatistikler (Statistics), Audit Geçmişi (Audit History), Karşılaştırma (Comparison)
- **Pagination, filtering, CSV export** for issue and page tables
- **Progress tracking** during crawl
- **Audit comparison** between runs
- **Integration** with existing `SeoProjectSelector` component

All 49 existing regression tests (mspovleceni.cz fixtures) must continue to pass.

---

## Critical Files to Modify

### Backend (`vex-backend/`)

| File | Purpose |
|------|---------|
| `app/routes/seo.py` | New endpoints: `/audits` (history with pagination), `/audits/{id}/compare`, `/audits/{id}/export/csv`, progress endpoint |
| `app/routes/seo_projects.py` | Add `project_id` to audit creation, history endpoint for project |
| `app/services/seo_service.py` | `create_audit` accepts `project_id`, new `compare_audits`, `export_csv`, progress tracking |
| `app/storage/seo_store.py` | Query methods for pagination/filtering audits |
| `app/schemas/seo_core.py` | Add `AuditComparison`, `PaginationParams`, `ExportFormat` models |
| `app/tests/test_seo.py` | Add tests for new endpoints (keep 49 existing) |

### Frontend (`vex-app/`)

| File | Purpose |
|------|---------|
| `src/components/seo/SiteAuditPage.tsx` | **New** — Main 6-tab workspace component |
| `src/components/seo/SiteAuditTabs/` | **New** — Tab components: `OverviewTab`, `IssuesTab`, `PagesTab`, `StatisticsTab`, `HistoryTab`, `ComparisonTab` |
| `src/services/seo.ts` | Add `fetchAuditHistory`, `compareAudits`, `exportAuditCsv`, progress polling |
| `src/services/seoProjectService.ts` | Add `createProjectAudit`, `listProjectAudits` enhancements |
| `src/types/seo.ts` | Add `AuditComparison`, `PaginationParams`, `AuditHistoryResponse` |
| `src/App.tsx` | Add route for `SiteAuditPage` |
| `src/components/seo/SeoUIComponents.tsx` | Reuse existing components; add `ProgressBar`, `DataTable`, `FilterBar` |

---

## Implementation Approach

### Phase 1: Backend API Extensions

1. **Add `project_id` to audit creation**
   - `SeoAuditService.create_audit(config, project_id?)` — store `project_id` in audit record
   - Update `SeoProjectService.add_audit_to_history` to be called automatically when `project_id` provided

2. **Audit History Endpoint (with pagination/filtering)**
   - `GET /seo/audits?project_id=&page=&page_size=&status=&date_from=&date_to=&sort=`
   - Returns paginated list: `{ items: Audit[], total: number, page: number, page_size: number }`
   - Also `GET /seo/projects/{project_id}/audits` with same params

3. **Audit Comparison Endpoint**
   - `GET /seo/audits/{id}/compare?baseline_id=` — returns `AuditComparison` (score delta, issue delta, page delta, new/resolved issues)

4. **CSV Export Endpoint**
   - `GET /seo/audits/{id}/export/csv` — streams CSV with issues or pages (query param `type=issues|pages`)

5. **Progress Tracking**
   - Store progress in audit record during crawl: `{ stage: string, completed: number, total: number, current_url: string }`
   - Endpoint: `GET /seo/audits/{id}/progress` — returns progress object for polling

6. **Storage Layer Updates**
   - `SeoAuditStore.list_audits` with filter/pagination params
   - `SeoAuditStore.find_by_project` for project-scoped queries

### Phase 2: Frontend SiteAuditPage

1. **Main Component** (`SiteAuditPage.tsx`)
   - Integrate `SeoProjectSelector` at top
   - Tab navigation (6 tabs matching SEMrush terminology)
   - Responsive layout with dark theme CSS variables

2. **Tab Components**
   - **Genel Bakış**: Score ring, issue counts by severity, crawl summary, top issues
   - **Sorunlar**: Filterable/paginated table (severity, category, status), CSV export
   - **Taranan Sayfalar**: Filterable/paginated table (page type, score, status), CSV export
   - **İstatistikler**: Charts (score distribution, issues by category/depth, CWV)
   - **Audit Geçmişi**: List of audits for project with pagination, "Run New Audit" button
   - **Karşılaştırma**: Select baseline audit, show deltas (score, issues, pages)

3. **Reusable UI Components** (in `SeoUIComponents.tsx`)
   - `ProgressBar` — crawl progress with stages
   - `DataTable` — sortable, paginated, selectable rows
   - `FilterBar` — multi-select filters for severity, category, status, page type
   - `ComparisonCard` — delta visualization

4. **Service Layer**
   - `fetchAuditHistory(params)` — paginated
   - `compareAudits(currentId, baselineId)`
   - `exportAuditCsv(auditId, type)`
   - `pollAuditProgress(auditId)` — for real-time crawl updates

### Phase 3: Testing & Verification

1. **Backend**: Add tests for new endpoints, run existing 49 tests
2. **Frontend**: Type check (`npm run build`), verify no regressions
3. **Integration**: Manual test with mspovleceni.cz fixture data

---

## Reused Existing Code

| Component | Location | Reuse Strategy |
|-----------|----------|----------------|
| `SeoProjectSelector` | `vex-app/src/components/seo/SeoProjectSelector.tsx` | Embed in `SiteAuditPage` header |
| `IssueBadge`, `ScoreDisplay`, `ScoreRing`, `SeverityIndicator`, `CategoryBadge` | `vex-app/src/components/seo/SeoUIComponents.tsx` | Use directly in tabs |
| `SeoAuditService.analyze_fetches` | `vex-backend/app/services/seo_service.py` | Core logic unchanged |
| `SeoProjectService.add_audit_to_history` | `vex-backend/app/services/seo_project_service.py` | Call from `create_audit` when `project_id` present |
| `seo_core` schemas | `vex-backend/app/schemas/seo_core.py` | Extend with new models |
| `normalizeBackendAudit` | `vex-app/src/services/seo.ts` | Use for audit data normalization |

---

## Verification Checklist

### Backend (run in `vex-backend/`)
```bash
# 1. Unit tests (all 49 + new)
./.venv/bin/python -m unittest discover -s app/tests -v

# 2. Syntax & imports
./.venv/bin/python -m py_compile app/**/*.py

# 3. Health endpoint
curl -sf http://127.0.0.1:8000/health

# 4. New endpoints smoke test
curl -sf "http://127.0.0.1:8000/seo/audits?page=1&page_size=10"
curl -sf "http://127.0.0.1:8000/seo/audits/{id}/export/csv?type=issues"
```

### Frontend (run in `vex-app/`)
```bash
# 1. Type check + build
npm run build

# 2. Dev server smoke test
npm run dev  # verify no console errors
```

### Git
```bash
git diff --check
git diff --stat  # review changes
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing 49 tests | Extend, don't modify `seo_core` models; keep backward compatibility |
| CSV export performance | Stream response, paginate at 1000 rows |
| Progress polling load | 2s interval, stop on completion |
| Comparison complexity | Compute deltas in service layer, return structured `AuditComparison` |
| Dark theme consistency | Use existing CSS variables from `App.css` |

---

## Acceptance Criteria

- [ ] `SiteAuditPage` accessible via new route (e.g., `/seo/site-audit`)
- [ ] Project selector shows all projects with scores/last audit date
- [ ] 6 tabs render correctly with data from backend
- [ ] Issues table: filter by severity/category/status, paginate, CSV export
- [ ] Pages table: filter by page type/score range, paginate, CSV export
- [ ] History tab: paginated list, "Run New Audit" triggers crawl with progress
- [ ] Comparison tab: select baseline, show score/issue/page deltas
- [ ] All 49 existing tests pass
- [ ] No TypeScript errors, clean build
- [ ] Dark theme consistent with existing UI