import { useState, useEffect, useCallback } from "react";
import { SeoProjectService } from "../../services/seoProjectService";
import { ScoreDisplay } from "./SeoUIComponents";

interface SeoProjectOption {
  id: string;
  name: string;
  domain: string;
  last_audit_at?: string | null;
  last_score?: number | null;
}

interface SeoProjectSelectorProps {
  value?: string;
  onChange?: (projectId: string) => void;
  placeholder?: string;
  className?: string;
  includeEmpty?: boolean;
  emptyLabel?: string;
  showDetails?: boolean;
  disabled?: boolean;
  onCreateNew?: () => void;
}

export function SeoProjectSelector({
  value,
  onChange,
  className = "",
  includeEmpty = true,
  emptyLabel = "Tüm projeler",
  showDetails = true,
  disabled = false,
  onCreateNew,
}: SeoProjectSelectorProps) {
  const [projects, setProjects] = useState<SeoProjectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const data = await SeoProjectService.listProjects();
      setProjects(
        data.map((p) => ({
          id: p.id,
          name: p.name,
          domain: p.domain,
          last_audit_at: p.last_audit_at ?? null,
          last_score: p.last_score ?? null,
        }))
      );
      setError(null);
    } catch (err) {
      setError("Projeler yüklenemedi");
      console.error("Failed to load SEO projects:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleSelect = (projectId: string) => {
    onChange?.(projectId);
    setOpen(false);
  };

  const handleCreateNew = () => {
    setOpen(false);
    onCreateNew?.();
  };

  if (loading) {
    return (
      <div className={`seo-project-selector ${className}`}>
        <select disabled={disabled} className="seo-project-select">
          <option value="">Yükleniyor...</option>
        </select>
      </div>
    );
  }

  return (
    <div className={`seo-project-selector ${className}`}>
      <div className="seo-project-select-wrapper">
        <select
          value={value || ""}
          onChange={(e) => handleSelect(e.target.value)}
          onClick={() => !disabled && setOpen(!open)}
          disabled={disabled}
          className="seo-project-select"
        >
          {includeEmpty && <option value="">{emptyLabel}</option>}
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name} ({project.domain})
            </option>
          ))}
        </select>
        {onCreateNew && (
          <button
            type="button"
            className="seo-project-create-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleCreateNew();
            }}
            disabled={disabled}
          >
            + Yeni Proje
          </button>
        )}
      </div>

      {error && <div className="seo-project-error">{error}</div>}

      {showDetails && (
        <div className="seo-project-selected-info">
          {value && projects.find((p) => p.id === value) && (
            <div className="seo-project-selected-detail">
              <SeoProjectSummary project={projects.find((p) => p.id === value)!} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface SeoProjectSummaryProps {
  project: SeoProjectOption;
}

function SeoProjectSummary({ project }: SeoProjectSummaryProps) {
  return (
    <div className="seo-project-summary">
      <div className="seo-project-main">
        <span className="seo-project-name">{project.name}</span>
        <span className="seo-project-domain">{project.domain}</span>
      </div>
      <div className="seo-project-meta">
        {project.last_score != null && (
          <span className="seo-project-score">
            Son skor: <strong>{project.last_score}/100</strong>
          </span>
        )}
        {project.last_audit_at && (
          <span className="seo-project-last-audit">
            Son audit: {formatDate(project.last_audit_at)}
          </span>
        )}
      </div>
    </div>
  );
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

// Project List View (for settings/management pages)
interface SeoProjectListProps {
  selectedId?: string;
  onSelect?: (project: SeoProjectOption) => void;
  onEdit?: (project: SeoProjectOption) => void;
  onDelete?: (projectId: string) => void;
  onCreateNew?: () => void;
  className?: string;
}

export function SeoProjectList({
  selectedId,
  onSelect,
  onEdit,
  onDelete,
  onCreateNew,
  className = "",
}: SeoProjectListProps) {
  const [projects, setProjects] = useState<SeoProjectOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      const data = await SeoProjectService.listProjects();
      setProjects(
        data.map((p) => ({
          id: p.id,
          name: p.name,
          domain: p.domain,
          last_audit_at: p.last_audit_at ?? null,
          last_score: p.last_score ?? null,
        }))
      );
      setError(null);
    } catch (err) {
      setError("Projeler yüklenemedi");
      console.error("Failed to load SEO projects:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const handleDelete = async (projectId: string) => {
    if (!window.confirm("Bu projeyi silmek istediğinizden emin misiniz?")) return;
    try {
      await SeoProjectService.deleteProject(projectId);
      loadProjects();
    } catch (err) {
      alert("Proje silinemedi");
    }
  };

  if (loading) {
    return <div className={`seo-project-list ${className}`}>Yükleniyor...</div>;
  }

  return (
    <div className={`seo-project-list ${className}`}>
      {onCreateNew && (
        <button type="button" className="seo-project-list-create" onClick={onCreateNew}>
          + Yeni SEO Projesi Oluştur
        </button>
      )}

      {error && <div className="seo-project-list-error">{error}</div>}

      <ul className="seo-project-list-items">
        {projects.map((project) => (
          <li
            key={project.id}
            className={`seo-project-list-item ${project.id === selectedId ? "selected" : ""}`}
            onClick={() => onSelect?.(project)}
          >
            <div className="seo-project-list-info">
              <span className="seo-project-list-name">{project.name}</span>
              <span className="seo-project-list-domain">{project.domain}</span>
            </div>
            <div className="seo-project-list-meta">
              {project.last_score != null && (
                <ScoreDisplay score={project.last_score} size="sm" showLabel={false} />
              )}
              {project.last_audit_at && (
                <span className="seo-project-list-date">
                  {formatRelativeDate(project.last_audit_at)}
                </span>
              )}
            </div>
            <div className="seo-project-list-actions">
              {onEdit && (
                <button
                  type="button"
                  className="seo-project-edit-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEdit(project);
                  }}
                >
                  Düzenle
                </button>
              )}
              {onDelete && (
                <button
                  type="button"
                  className="seo-project-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(project.id);
                  }}
                >
                  Sil
                </button>
              )}
            </div>
          </li>
        ))}
        {projects.length === 0 && (
          <li className="seo-project-list-empty">
            Henüz SEO projesi yok. Başlamak için "Yeni SEO Projesi Oluştur" butonuna tıklayın.
          </li>
        )}
      </ul>
    </div>
  );
}

function formatRelativeDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

    if (diffDays > 7) {
      return date.toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
    } else if (diffDays > 0) {
      return `${diffDays} gün önce`;
    } else if (diffHours > 0) {
      return `${diffHours} saat önce`;
    } else {
      return "Az önce";
    }
  } catch {
    return dateStr;
  }
}