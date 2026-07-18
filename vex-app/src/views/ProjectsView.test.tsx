import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";
import { ProjectsView } from "./ProjectsView";

const projects = [
  {
    id: "global-store",
    name: "Global Mağaza",
    type: "E-ticaret",
    status: "aktif",
    description: "Yeni mağaza deneyimi",
    main_goals: ["Global site yapısını kur"],
    notes: ["Modern ve premium tasarım"],
  },
  {
    id: "content-hub",
    name: "İçerik Merkezi",
    type: "İçerik",
    status: "planlama",
    description: "İçerikleri tek yerde yönet",
    main_goals: ["Yayın akışını sadeleştir"],
    notes: ["SEO öncelikli"],
  },
];

function createProps(
  overrides: Partial<ComponentProps<typeof ProjectsView>> = {},
): ComponentProps<typeof ProjectsView> {
  return {
    projects,
    activeProjectId: "global-store",
    isProjectsLoading: false,
    isCreatingProject: false,
    projectForm: {
      isOpen: false,
      name: "",
      type: "",
      description: "",
      goals: "",
      notes: "",
      toggle: vi.fn(),
      setName: vi.fn(),
      setType: vi.fn(),
      setDescription: vi.fn(),
      setGoals: vi.fn(),
      setNotes: vi.fn(),
    },
    onRefresh: vi.fn(),
    onSelectProject: vi.fn(),
    onCreateProject: vi.fn(),
    onDeleteProject: vi.fn(),
    ...overrides,
  };
}

describe("ProjectsView", () => {
  it("renders the projects heading and supplied project list without a network call", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(<ProjectsView {...createProps()} />);

    expect(screen.getByRole("heading", { name: "Vex Projeleri" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Global Mağaza" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "İçerik Merkezi" })).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("preserves the loading state", () => {
    render(<ProjectsView {...createProps({ isProjectsLoading: true })} />);

    expect(screen.getByText("Projeler yükleniyor...")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Global Mağaza" })).not.toBeInTheDocument();
  });

  it("shows the existing empty state", () => {
    render(<ProjectsView {...createProps({ projects: [] })} />);

    expect(screen.getByText("Henüz proje yok.")).toBeVisible();
    expect(
      screen.getByText("Backend’de projects.json dosyasını kontrol edelim."),
    ).toBeVisible();
  });

  it("marks the active project as selected", () => {
    render(<ProjectsView {...createProps()} />);

    const activeCard = screen.getByRole("heading", { name: "Global Mağaza" })
      .closest(".project-card");
    const inactiveCard = screen.getByRole("heading", { name: "İçerik Merkezi" })
      .closest(".project-card");

    expect(activeCard).not.toBeNull();
    expect(inactiveCard).not.toBeNull();
    expect(within(activeCard as HTMLElement).getByText("Aktif Proje")).toBeVisible();
    expect(
      within(activeCard as HTMLElement).queryByRole("button", { name: "Aktif Yap" }),
    ).not.toBeInTheDocument();
    expect(
      within(inactiveCard as HTMLElement).getByRole("button", { name: "Aktif Yap" }),
    ).toBeVisible();
  });

  it("selects the requested project through the delegated callback", async () => {
    const user = userEvent.setup();
    const onSelectProject = vi.fn();
    render(<ProjectsView {...createProps({ onSelectProject })} />);

    await user.click(screen.getByRole("button", { name: "Aktif Yap" }));

    expect(onSelectProject).toHaveBeenCalledOnce();
    expect(onSelectProject).toHaveBeenCalledWith("content-hub");
  });

  it("shows all existing new-project fields", () => {
    render(
      <ProjectsView
        {...createProps({
          projectForm: {
            ...createProps().projectForm,
            isOpen: true,
          },
        })}
      />,
    );

    expect(screen.getByLabelText("Proje adı")).toBeVisible();
    expect(screen.getByLabelText("Proje tipi")).toBeVisible();
    expect(screen.getByLabelText("Açıklama")).toBeVisible();
    expect(screen.getByLabelText("Ana hedefler")).toBeVisible();
    expect(screen.getByLabelText("Notlar")).toBeVisible();
  });

  it("submits the existing payload through the delegated callback", async () => {
    const user = userEvent.setup();
    const onCreateProject = vi.fn();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(
      <ProjectsView
        {...createProps({
          onCreateProject,
          projectForm: {
            ...createProps().projectForm,
            isOpen: true,
            name: "  Yeni Şube  ",
            type: "  E-ticaret  ",
            description: "  Bölgesel mağaza  ",
            goals: " İlk hedef \n\n İkinci hedef ",
            notes: " İlk not \n İkinci not ",
          },
        })}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Projeyi Kaydet" }));

    expect(onCreateProject).toHaveBeenCalledOnce();
    expect(onCreateProject).toHaveBeenCalledWith(
      {
        id: "yeni-sube",
        name: "Yeni Şube",
        type: "E-ticaret",
        status: "aktif",
        description: "Bölgesel mağaza",
        main_goals: ["İlk hedef", "İkinci hedef"],
        notes: ["İlk not", "İkinci not"],
      },
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("keeps the create action disabled while submitting", async () => {
    const user = userEvent.setup();
    const onCreateProject = vi.fn();
    render(
      <ProjectsView
        {...createProps({
          isCreatingProject: true,
          onCreateProject,
          projectForm: {
            ...createProps().projectForm,
            isOpen: true,
          },
        })}
      />,
    );

    const submitButton = screen.getByRole("button", { name: "Kaydediliyor..." });
    expect(submitButton).toBeDisabled();
    await user.click(submitButton);
    expect(onCreateProject).not.toHaveBeenCalled();
  });

  it("deletes the requested project through the delegated callback", async () => {
    const user = userEvent.setup();
    const onDeleteProject = vi.fn();
    render(<ProjectsView {...createProps({ onDeleteProject })} />);

    const contentCard = screen.getByRole("heading", { name: "İçerik Merkezi" })
      .closest(".project-card");
    expect(contentCard).not.toBeNull();
    await user.click(
      within(contentCard as HTMLElement).getByRole("button", { name: "Sil" }),
    );

    expect(onDeleteProject).toHaveBeenCalledOnce();
    expect(onDeleteProject).toHaveBeenCalledWith("content-hub");
  });
});
