type BackendStatus = "checking" | "online" | "offline";

type ProjectSummary = {
  name: string;
  type: string;
};

type TaskSummary = {
  id: string;
  title: string;
  project_id: string;
  status: string;
  priority: string;
};

type ApprovalSummary = {
  id: string;
  title: string;
  risk_level: string;
};

type OutputSummary = {
  id: string;
  title: string;
  output_type: string;
  status: string;
};

type WorkspaceSummaryViewData = {
  counts: {
    active_projects: number;
    open_tasks: number;
    high_priority_tasks: number;
    pending_approvals: number;
    outputs?: number;
  };
  high_priority_tasks: TaskSummary[];
  pending_approvals: ApprovalSummary[];
  suggested_next_step: string;
};

type ActiveProjectDetailViewData = {
  has_active_project: boolean;
  project: {
    description: string;
  } | null;
  open_tasks: TaskSummary[];
  high_priority_tasks: TaskSummary[];
  pending_approvals: ApprovalSummary[];
  outputs: OutputSummary[];
  counts?: {
    open_tasks: number;
    high_priority_tasks: number;
    pending_approvals: number;
  };
  suggested_next_step: string;
};

export type DashboardViewProps = {
  backendStatus: BackendStatus;
  isWorkspaceLoading: boolean;
  workspaceSummary: WorkspaceSummaryViewData | null;
  activeProject: ProjectSummary | null;
  isActiveProjectDetailLoading: boolean;
  activeProjectDetail: ActiveProjectDetailViewData | null;
  onRefresh: () => void;
  onOpenProjects: () => void;
  onOpenTasks: () => void;
  onOpenApprovals: () => void;
  onOpenOutputs: () => void;
};

function getBackendLabel(backendStatus: BackendStatus) {
  if (backendStatus === "online") return "Backend: Bağlı";
  if (backendStatus === "offline") return "Backend: Kapalı";
  return "Backend: Kontrol Ediliyor";
}

