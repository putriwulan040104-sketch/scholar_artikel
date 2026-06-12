import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  className?: string;
}

function buildPageItems(
  currentPage: number,
  totalPages: number,
): Array<number | "ellipsis"> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items: Array<number | "ellipsis"> = [1];
  const start = Math.max(2, currentPage - 1);
  const end = Math.min(totalPages - 1, currentPage + 1);

  if (start > 2) items.push("ellipsis");
  for (let page = start; page <= end; page += 1) items.push(page);
  if (end < totalPages - 1) items.push("ellipsis");

  items.push(totalPages);
  return items;
}

export function PaginationControls({
  currentPage,
  totalPages,
  onPageChange,
  className = "",
}: PaginationControlsProps) {
  if (totalPages <= 1) return null;

  const activePage = Math.min(Math.max(currentPage, 1), totalPages);
  const pageItems = buildPageItems(activePage, totalPages);

  return (
    <div
      className={`flex flex-wrap items-center justify-center gap-2 ${className}`}
    >
      <button
        type="button"
        onClick={() => onPageChange(activePage - 1)}
        disabled={activePage <= 1}
        aria-label="Halaman sebelumnya"
        className="inline-flex h-8 w-8 items-center justify-center rounded-md border bg-background transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>

      {pageItems.map((item, index) =>
        item === "ellipsis" ? (
          <span
            key={`ellipsis-${index}`}
            className="px-1 text-sm text-muted-foreground"
          >
            ...
          </span>
        ) : (
          <button
            key={item}
            type="button"
            onClick={() => onPageChange(item)}
            aria-label={`Buka halaman ${item}`}
            aria-current={activePage === item ? "page" : undefined}
            className={`inline-flex h-8 min-w-8 items-center justify-center rounded-md border px-2 text-sm transition-colors ${
              activePage === item
                ? "border-primary bg-primary text-primary-foreground"
                : "bg-background hover:bg-muted"
            }`}
          >
            {item}
          </button>
        ),
      )}

      <button
        type="button"
        onClick={() => onPageChange(activePage + 1)}
        disabled={activePage >= totalPages}
        aria-label="Halaman berikutnya"
        className="inline-flex h-8 w-8 items-center justify-center rounded-md border bg-background transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
