import { useEffect, useState } from "react";
import {
  fetchProvidersStatus,
  fetchProviderSettings,
  updateProviderSettings,
  type ProviderHealth,
  type ProviderSettings,
  type UpdateProviderSettingsRequest,
  getStatusColor,
  getStatusLabel,
} from "../../services/aiProvider";

export function ProviderSettingsPanel() {
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [health, setHealth] = useState<Record<string, ProviderHealth>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [settingsData, healthData] = await Promise.all([
        fetchProviderSettings(),
        fetchProvidersStatus(),
      ]);
      setSettings(settingsData);
      setHealth(healthData);
    } catch (e) {
      setMessage({ type: "error", text: `Yükleme hatası: ${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async (updates: UpdateProviderSettingsRequest) => {
    if (!settings) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await updateProviderSettings(updates);
      setSettings(updated);
      setMessage({ type: "success", text: "Ayarlar kaydedildi." });
      // Re-fetch health after settings change
      const healthData = await fetchProvidersStatus();
      setHealth(healthData);
    } catch (e) {
      setMessage({ type: "error", text: `Kayıt hatası: ${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="provider-settings-panel">
        <div className="panel-card" style={{ textAlign: "center", padding: "40px" }}>
          <strong>AI Sağlayıcı ayarları yükleniyor...</strong>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="provider-settings-panel">
        <div className="panel-card" style={{ textAlign: "center", padding: "40px" }}>
          <strong style={{ color: "#ef4444" }}>Ayarlar yüklenemedi.</strong>
        </div>
      </div>
    );
  }

  const providers = settings.available_providers;
  const currentMode = settings.mode;
  const currentPreferred = settings.preferred_provider;
  const fallbackEnabled = settings.fallback_enabled;
  const fallbackOrder = settings.fallback_order;
  const providerLock = settings.provider_lock;

  return (
    <div className="provider-settings-panel">
      <div className="panel-card" style={{ marginBottom: "20px" }}>
        <div className="panel-header">
          <p className="panel-label">Yönlendirme Modu</p>
          <h3>Aktif: {currentMode === "auto" ? "Otomatik" : "Manuel"}</h3>
        </div>

        <div className="settings-grid">
          <label className="setting-item">
            <div className="setting-label">
              <strong>Mod</strong>
              <span className="setting-hint">
                {currentMode === "auto" ? "Görev türüne göre en iyi sağlayıcıyı otomatik seç" : "Belirli bir sağlayıcıyı kilitle"}
              </span>
            </div>
            <div className="setting-control">
              <label className="radio-inline">
                <input
                  type="radio"
                  name="mode"
                  value="auto"
                  checked={currentMode === "auto"}
                  onChange={() => handleSave({ mode: "auto" })}
                  disabled={saving}
                />
                <span>Otomatik</span>
              </label>
              <label className="radio-inline">
                <input
                  type="radio"
                  name="mode"
                  value="manual"
                  checked={currentMode === "manual"}
                  onChange={() => handleSave({ mode: "manual" })}
                  disabled={saving}
                />
                <span>Manuel</span>
              </label>
            </div>
          </label>

          {providers.length > 1 && (
            <label className="setting-item">
              <div className="setting-label">
                <strong>Tercih Edilen Sağlayıcı (Manuel Mod)</strong>
                <span className="setting-hint">Manuel moddayken kullanılacak sağlayıcı</span>
              </div>
              <div className="setting-control">
                <select
                  value={currentPreferred || ""}
                  onChange={(e) => handleSave({ preferred_provider: e.target.value || null })}
                  disabled={saving || currentMode !== "manual" || providers.length <= 1}
                  style={{ width: "100%", maxWidth: "300px" }}
                >
                  <option value="">— Otomatik Seç —</option>
                  {providers.map((p: string) => (
                    <option key={p} value={p}>
                      {p === "gemini" ? "Google Gemini" : p === "nvidia" ? "NVIDIA NIM" : p}
                    </option>
                  ))}
                </select>
                {currentMode !== "manual" && (
                  <span className="setting-hint">Manuel mod seçildiğinde aktif olur</span>
                )}
              </div>
            </label>
          )}

          <label className="setting-item">
            <div className="setting-label">
              <strong>Sağlayıcı Kilidi</strong>
              <span className="setting-hint">
                Açıkken, seçili sağlayıcı başarısız olsa bile yedek sağlayıcıya düşmez
              </span>
            </div>
            <div className="setting-control">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={providerLock}
                  onChange={(e) => handleSave({ provider_lock: e.target.checked })}
                  disabled={saving}
                />
                <span className="toggle-slider"></span>
              </label>
              <span className="toggle-label">{providerLock ? "Açık" : "Kapalı"}</span>
            </div>
          </label>

          <label className="setting-item">
            <div className="setting-label">
              <strong>Yedek Sağlayıcı (Fallback)</strong>
              <span className="setting-hint">
                Birincil sağlayıcı başarısız olursa otomatik olarak yedek sağlayıcıları dene
              </span>
            </div>
            <div className="setting-control">
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={fallbackEnabled}
                  onChange={(e) => handleSave({ fallback_enabled: e.target.checked })}
                  disabled={saving}
                />
                <span className="toggle-slider"></span>
              </label>
              <span className="toggle-label">{fallbackEnabled ? "Açık" : "Kapalı"}</span>
            </div>
          </label>

          {fallbackEnabled && (
            <label className="setting-item">
              <div className="setting-label">
                <strong>Yedek Sıralaması</strong>
                <span className="setting-hint">
                  Sürükleyerek sıralayın (ilk denenen en üstte)
                </span>
              </div>
              <div className="setting-control">
                <div className="fallback-order-list">
                  {fallbackOrder.map((p: string, i: number) => (
                    <div key={p} className="fallback-order-item" style={{ opacity: i === 0 ? 1 : 0.7 }}>
                      <span className="fallback-order-index">{i + 1}.</span>
                      <span className="fallback-order-name">
                        {p === "gemini" ? "Google Gemini" : p === "nvidia" ? "NVIDIA NIM" : p}
                      </span>
                      {health[p] && (
                        <span
                          className="provider-status-badge"
                          style={{ backgroundColor: getStatusColor(health[p].status) }}
                        >
                          {getStatusLabel(health[p].status)}
                        </span>
                      )}
                    </div>
                  ))}
                  {fallbackOrder.length === 0 && (
                    <div className="fallback-order-item" style={{ opacity: 0.5, fontStyle: "italic" }}>
                      Yedek sağlayıcı yok
                    </div>
                  )}
                </div>
              </div>
            </label>
          )}
        </div>
      </div>

      <div className="panel-card" style={{ marginBottom: "20px" }}>
        <p className="panel-label">Sağlayıcı Sağlık Durumu</p>
        <div className="health-grid">
          {providers.map((p: string) => {
            const h = health[p];
            return (
              <div key={p} className="health-card" style={{ borderLeftColor: h ? getStatusColor(h.status) : "#6b7280" }}>
                <div className="health-header">
                  <strong>{p === "gemini" ? "Google Gemini" : p === "nvidia" ? "NVIDIA NIM" : p}</strong>
                  <span
                    className="health-status"
                    style={{ backgroundColor: h ? getStatusColor(h.status) : "#6b7280" }}
                  >
                    {h ? getStatusLabel(h.status) : "Bilinmiyor"}
                  </span>
                </div>
                {h && (
                  <div className="health-details">
                    <div className="health-row">
                      <span>Model:</span>
                      <span>{h.model}</span>
                    </div>
                    <div className="health-row">
                      <span>Yapılandırılmış:</span>
                      <span>{h.configured ? "Evet" : "Hayır"}</span>
                    </div>
                    <div className="health-row">
                      <span>Etkin:</span>
                      <span>{h.enabled ? "Evet" : "Hayır"}</span>
                    </div>
                    <div className="health-row">
                      <span>Kullanılabilir:</span>
                      <span>{h.available ? "Evet" : "Hayır"}</span>
                    </div>
                    {h.average_latency_ms && h.average_latency_ms > 0 && (
                      <div className="health-row">
                        <span>Ort. Gecikme:</span>
                        <span>{Math.round(h.average_latency_ms)} ms</span>
                      </div>
                    )}
                    {h.consecutive_failures > 0 && (
                      <div className="health-row" style={{ color: "#ef4444" }}>
                        <span>Ardışık Hata:</span>
                        <span>{h.consecutive_failures}</span>
                      </div>
                    )}
                    {h.last_error_code && (
                      <div className="health-row" style={{ color: "#f59e0b", fontSize: "12px" }}>
                        <span>Son Hata:</span>
                        <span>{h.last_error_code}</span>
                      </div>
                    )}
                    <div className="health-capabilities">
                      <span className={`cap-badge ${h.supports_streaming ? "active" : ""}`}>Streaming</span>
                      <span className={`cap-badge ${h.supports_tools ? "active" : ""}`}>Araçlar</span>
                      <span className={`cap-badge ${h.supports_vision ? "active" : ""}`}>Vision</span>
                      <span className={`cap-badge ${h.supports_json ? "active" : ""}`}>JSON Modu</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {message && (
        <div className={`toast-message ${message.type}`} style={{ marginTop: "16px", padding: "12px 16px", borderRadius: "8px", background: message.type === "success" ? "rgba(34, 197, 94, 0.15)" : "rgba(239, 68, 68, 0.15)", border: message.type === "success" ? "1px solid #22c55e" : "1px solid #ef4444", color: message.type === "success" ? "#22c55e" : "#ef4444", display: "flex", alignItems: "center", gap: "8px" }}>
          {message.type === "success" ? "✓" : "✕"} {message.text}
        </div>
      )}
    </div>
  );
}