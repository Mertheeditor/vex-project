import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { OutputsView } from "./OutputsView";

const outputs = [
  {
    id: "output-1",
    title: "Yayın planı",
    project_id: "project-1",
    task_id: "task-1",
    output_type: "document",
    content: "İlk çıktı içeriği",
    status: "draft",
    notes: ["Editör inceleyecek"],
  },
  {
    id: "output-2",
    title: "Genel özet",
    project_id: "",
    task_id: "",
    output_type: "summary",
    content: "İkinci çıktı içeriği",
    status: "ready",
    notes: [],
  },
];

function createProps(
  overrides: Partial<ComponentProps<typeof OutputsView>> = {},
): ComponentProps<typeof OutputsView> {
  return {
    outputs,
    isLoading: false,
    onRefresh: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  };
}

describe("OutputsView", () => {
  it("renders the heading and supplied output list without a network call", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<OutputsView {...createProps()} />);

    expect(screen.getByRole("heading", { name: "Kaydedilen Çıktılar" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Yayın planı" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Genel özet" })).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows each output type and status", () => {
    render(<OutputsView {...createProps()} />);

    expect(screen.getByText("document")).toBeVisible();
    expect(screen.getByText("draft")).toBeVisible();
    expect(screen.getByText("summary")).toBeVisible();
    expect(screen.getByText("ready")).toBeVisible();
  });

  it("preserves output fields and their fallback labels", () => {
    render(<OutputsView {...createProps()} />);

    expect(screen.getByText("Proje: project-1")).toBeVisible();
    expect(screen.getByText("task-1")).toBeVisible();
    expect(screen.getByText("İlk çıktı içeriği")).toBeVisible();
    expect(screen.getByText("Editör inceleyecek")).toBeVisible();
    expect(screen.getByText("Genel çıktı")).toBeVisible();
    expect(screen.getByText("Bağlı görev yok")).toBeVisible();
  });

  it("shows the existing loading state and hides output actions", () => {
    render(<OutputsView {...createProps({ isLoading: true })} />);

    expect(screen.getByText("Çıktılar yükleniyor...")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Sil" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Yenile" })).toBeEnabled();
  });

  it("shows the existing empty state", () => {
    render(<OutputsView {...createProps({ outputs: [] })} />);

    expect(screen.getByText("Henüz kayıtlı çıktı yok.")).toBeVisible();
    expect(
      screen.getByText("Vex bir metin ürettikten sonra “bunu kaydet” diyebilirsin."),
    ).toBeVisible();
  });

  it("calls the refresh callback from the refresh action", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<OutputsView {...createProps({ onRefresh })} />);

    await user.click(screen.getByRole("button", { name: "Yenile" }));

    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("deletes the requested output through the delegated callback", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();
    render(<OutputsView {...createProps({ onDelete })} />);

    const outputCard = screen.getByRole("heading", { name: "Genel özet" })
      .closest(".project-card");
    expect(outputCard).not.toBeNull();
    await user.click(
      within(outputCard as HTMLElement).getByRole("button", { name: "Sil" }),
    );

    expect(onDelete).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledWith("output-2");
  });
});
