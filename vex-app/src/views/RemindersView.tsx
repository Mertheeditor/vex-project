export type ReminderData = {
  id: string;
  title: string;
  remind_at: string;
  project_id: string;
  task_id: string;
  status: string;
  notified: boolean;
  notes: string[];
};

export type RemindersViewProps = {
  reminders: ReminderData[];
  isLoading: boolean;
  onRefresh: () => void;
  onDelete: (reminderId: string) => void;
};

export function RemindersView({
  reminders,
  isLoading,
  onRefresh,
  onDelete,
}: RemindersViewProps) {
  return (
    <>
      <header className="topbar">
        <div>
          <p className="eyebrow">Alarm ve hatırlatma sistemi</p>
          <h2>Hatırlatmalar</h2>
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
            <strong>Hatırlatmalar yükleniyor...</strong>
          </div>
        ) : reminders.length > 0 ? (
          <div className="project-grid">
            {reminders.map((reminder) => (
              <div className="project-card" key={reminder.id}>
                <div className="project-card-header">
                  <div>
                    <p className="panel-label">
                      {reminder.project_id ? `Proje: ${reminder.project_id}` : "Genel hatırlatma"}
                    </p>
                    <h3>{reminder.title}</h3>
                  </div>

                  <div className="project-card-actions">
                    <span className="status-pill">{reminder.status}</span>
                    <span className="status-pill">{reminder.notified ? "bildirildi" : "bekliyor"}</span>

                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => onDelete(reminder.id)}
                    >
                      Sil
                    </button>
                  </div>
                </div>

                <div className="project-section">
                  <p className="panel-label">Zaman</p>
                  <ul>
                    <li>{reminder.remind_at}</li>
                  </ul>
                </div>

                <div className="project-section">
                  <p className="panel-label">Bağlantı</p>
                  <ul>
                    <li>Görev: {reminder.task_id || "Bağlı görev yok"}</li>
                  </ul>
                </div>

                {reminder.notes?.length > 0 ? (
                  <div className="project-section">
                    <p className="panel-label">Notlar</p>
                    <ul>
                      {reminder.notes.map((note, index) => (
                        <li key={`${reminder.id}-note-${index}`}>{note}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="panel-card">
            <strong>Henüz hatırlatma yok.</strong>
            <p className="panel-label">
              “30 dakika sonra beni uyar” veya “saat 18:00’de bunu hatırlat” diyebilirsin.
            </p>
          </div>
        )}
      </div>
    </>
  );
}
