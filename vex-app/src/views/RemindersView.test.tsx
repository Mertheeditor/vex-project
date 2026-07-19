import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { RemindersView } from "./RemindersView";

const reminders = [
  {
    id: "reminder-1",
    title: "Durum toplantısına katıl",
    remind_at: "2026-07-18T15:30:00",
    project_id: "project-1",
    task_id: "task-1",
    status: "active",
    notified: false,
    notes: ["Gündemi hazırla"],
  },
  {
    id: "reminder-2",
    title: "Su iç",
    remind_at: "2026-07-18T16:00:00",
    project_id: "",
    task_id: "",
    status: "completed",
    notified: true,
    notes: [],
  },
];

function createProps(
  overrides: Partial<ComponentProps<typeof RemindersView>> = {},
): ComponentProps<typeof RemindersView> {
  return {
    reminders,
    isLoading: false,
    onRefresh: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  };
}

describe("RemindersView", () => {
  it("renders the heading and supplied reminder list", () => {
    render(<RemindersView {...createProps()} />);

    expect(screen.getByRole("heading", { name: "Hatırlatmalar" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Durum toplantısına katıl" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Su iç" })).toBeVisible();
  });

  it("shows reminder time, status, notification and project information", () => {
    render(<RemindersView {...createProps()} />);

    expect(screen.getByText("2026-07-18T15:30:00")).toBeVisible();
    expect(screen.getByText("active")).toBeVisible();
    expect(screen.getByText("bekliyor")).toBeVisible();
    expect(screen.getByText("Proje: project-1")).toBeVisible();
    expect(screen.getByText("Görev: task-1")).toBeVisible();
    expect(screen.getByText("Gündemi hazırla")).toBeVisible();
    expect(screen.getByText("completed")).toBeVisible();
    expect(screen.getByText("bildirildi")).toBeVisible();
    expect(screen.getByText("Genel hatırlatma")).toBeVisible();
    expect(screen.getByText("Görev: Bağlı görev yok")).toBeVisible();
  });

  it("shows the existing loading state and preserves available actions", () => {
    render(<RemindersView {...createProps({ isLoading: true })} />);

    expect(screen.getByText("Hatırlatmalar yükleniyor...")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Sil" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yenile" })).toBeEnabled();
  });

  it("shows the existing empty state", () => {
    render(<RemindersView {...createProps({ reminders: [] })} />);

    expect(screen.getByText("Henüz hatırlatma yok.")).toBeVisible();
    expect(
      screen.getByText(
        "“30 dakika sonra beni uyar” veya “saat 18:00’de bunu hatırlat” diyebilirsin.",
      ),
    ).toBeVisible();
  });

  it("calls the refresh callback from the refresh action", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<RemindersView {...createProps({ onRefresh })} />);

    await user.click(screen.getByRole("button", { name: "Yenile" }));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("deletes the requested reminder through the delegated callback", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<RemindersView {...createProps({ onDelete })} />);

    const reminderCard = screen.getByRole("heading", { name: "Su iç" })
      .closest(".project-card");
    expect(reminderCard).not.toBeNull();
    await user.click(
      within(reminderCard as HTMLElement).getByRole("button", { name: "Sil" }),
    );

    expect(onDelete).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledWith("reminder-2");
  });

  it("does not start network, timer or notification side effects", () => {
    const fetchMock = vi.fn();
    const intervalMock = vi.spyOn(window, "setInterval");
    const timeoutMock = vi.spyOn(window, "setTimeout");
    const notificationMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("Notification", notificationMock);

    render(<RemindersView {...createProps()} />);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(intervalMock).not.toHaveBeenCalled();
    expect(timeoutMock).not.toHaveBeenCalled();
    expect(notificationMock).not.toHaveBeenCalled();
  });
});
