export type TaskData = {
  id: string;
  title: string;
  project_id: string;
  status: string;
  priority: string;
  description: string;
  notes: string[];
};

export type TaskFromChatResult = {
  success: boolean;
  message: string;
  task?: TaskData;
  tasks?: TaskData[];
  source_message?: string;
};

export type ActiveTaskResponse = {
  success: boolean;
  message?: string;
  task_id: string;
  task: TaskData | null;
};

type TasksViewProps = {
  tasks: TaskData[];
  activeTaskId: string;
  isTasksLoading: boolean;
  onRefresh: () => void;
  onSelectTask: (taskId: string) => void;
  onCompleteTask: (taskId: string) => void;
  onDeleteTask: (taskId: string) => void;
};

export function TasksView({
  tasks,
  activeTaskId,
  isTasksLoading,
  onRefresh,
  onSelectTask,
  onCompleteTask,
  onDeleteTask,
}: TasksViewProps) {
  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Görev merkezi</p>
          <h2>Vex Görevleri</h2>
        </div>
        <div className="topbar-actions">
          <button className="small-action-button" onClick={onRefresh}>
            Yenile
          </button>
        </div>
      </header>

      <div className="projects-page">
        {isTasksLoading ? (
          <div className="panel-card">
            <strong>Görevler yükleniyor...</strong>
          </div>
        ) : tasks.length > 0 ? (
          <div className="project-grid">
            {tasks.map((task) => (
              <div className="project-card" key={task.id}>
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">
                      {task.project_id ? `Proje: ${task.project_id}` : "Genel görev"}
                    </p>
                    <h3>{task.title}</h3>
                  </div>

                  <div className="project-card-actions">
                    {activeTaskId === task.id ? (
                      <span className="status-pill">Aktif Görev</span>
                    ) : (
                      <button
                        className="small-action-button"
                        type="button"
                        onClick={() => onSelectTask(task.id)}
                      >
                        Aktif Yap
                      </button>
                    )}

                    <span className="status-pill">{task.priority}</span>
                    <span className="status-pill">{task.status}</span>

                    {task.status !== "tamamlandı" ? (
                      <button
                        className="small-action-button"
                        type="button"
                        onClick={() => onCompleteTask(task.id)}
                      >
                        Tamamla
                      </button>
                    ) : null}

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => onDeleteTask(task.id)}
                    >
                      Sil
                    </button>
                  </div>
                </div>

                <p className="project-description">
                  {task.description || "Açıklama yok."}
                </p>

                {task.notes?.length > 0 ? (
                  <div className="project-section">
                    <p className="panel-label">Notlar</p>
                    <ul>
                      {task.notes.map((note, index) => (
                        <li key={`${task.id}-note-${index}`}>{note}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-card">
            <strong>Henüz görev yok.</strong>
            <p className="panel-label">
              Sohbette “Bilsanpack için şu işi görev olarak ekle” diyebilirsin.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
