import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SeoProjectService } from "../../services/seoProjectService";
import type { SeoProject } from "../../types/seo";
import { SeoProjectSelector } from "./SeoProjectSelector";

vi.mock("../../services/seoProjectService", () => ({
  SeoProjectService: {
    listProjects: vi.fn(),
  },
}));

const projects: SeoProject[] = [
  makeProject({ id: "project-1", name: "Vex", domain: "vex.test", last_score: 87 }),
  makeProject({ id: "project-2", name: "Docs", domain: "docs.vex.test", last_score: null }),
];

describe("SeoProjectSelector", () => {
  beforeEach(() => {
    vi.mocked(SeoProjectService.listProjects).mockResolvedValue(projects);
  });

  it("renders the project list", async () => {
    render(<SeoProjectSelector />);

    expect(await screen.findByRole("option", { name: "Vex (vex.test)" })).toBeVisible();
    expect(screen.getByRole("option", { name: "Docs (docs.vex.test)" })).toBeVisible();
  });

  it("shows the selected project and its details", async () => {
    render(<SeoProjectSelector value="project-1" />);

    await screen.findByText("Vex", { selector: ".seo-project-name" });
    const selector = screen.getByRole("combobox");
    expect(selector).toHaveValue("project-1");
    expect(screen.getByText("Vex", { selector: ".seo-project-name" })).toBeVisible();
    expect(screen.getByText(/Son skor:/)).toHaveTextContent("Son skor: 87/100");
  });

  it("reports the selected project ID when the user changes selection", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SeoProjectSelector value="project-1" onChange={onChange} />);

    await screen.findByRole("option", { name: "Docs (docs.vex.test)" });
    await user.selectOptions(screen.getByRole("combobox"), "project-2");

    expect(onChange).toHaveBeenCalledWith("project-2");
  });

  it("keeps the current empty-list contract", async () => {
    vi.mocked(SeoProjectService.listProjects).mockResolvedValue([]);
    render(<SeoProjectSelector emptyLabel="SEO projesi seç" />);

    const selector = await screen.findByRole("combobox");
    expect(screen.getByRole("option", { name: "SEO projesi seç" })).toBeVisible();
    expect(selector).toHaveValue("");
    expect(screen.getAllByRole("option")).toHaveLength(1);
  });

  it("shows the loading option while projects are pending", () => {
    vi.mocked(SeoProjectService.listProjects).mockReturnValue(new Promise(() => undefined));
    render(<SeoProjectSelector />);

    expect(screen.getByRole("combobox")).toBeEnabled();
    expect(screen.getByRole("option", { name: "Yükleniyor..." })).toBeVisible();
  });

  it("preserves the visible error state when loading fails", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.mocked(SeoProjectService.listProjects).mockRejectedValue(new Error("offline"));
    render(<SeoProjectSelector />);

    expect(await screen.findByText("Projeler yüklenemedi")).toBeVisible();
    expect(screen.getByRole("option", { name: "Tüm projeler" })).toBeVisible();
  });
});

function makeProject(overrides: Partial<SeoProject>): SeoProject {
  return {
    id: "project",
    name: "Project",
    domain: "project.test",
    description: "",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    settings: { max_pages: 100, max_depth: 3 },
    audit_history: [],
    active_audit_id: null,
    last_audit_at: null,
    last_score: null,
    ...overrides,
  };
}
