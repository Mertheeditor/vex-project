import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { DashboardView } from "./DashboardView";

const workspaceSummary = {
  counts: {
    active_projects: 3,
    open_tasks: 7,
    high_priority_tasks: 2,
    pending_approvals: 1,
    outputs: 4,
  },
  high_priority_tasks: [
    {
      id: "task-1",
      title: "Yayın planını tamamla",
      project_id: "project-1",
      status: "open",
      priority: "high",
    },
  ],
  pending_approvals: [
    {
      id: "approval-1",
      title: "Canlıya çıkışı onayla",
      risk_level: "medium",
    },
  ],
  suggested_next_step: "Öncelikli görevi tamamla",
};

const activeProjectDetail = {
  has_active_project: true,
  project: {
    description: "Yeni mağaza deneyimi",
  },
  open_tasks: [],
  high_priority_tasks: workspaceSummary.high_priority_tasks,
  pending_approvals: workspaceSummary.pending_approvals,
  outputs: [
    {
      id: "output-1",
      title: "Ana sayfa taslağı",
      output_type: "document",
      status: "draft",
    },
  ],
  counts: {
    open_tasks: 7,
    high_priority_tasks: 2,
    pending_approvals: 1,
  },
  suggested_next_step: "Tasarımı gözden geçir",
};

function createProps(
  overrides: Partial<ComponentProps<typeof DashboardView>> = {},
): ComponentProps<typeof DashboardView> {
  return {
    backendStatus: "online",
    isWorkspaceLoading: false,
    workspaceSummary,
    activeProject: {
      name: "Global Mağaza",
      type: "E-ticaret",
    },
    isActiveProjectDetailLoading: false,
    activeProjectDetail,
    onRefresh: vi.fn(),
    onOpenProjects: vi.fn(),
    onOpenTasks: vi.fn(),
    onOpenApprovals: vi.fn(),
    onOpenOutputs: vi.fn(),
    ...overrides,
  };
}

describe("DashboardView", () => {
  it("renders the dashboard heading and supplied workspace data without a network call", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<DashboardView {...createProps()} />);

    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    expect(screen.getAllByText("Global Mağaza")).toHaveLength(2);
    expect(screen.getByText("Öncelikli görevi tamamla")).toBeVisible();
    expect(screen.getAllByText(/Yayın planını tamamla/)).toHaveLength(2);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("calls the refresh callback from the refresh action", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<DashboardView {...createProps({ onRefresh })} />);

    await user.click(screen.getByRole("button", { name: "Yenile" }));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("keeps navigation actions delegated to the app", async () => {
    const user = userEvent.setup();
    const onOpenProjects = vi.fn();
    render(<DashboardView {...createProps({ onOpenProjects })} />);

    await user.click(screen.getByRole("button", { name: "Proje Seç" }));

    expect(onOpenProjects).toHaveBeenCalledOnce();
  });

  it("shows the workspace loading state", () => {
    render(<DashboardView {...createProps({ isWorkspaceLoading: true })} />);

    expect(screen.getByText("Dashboard yükleniyor...")).toBeVisible();
    expect(screen.queryByText("Öncelikli görevi tamamla")).not.toBeInTheDocument();
  });

  it("shows the workspace error state when summary data is unavailable", () => {
    render(<DashboardView {...createProps({ workspaceSummary: null })} />);

    expect(screen.getByText("Dashboard yüklenemedi.")).toBeVisible();
    expect(screen.getByText("Backend çalışıyor mu kontrol edelim.")).toBeVisible();
  });

  it("preserves empty states for an active project with no work items", () => {
    render(
      <DashboardView
        {...createProps({
          activeProjectDetail: {
            ...activeProjectDetail,
            open_tasks: [],
            high_priority_tasks: [],
            pending_approvals: [],
            outputs: [],
          },
        })}
      />,
    );

    expect(screen.getByText("Bu proje için açık görev yok.")).toBeVisible();
    expect(screen.getByText("Bu proje için bekleyen onay yok.")).toBeVisible();
    expect(screen.getByText("Bu proje için kayıtlı çıktı yok.")).toBeVisible();
  });
});
