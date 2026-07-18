export type ProjectViewData = {
  id: string;
  name: string;
  type: string;
  status: string;
  description: string;
  main_goals: string[];
  notes: string[];
};

export type CreateProjectPayload = ProjectViewData;

type ProjectForm = {
  isOpen: boolean;
  name: string;
  type: string;
  description: string;
  goals: string;
  notes: string;
  toggle: () => void;
  setName: (value: string) => void;
  setType: (value: string) => void;
  setDescription: (value: string) => void;
  setGoals: (value: string) => void;
  setNotes: (value: string) => void;
};

type ProjectsViewProps = {
  projects: ProjectViewData[];
  activeProjectId: string;
  isProjectsLoading: boolean;
  isCreatingProject: boolean;
  projectForm: ProjectForm;
  onRefresh: () => void;
  onSelectProject: (projectId: string) => void;
  onCreateProject: (project: CreateProjectPayload) => void | Promise<void>;
  onDeleteProject: (projectId: string) => void;
};

function slugify(text: string) {
  return text
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .replace(/ğ/g, "g")
    .replace(/ü/g, "u")
    .replace(/ş/g, "s")
    .replace(/ö/g, "o")
    .replace(/ç/g, "c")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function splitLines(text: string) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function ProjectsView({
  projects,
  activeProjectId,
  isProjectsLoading,
  isCreatingProject,
  projectForm,
  onRefresh,
  onSelectProject,
  onCreateProject,
  onDeleteProject,
}: ProjectsViewProps) {
  function createProject() {
    const cleanName = projectForm.name.trim();

    if (!cleanName || isCreatingProject) {
      return;
    }

    void onCreateProject({
      id: slugify(cleanName),
      name: cleanName,
      type: projectForm.type.trim() || "Genel proje",
      status: "aktif",
      description: projectForm.description.trim(),
      main_goals: splitLines(projectForm.goals),
      notes: splitLines(projectForm.notes),
    });
  }

  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Proje merkezi</p>
          <h2>Vex Projeleri</h2>
        </div>
        <div className="topbar-actions">
          <button
            className="small-action-button"
            onClick={projectForm.toggle}
          >
            {projectForm.isOpen ? "Formu Kapat" : "Yeni Proje"}
          </button>
          <button className="small-action-button" onClick={onRefresh}>
            Yenile
          </button>
        </div>
      </header>

      <div className="projects-page">
        {projectForm.isOpen ? (
          <div className="project-form">
            <div>
              <p className="eyebrow">Yeni proje</p>
              <h3>Vex’e yeni proje ekle</h3>
            </div>

            <div className="form-grid">
              <label>
                Proje adı
                <input
                  value={projectForm.name}
                  onChange={(event) => projectForm.setName(event.target.value)}
                  placeholder="Örn: Yeni Shopify Sitesi"
                />
              </label>

              <label>
                Proje tipi
                <input
                  value={projectForm.type}
                  onChange={(event) => projectForm.setType(event.target.value)}
                  placeholder="Örn: E-ticaret / Shopify"
                />
              </label>
            </div>

            <label>
              Açıklama
              <textarea
                value={projectForm.description}
                onChange={(event) => projectForm.setDescription(event.target.value)}
                placeholder="Bu proje ne için oluşturuluyor?"
              />
            </label>

            <label>
              Ana hedefler
              <textarea
                value={projectForm.goals}
                onChange={(event) => projectForm.setGoals(event.target.value)}
                placeholder={"Her satıra bir hedef yaz\nÖrn: Global site yapısı kurulacak"}
              />
            </label>

            <label>
              Notlar
              <textarea
                value={projectForm.notes}
                onChange={(event) => projectForm.setNotes(event.target.value)}
                placeholder={"Her satıra bir not yaz\nÖrn: Tasarım modern ve premium olacak"}
              />
            </label>

            <div className="form-actions">
              <button
                className="small-action-button"
                onClick={createProject}
                disabled={isCreatingProject}
              >
                {isCreatingProject ? "Kaydediliyor..." : "Projeyi Kaydet"}
              </button>
            </div>
          </div>
        ) : null}

        {isProjectsLoading ? (
          <div className="panel-card">
            <strong>Projeler yükleniyor...</strong>
          </div>
        ) : projects.length > 0 ? (
          <div className="project-grid">
            {projects.map((project) => (
              <div className="project-card" key={project.id}>
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">{project.type}</p>
                    <h3>{project.name}</h3>
                  </div>

                  <div className="project-card-actions">
                    {activeProjectId === project.id ? (
                      <span className="status-pill">Aktif Proje</span>
                    ) : (
                      <button
                        className="small-action-button"
                        type="button"
                        onClick={() => onSelectProject(project.id)}
                      >
                        Aktif Yap
                      </button>
                    )}

                    <span className="status-pill">{project.status}</span>

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => onDeleteProject(project.id)}
                    >
                      Sil
                    </button>
                  </div>
                </div>

                <p className="project-description">{project.description}</p>

                <div className="project-section">
                  <p className="panel-label">Ana hedefler</p>
                  <ul>
                    {project.main_goals.map((goal, index) => (
                      <li key={`${project.id}-goal-${index}`}>{goal}</li>
                    ))}
                  </ul>
                </div>

                <div className="project-section">
                  <p className="panel-label">Notlar</p>
                  <ul>
                    {project.notes.map((note, index) => (
                      <li key={`${project.id}-note-${index}`}>{note}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-card">
            <strong>Henüz proje yok.</strong>
            <p className="panel-label">
              Backend’de projects.json dosyasını kontrol edelim.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
