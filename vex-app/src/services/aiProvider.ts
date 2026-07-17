import { ApiError, apiRequest } from "./apiClient";

export type ProviderMode = "auto" | "manual";

export interface ProviderHealth {
  provider: string;
  model: string;
  configured: boolean;
  enabled: boolean;
  available: boolean;
  status: "connected" | "not_configured" | "disabled" | "degraded" | "rate_limited" | "unavailable" | "checking";
  supports_streaming: boolean;
  supports_tools: boolean;
  supports_vision: boolean;
  supports_json: boolean;
  last_success_at: number | null;
  last_failure_at: number | null;
  last_error_code: string | null;
  consecutive_failures: number;
  rate_limited: boolean;
  average_latency_ms: number | null;
}

export interface ProvidersStatusResponse {
  [provider: string]: ProviderHealth;
}

export interface ProviderSettings {
  mode: ProviderMode;
  preferred_provider: string | null;
  fallback_enabled: boolean;
  fallback_order: string[];
  available_providers: string[];
  provider_lock: boolean;
}

export interface UpdateProviderSettingsRequest {
  mode?: ProviderMode;
  preferred_provider?: string | null;
  fallback_enabled?: boolean;
  fallback_order?: string[];
  provider_lock?: boolean;
}

export async function fetchProvidersStatus(): Promise<ProvidersStatusResponse> {
  try {
    return await apiRequest<ProvidersStatusResponse>("/ai/providers/status", { cache: "no-store" });
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status !== null) {
      throw new Error(`Failed to fetch providers status: ${error.status}`);
    }
    throw error;
  }
}

export async function fetchProviderSettings(): Promise<ProviderSettings> {
  try {
    return await apiRequest<ProviderSettings>("/ai/provider/settings", { cache: "no-store" });
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status !== null) {
      throw new Error(`Failed to fetch provider settings: ${error.status}`);
    }
    throw error;
  }
}

export async function updateProviderSettings(data: UpdateProviderSettingsRequest): Promise<ProviderSettings> {
  try {
    return await apiRequest<ProviderSettings>("/ai/provider/settings", {
      method: "PATCH",
      body: data,
    });
  } catch (error: unknown) {
    if (error instanceof ApiError && error.status !== null) {
      if (isRecord(error.body) && typeof error.body.detail === "string" && error.body.detail) {
        throw new Error(error.body.detail);
      }
      throw new Error(`Failed to update settings: ${error.status}`);
    }
    throw error;
  }
}

export function getStatusColor(status: ProviderHealth["status"]): string {
  switch (status) {
    case "connected": return "#22c55e";
    case "degraded": return "#f59e0b";
    case "rate_limited": return "#f97316";
    case "unavailable":
    case "not_configured":
    case "disabled": return "#ef4444";
    case "checking": return "#3b82f6";
    default: return "#6b7280";
  }
}

export function getStatusLabel(status: ProviderHealth["status"]): string {
  const labels: Record<ProviderHealth["status"], string> = {
    connected: "Bağlı",
    not_configured: "Yapılandırılmamış",
    disabled: "Devre Dışı",
    degraded: "Boğulmuş",
    rate_limited: "Sınırlı",
    unavailable: "Erişilemez",
    checking: "Kontrol Ediliyor",
  };
  return labels[status] || status;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
