import { useState, useEffect, useCallback } from "react";
import { ProviderStatus, ProviderInfo, SeoProjectService } from "../../services/seoProjectService";

interface ProviderStatusFieldProps {
  className?: string;
  compact?: boolean;
  onRefresh?: () => void;
}

export function ProviderStatusField({
  className = "",
  compact = false,
  onRefresh,
}: ProviderStatusFieldProps) {
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      const data = await SeoProjectService.getProviderStatus();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError("Sağlayıcı durumları yüklenemedi");
      console.error("Failed to load provider status:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  if (!status) {
    return (
      <div className={`provider-status-field ${className}`}>
        <div className="provider-status-loading">Yükleniyor...</div>
      </div>
    );
  }

  const providers = Object.entries(status);

  const getStatusColor = (provider: ProviderInfo) => {
    if (!provider.configured) return "not-configured";
    if (!provider.connected) return "disconnected";
    return "connected";
  };

  const getStatusLabel = (provider: ProviderInfo) => {
    if (!provider.configured) return "Yapılandırılmamış";
    if (!provider.connected) return "Bağlı Değil";
    return "Bağlı";
  };

  return (
    <div className={`provider-status-field ${className}`}>
      <div className="provider-status-header">
        <h4>SEO Veri Sağlayıcıları</h4>
        {onRefresh && (
          <button
            type="button"
            className="provider-status-refresh"
            onClick={loadStatus}
            disabled={loading}
          >
            {loading ? "Yenileniyor..." : "Yenile"}
          </button>
        )}
      </div>

      {error && <div className="provider-status-error">{error}</div>}

      <div className="provider-status-grid">
        {providers.map(([key, provider]) => (
          <div
            key={key}
            className={`provider-status-item ${getStatusColor(provider)}`}
          >
            <div className="provider-status-info">
              <span className="provider-status-name">{formatProviderName(key)}</span>
              <span className={`provider-status-badge ${getStatusColor(provider)}`}>
                {getStatusLabel(provider)}
              </span>
            </div>
            {!compact && (
              <div className="provider-status-details">
                {provider.configured && provider.last_sync && (
                  <span className="provider-last-sync">
                    Son senkronizasyon: {formatDate(provider.last_sync)}
                  </span>
                )}
                {provider.error && (
                  <span className="provider-error">{provider.error}</span>
                )}
                {provider.scopes && provider.scopes.length > 0 && (
                  <span className="provider-scopes">
                    Kapsam: {provider.scopes.join(", ")}
                  </span>
                )}
              </div>
            )}
            {!provider.configured && (
              <button
                type="button"
                className="provider-configure-btn"
                onClick={() => alert(`${formatProviderName(key)} konfigürasyonu henüz desteklenmiyor`)}
              >
                Yapılandır
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function formatProviderName(key: string): string {
  const names: Record<string, string> = {
    google_search_console: "Google Search Console",
    google_analytics: "Google Analytics",
    ahrefs: "Ahrefs",
    semrush: "Semrush",
    screaming_frog: "Screaming Frog",
    sitebulb: "Sitebulb",
    custom_api: "Özel API",
  };
  return names[key] || key;
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString("tr-TR");
  } catch {
    return dateStr;
  }
}

// Compact version for use in headers/sidebars
export function CompactProviderStatus({ className = "" }: { className?: string }) {
  const [status, setStatus] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await SeoProjectService.getProviderStatus();
        setStatus(data);
      } catch (err) {
        console.error("Failed to load provider status:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading || !status) return <span className={`provider-status-compact ${className}`} />;

  const connectedCount = Object.values(status).filter((p) => p.connected).length;
  const configuredCount = Object.values(status).filter((p) => p.configured).length;

  return (
    <div className={`provider-status-compact ${className}`} title={`${connectedCount}/${configuredCount} sağlayıcı bağlı`}>
      <span className="provider-status-dot" style={{ backgroundColor: connectedCount > 0 ? "#22c55e" : configuredCount > 0 ? "#f59e0b" : "#6b7280" }} />
      <span>{connectedCount}/{Object.keys(status).length}</span>
    </div>
  );
}