import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DataTable, IssueBadge, Pagination, type Column } from "./SeoUIComponents";

describe("SeoUIComponents", () => {
  it("renders the severity label and its public CSS classes", () => {
    render(<IssueBadge severity="P0" size="sm" />);

    expect(screen.getByText("P0")).toHaveClass("issue-badge", "issue-badge-p0", "issue-badge-sm");
  });

  it("keeps a real zero visible while leaving unavailable metrics blank", () => {
    type MetricRow = { id: string; value: number | null | undefined };
    const columns: Column<MetricRow>[] = [{ key: "value", header: "Değer" }];

    render(
      <DataTable
        data={[
          { id: "zero", value: 0 },
          { id: "null", value: null },
          { id: "missing", value: undefined },
        ]}
        columns={columns}
        keyExtractor={(row) => row.id}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    expect(within(rows[0]).getByText("0")).toBeVisible();
    expect(within(rows[1]).getByRole("cell")).toBeEmptyDOMElement();
    expect(within(rows[2]).getByRole("cell")).toBeEmptyDOMElement();
    expect(screen.getAllByText("0")).toHaveLength(1);
  });

  it("renders the supplied no-data explanation", () => {
    render(
      <DataTable<{ id: string }>
        data={[]}
        columns={[]}
        keyExtractor={(row) => row.id}
        emptyMessage="Bu metrik için veri mevcut değil."
      />,
    );

    expect(screen.getByText("Bu metrik için veri mevcut değil.")).toBeVisible();
  });

  it("disables previous navigation on the first page", () => {
    renderPagination({ currentPage: 1 });

    expect(screen.getByRole("button", { name: "İlk sayfa" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Önceki sayfa" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Sonraki sayfa" })).toBeEnabled();
  });

  it("disables next navigation on the last page", () => {
    renderPagination({ currentPage: 3 });

    expect(screen.getByRole("button", { name: "Sonraki sayfa" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Son sayfa" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Önceki sayfa" })).toBeEnabled();
  });

  it("calls pagination callbacks with the requested page and page size", async () => {
    const user = userEvent.setup();
    const onPageChange = vi.fn();
    const onPageSizeChange = vi.fn();
    renderPagination({ currentPage: 2, onPageChange, onPageSizeChange });

    await user.click(screen.getByRole("button", { name: "Önceki sayfa" }));
    await user.click(screen.getByRole("button", { name: "Sonraki sayfa" }));
    await user.selectOptions(screen.getByRole("combobox"), "50");

    expect(onPageChange).toHaveBeenNthCalledWith(1, 1);
    expect(onPageChange).toHaveBeenNthCalledWith(2, 3);
    expect(onPageSizeChange).toHaveBeenCalledWith(50);
  });
});

function renderPagination({
  currentPage,
  onPageChange = vi.fn(),
  onPageSizeChange = vi.fn(),
}: {
  currentPage: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
}) {
  return render(
    <Pagination
      currentPage={currentPage}
      totalPages={3}
      pageSize={20}
      totalItems={55}
      onPageChange={onPageChange}
      onPageSizeChange={onPageSizeChange}
    />,
  );
}
