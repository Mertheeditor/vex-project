import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { TasksView } from "./TasksView";

const tasks = [
  {
    id: "task-active",
    title: "Ürün sayfasını hazırla",
    project_id: "bilsanpack",
    status: "devam ediyor",
    priority: "yüksek",
    description: "Yeni ürün sayfasının içeriğini tamamla.",
    notes: ["Mobil görünümü kontrol et"],
  },
  {
    id: "task-completed",
    title: "Anahtar kelimeleri çıkar",
    project_id: "",
    status: "tamamlandı",
    priority: "normal",
    description: "",
    notes: [],
  },
];

function createProps(
  overrides: Partial<ComponentProps<typeof TasksView>> = {},
): ComponentProps<typeof TasksView> {
  return {
    tasks,
    activeTaskId: "task-active",
    isTasksLoading: false,
    onRefresh: vi.fn(),
    onSelectTask: vi.fn(),
    onCompleteTask: vi.fn(),
    onDeleteTask: vi.fn(),
    ...overrides,
  };
}

describe("TasksView", () => {
  it("renders the tasks heading and supplied task list", () => {
    render(<TasksView {...createProps()} />);

    expect(screen.getByRole("heading", { name: "Vex Görevleri" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Ürün sayfasını hazırla" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Anahtar kelimeleri çıkar" })).toBeVisible();
  });

  it("shows project, priority, status, description and notes", () => {
    render(<TasksView {...createProps()} />);

    expect(screen.getByText("Proje: bilsanpack")).toBeVisible();
    expect(screen.getByText("Genel görev")).toBeVisible();
    expect(screen.getByText("yüksek")).toBeVisible();
    expect(screen.getByText("devam ediyor")).toBeVisible();
    expect(screen.getByText("Yeni ürün sayfasının içeriğini tamamla.")).toBeVisible();
    expect(screen.getByText("Mobil görünümü kontrol et")).toBeVisible();
    expect(screen.getByText("Açıklama yok.")).toBeVisible();
  });

  it("preserves the loading state", () => {
    render(<TasksView {...createProps({ isTasksLoading: true })} />);

    expect(screen.getByText("Görevler yükleniyor...")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Ürün sayfasını hazırla" })).not.toBeInTheDocument();
  });

  it("shows the existing empty state", () => {
    render(<TasksView {...createProps({ tasks: [] })} />);

    expect(screen.getByText("Henüz görev yok.")).toBeVisible();
    expect(
      screen.getByText("Sohbette “Bilsanpack için şu işi görev olarak ekle” diyebilirsin."),
    ).toBeVisible();
  });

  it("calls the refresh callback", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<TasksView {...createProps({ onRefresh })} />);

    await user.click(screen.getByRole("button", { name: "Yenile" }));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("marks the active task and only offers selection for inactive tasks", () => {
    render(<TasksView {...createProps()} />);

    const activeCard = screen.getByRole("heading", { name: "Ürün sayfasını hazırla" })
      .closest(".project-card");
    const inactiveCard = screen.getByRole("heading", { name: "Anahtar kelimeleri çıkar" })
      .closest(".project-card");

    expect(activeCard).not.toBeNull();
    expect(inactiveCard).not.toBeNull();
    expect(within(activeCard as HTMLElement).getByText("Aktif Görev")).toBeVisible();
    expect(within(activeCard as HTMLElement).queryByRole("button", { name: "Aktif Yap" })).not.toBeInTheDocument();
    expect(within(inactiveCard as HTMLElement).getByRole("button", { name: "Aktif Yap" })).toBeVisible();
  });

  it("selects the requested task through the delegated callback", async () => {
    const user = userEvent.setup();
    const onSelectTask = vi.fn();
    render(<TasksView {...createProps({ onSelectTask })} />);

    await user.click(screen.getByRole("button", { name: "Aktif Yap" }));

    expect(onSelectTask).toHaveBeenCalledOnce();
    expect(onSelectTask).toHaveBeenCalledWith("task-completed");
  });

  it("completes the requested open task and hides completion for completed tasks", async () => {
    const user = userEvent.setup();
    const onCompleteTask = vi.fn();
    render(<TasksView {...createProps({ onCompleteTask })} />);

    const activeCard = screen.getByRole("heading", { name: "Ürün sayfasını hazırla" })
      .closest(".project-card");
    const completedCard = screen.getByRole("heading", { name: "Anahtar kelimeleri çıkar" })
      .closest(".project-card");

    expect(activeCard).not.toBeNull();
    expect(completedCard).not.toBeNull();
    await user.click(within(activeCard as HTMLElement).getByRole("button", { name: "Tamamla" }));

    expect(onCompleteTask).toHaveBeenCalledOnce();
    expect(onCompleteTask).toHaveBeenCalledWith("task-active");
    expect(within(completedCard as HTMLElement).queryByRole("button", { name: "Tamamla" })).not.toBeInTheDocument();
  });

  it("deletes the requested task through the delegated callback", async () => {
    const user = userEvent.setup();
    const onDeleteTask = vi.fn();
    render(<TasksView {...createProps({ onDeleteTask })} />);

    const completedCard = screen.getByRole("heading", { name: "Anahtar kelimeleri çıkar" })
      .closest(".project-card");
    expect(completedCard).not.toBeNull();
    await user.click(within(completedCard as HTMLElement).getByRole("button", { name: "Sil" }));

    expect(onDeleteTask).toHaveBeenCalledOnce();
    expect(onDeleteTask).toHaveBeenCalledWith("task-completed");
  });

  it("does not start network, timer, notification or delegated task side effects", () => {
    const fetchMock = vi.fn();
    const intervalMock = vi.spyOn(window, "setInterval");
    const timeoutMock = vi.spyOn(window, "setTimeout");
    const notificationMock = vi.fn();
    const props = createProps();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("Notification", notificationMock);

    render(<TasksView {...props} />);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(intervalMock).not.toHaveBeenCalled();
    expect(timeoutMock).not.toHaveBeenCalled();
    expect(notificationMock).not.toHaveBeenCalled();
    expect(props.onRefresh).not.toHaveBeenCalled();
    expect(props.onSelectTask).not.toHaveBeenCalled();
    expect(props.onCompleteTask).not.toHaveBeenCalled();
    expect(props.onDeleteTask).not.toHaveBeenCalled();
  });
});