export function DashboardView({
  backendStatus,
  isWorkspaceLoading,
  workspaceSummary,
  activeProject,
  isActiveProjectDetailLoading,
  activeProjectDetail,
  onRefresh,
  onOpenProjects,
  onOpenTasks,
  onOpenApprovals,
  onOpenOutputs,
}: DashboardViewProps) {
  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Vex çalışma alanı</p>
          <h2>Dashboard</h2>
        </div>
        <div className="topbar-actions">
          <button className="small-action-button" onClick={onRefresh}>
            Yenile
          </button>

          <span className={`status-pill backend-${backendStatus === "checking" ? "online" : backendStatus}`}>
            {getBackendLabel(backendStatus)}
          </span>
        </div>
      </header>

      <div className="projects-page">
        {isWorkspaceLoading ? (
          <div className="panel-card">
            <strong>Dashboard yükleniyor...</strong>
          </div>
        ) : workspaceSummary ? (
          <>
            <div className="memory-grid">
              <div className="memory-card">
                <p className="panel-label">Şu an üzerinde çalışılan proje</p>
                <h3>{activeProject?.name ?? "Seçilmedi"}</h3>
                <p>{activeProject?.type ?? "Projeler panelinden aktif proje seçebilirsin."}</p>
              </div>

              <div className="memory-card">
                <p className="panel-label">Aktif projeler</p>
                <h3>{workspaceSummary.counts.active_projects}</h3>
              </div>

              <div className="memory-card">
                <p className="panel-label">Açık görevler</p>
                <h3>{workspaceSummary.counts.open_tasks}</h3>
              </div>

              <div className="memory-card">
                <p className="panel-label">Yüksek öncelik</p>
                <h3>{workspaceSummary.counts.high_priority_tasks}</h3>
              </div>

              <div className="memory-card">
                <p className="panel-label">Bekleyen onay</p>
                <h3>{workspaceSummary.counts.pending_approvals}</h3>
              </div>

              <div className="memory-card">
                <p className="panel-label">Kaydedilen çıktılar</p>
                <h3>{workspaceSummary.counts.outputs ?? 0}</h3>
              </div>
            </div>

            <div className="memory-section">
              <div className="memory-section-header">
                <div>
                  <p className="eyebrow">Önerilen sonraki adım</p>
                  <h3>{workspaceSummary.suggested_next_step}</h3>
                </div>
              </div>
            </div>

            <div className="memory-section">
              <div className="memory-section-header">
                <div>
                  <p className="eyebrow">Aktif proje çalışma alanı</p>
                  <h3>{activeProject?.name ?? "Aktif proje seçilmedi"}</h3>
                </div>

                <button className="small-action-button" onClick={onOpenProjects}>
                  Proje Seç
                </button>
              </div>

              {isActiveProjectDetailLoading ? (
                <p className="panel-label">Aktif proje detayı yükleniyor...</p>
              ) : activeProjectDetail?.has_active_project ? (
                <>
                  <p className="project-description">{activeProjectDetail.project?.description}</p>

                  <div className="memory-grid">
                    <div className="memory-card">
                      <p className="panel-label">Bu projedeki açık görevler</p>
                      <h3>{activeProjectDetail.counts?.open_tasks ?? 0}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Yüksek öncelikli görevler</p>
                      <h3>{activeProjectDetail.counts?.high_priority_tasks ?? 0}</h3>
                    </div>

                    <div className="memory-card">
                      <p className="panel-label">Bekleyen onaylar</p>
                      <h3>{activeProjectDetail.counts?.pending_approvals ?? 0}</h3>
                    </div>
                  </div>

                  <div className="project-section">
                    <p className="panel-label">Vex’in önerdiği sonraki adım</p>
                    <p>{activeProjectDetail.suggested_next_step}</p>
                  </div>

                  <div className="project-grid">
                    <div className="project-card">
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">Aktif proje görevleri</p>
                          <h3>Öncelikli işler</h3>
                        </div>
                        <button className="small-action-button" onClick={onOpenTasks}>
                          Görevlere Git
                        </button>
                      </div>

                      <div className="project-section">
                        {activeProjectDetail.high_priority_tasks.length > 0 ? (
                          <ul>
                            {activeProjectDetail.high_priority_tasks.slice(0, 5).map((task) => (
                              <li key={task.id}>
                                {task.title} — {task.priority}
                              </li>
                            ))}
                          </ul>
                        ) : activeProjectDetail.open_tasks.length > 0 ? (
                          <ul>
                            {activeProjectDetail.open_tasks.slice(0, 5).map((task) => (
                              <li key={task.id}>
                                {task.title} — {task.status}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="panel-label">Bu proje için açık görev yok.</p>
                        )}
                      </div>
                    </div>

                    <div className="project-card">
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">Aktif proje onayları</p>
                          <h3>Bekleyen kararlar</h3>
                        </div>
                        <button className="small-action-button" onClick={onOpenApprovals}>
                          Onaylara Git
                        </button>
                      </div>

                      <div className="project-section">
                        {activeProjectDetail.pending_approvals.length > 0 ? (
                          <ul>
                            {activeProjectDetail.pending_approvals.slice(0, 5).map((approval) => (
                              <li key={approval.id}>
                                {approval.title} — {approval.risk_level}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="panel-label">Bu proje için bekleyen onay yok.</p>
                        )}
                      </div>
                    </div>

                    <div className="project-card">
                      <div className="project-card-header">
                        <div>
                          <p className="panel-label">Aktif proje çıktıları</p>
                          <h3>Kaydedilen taslaklar</h3>
                        </div>
                        <button className="small-action-button" onClick={onOpenOutputs}>
                          Çıktılara Git
                        </button>
                      </div>

                      <div className="project-section">
                        {activeProjectDetail.outputs?.length > 0 ? (
                          <ul>
                            {activeProjectDetail.outputs.slice(0, 5).map((output) => (
                              <li key={output.id}>
                                {output.title} — {output.output_type} / {output.status}
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="panel-label">Bu proje için kayıtlı çıktı yok.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <p className="panel-label">
                  Aktif proje seçilmedi. Projeler panelinden bir projeyi aktif yapabilirsin.
                </p>
              )}
            </div>

            <div className="project-grid">
              <div className="project-card">
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">Öncelikli görevler</p>
                    <h3>Bugün bakılacak işler</h3>
                  </div>
                  <button className="small-action-button" onClick={onOpenTasks}>
                    Görevlere Git
                  </button>
                </div>

                <div className="project-section">
                  {workspaceSummary.high_priority_tasks.length > 0 ? (
                    <ul>
                      {workspaceSummary.high_priority_tasks.slice(0, 5).map((task) => (
                        <li key={task.id}>
                          {task.title} — {task.project_id || "Genel"} / {task.priority}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="panel-label">Yüksek öncelikli açık görev yok.</p>
                  )}
                </div>
              </div>

              <div className="project-card">
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">Bekleyen onaylar</p>
                    <h3>Riskli işlemler</h3>
                  </div>
                  <button className="small-action-button" onClick={onOpenApprovals}>
                    Onaylara Git
                  </button>
                </div>

                <div className="project-section">
                  {workspaceSummary.pending_approvals.length > 0 ? (
                    <ul>
                      {workspaceSummary.pending_approvals.slice(0, 5).map((approval) => (
                        <li key={approval.id}>
                          {approval.title} — {approval.risk_level}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="panel-label">Bekleyen onay yok.</p>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="panel-card">
            <strong>Dashboard yüklenemedi.</strong>
            <p className="panel-label">Backend çalışıyor mu kontrol edelim.</p>
          </div>
        )}
      </div>
    </>
  );
}
