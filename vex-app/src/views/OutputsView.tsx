export type OutputViewData = {
  id: string;
  title: string;
  project_id: string;
  task_id: string;
  output_type: string;
  content: string;
  status: string;
  notes: string[];
};

export type OutputsViewProps = {
  outputs: OutputViewData[];
  isLoading: boolean;
  onRefresh: () => void;
  onDelete: (outputId: string) => void;
};

export function OutputsView({
  outputs,
  isLoading,
  onRefresh,
  onDelete,
}: OutputsViewProps) {
  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Proje çıktıları</p>
          <h2>Kaydedilen Çıktılar</h2>
        </div>
        <div className="topbar-actions">
          <button className="small-action-button" onClick={onRefresh}>
            Yenile
          </button>
        </div>
      </header>

      <div className="projects-page">
        {isLoading ? (
          <div className="panel-card">
            <strong>Çıktılar yükleniyor...</strong>
          </div>
        ) : outputs.length > 0 ? (
          <div className="project-grid">
            {outputs.map((output) => (
              <div className="project-card" key={output.id}>
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">
                      {output.project_id ? `Proje: ${output.project_id}` : "Genel çıktı"}
                    </p>
                    <h3>{output.title}</h3>
                  </div>

                  <div className="project-card-actions">
                    <span className="status-pill">{output.output_type}</span>
                    <span className="status-pill">{output.status}</span>

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => onDelete(output.id)}
                    >
                      Sil
                    </button>
                  </div>
                </div>

                <div className="project-section">
                  <p className="panel-label">Bağlı görev</p>
                  <ul>
                    <li>{output.task_id || "Bağlı görev yok"}</li>
                  </ul>
                </div>

                <div className="project-section">
                  <p className="panel-label">İçerik</p>
                  <pre className="payload-preview">{output.content}</pre>
                </div>

                {output.notes?.length > 0 ? (
                  <div className="project-section">
                    <p className="panel-label">Notlar</p>
                    <ul>
                      {output.notes.map((note, index) => (
                        <li key={`${output.id}-note-${index}`}>{note}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-card">
            <strong>Henüz kayıtlı çıktı yok.</strong>
            <p className="panel-label">
              Vex bir metin ürettikten sonra “bunu kaydet” diyebilirsin.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
