import { useCallback, useEffect, useMemo, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  deleteManagedPublication,
  getManagedPublications,
  updateManagedPublication,
  type ManagedPublication,
  type PublicationMutationPayload,
} from "@/api/api";
import { Button } from "@/components/ui/button";
import { PublicationStatCards } from "./cards";
import { PublicationDetailDialog } from "./detail-dialog";
import { PublicationDialog, type PublicationDialogMode } from "./dialog";
import PublicationTable from "./table";

const ITEMS_PER_PAGE = 20;

export default function SuperAdminPublicationsPage() {
  const [publications, setPublications] = useState<ManagedPublication[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [yearFilter, setYearFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<PublicationDialogMode>("edit");
  const [dialogLoading, setDialogLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedPublication, setSelectedPublication] =
    useState<ManagedPublication | null>(null);

  const loadPublications = useCallback(async () => {
    setLoading(true);
    setMessage("");

    const result = await getManagedPublications();
    if (result.status === "error") {
      setPublications([]);
      setMessage(result.message || "Gagal mengambil data publikasi.");
    } else {
      setPublications(
        [...(result.data || [])].sort(
          (left, right) => Number(left.id) - Number(right.id),
        ),
      );
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    void loadPublications();
  }, [loadPublications]);

  const filteredPublications = useMemo(() => {
    const keyword = query.trim().toLowerCase();

    return publications.filter((publication) => {
      const haystack = [
        publication.title,
        publication.doi,
        publication.journal,
        publication.year,
        ...(publication.authors || []),
        ...(publication.keywords || []),
        publication.category,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchesQuery = haystack.includes(keyword);
      const matchesStatus =
        statusFilter === "all"
          ? true
          : statusFilter === "no-references"
            ? Number(publication.referenceCount || 0) === 0
            : publication.extractionStatus === statusFilter;
      const normalizedCategory = String(publication.category || "")
        .trim()
        .toLowerCase();
      const matchesCategory =
        categoryFilter === "all"
          ? true
          : categoryFilter === "uncategorized"
            ? !normalizedCategory
            : normalizedCategory === categoryFilter;
      const normalizedYear =
        publication.year === null || publication.year === undefined
          ? ""
          : String(publication.year);
      const matchesYear =
        yearFilter === "all"
          ? true
          : yearFilter === "unknown"
            ? !normalizedYear
            : normalizedYear === yearFilter;

      return matchesQuery && matchesStatus && matchesCategory && matchesYear;
    });
  }, [categoryFilter, publications, query, statusFilter, yearFilter]);

  const categoryOptions = useMemo(() => {
    const options = new Map<string, string>();

    publications.forEach((publication) => {
      const label = String(publication.category || "").trim();
      const value = label.toLowerCase();
      if (label && !options.has(value)) options.set(value, label);
    });

    return Array.from(options, ([value, label]) => ({ value, label })).sort(
      (left, right) => left.label.localeCompare(right.label, "id"),
    );
  }, [publications]);

  const hasUncategorizedPublications = useMemo(
    () =>
      publications.some(
        (publication) => !String(publication.category || "").trim(),
      ),
    [publications],
  );

  const yearOptions = useMemo(
    () =>
      Array.from(
        new Set(
          publications
            .map((publication) => publication.year)
            .filter(
              (year): year is number =>
                year !== null &&
                year !== undefined &&
                Number.isFinite(Number(year)),
            )
            .map(Number),
        ),
      ).sort((left, right) => right - left),
    [publications],
  );

  const hasPublicationsWithoutYear = useMemo(
    () =>
      publications.some(
        (publication) =>
          publication.year === null || publication.year === undefined,
      ),
    [publications],
  );

  const totalPages = Math.max(
    1,
    Math.ceil(filteredPublications.length / ITEMS_PER_PAGE),
  );
  const activePage = Math.min(page, totalPages);

  const paginatedPublications = useMemo(() => {
    const start = (activePage - 1) * ITEMS_PER_PAGE;
    return filteredPublications.slice(start, start + ITEMS_PER_PAGE);
  }, [activePage, filteredPublications]);

  const completeCount = publications.filter(
    (item) => item.extractionStatus === "complete",
  ).length;
  const partialCount = publications.filter(
    (item) => item.extractionStatus === "partial",
  ).length;
  const withoutReferencesCount = publications.filter(
    (item) => Number(item.referenceCount || 0) === 0,
  ).length;

  const openDialog = (
    mode: PublicationDialogMode,
    publication: ManagedPublication,
  ) => {
    setSelectedPublication(publication);
    setDialogMode(mode);
    setDialogOpen(true);
  };

  const openDetail = (publication: ManagedPublication) => {
    setSelectedPublication(publication);
    setDetailOpen(true);
  };

  const handleDialogSubmit = async (payload?: PublicationMutationPayload) => {
    if (!selectedPublication) return;

    setDialogLoading(true);
    setMessage("");
    const result =
      dialogMode === "delete"
        ? await deleteManagedPublication(selectedPublication.id)
        : await updateManagedPublication(
            selectedPublication.id,
            payload as PublicationMutationPayload,
          );
    setDialogLoading(false);

    if (result.status === "error") {
      setMessage(result.message || "Operasi publikasi gagal.");
      return;
    }

    setDialogOpen(false);
    setSelectedPublication(null);
    setMessage(result.message || "Data publikasi berhasil diperbarui.");
    await loadPublications();
  };

  return (
    <div className="flex w-full min-w-0 max-w-full flex-1 flex-col gap-4 px-0 py-3 sm:gap-6 sm:px-4 sm:py-4 lg:px-6">
      <div className="flex justify-stretch sm:justify-end">
        <Button
          onClick={loadPublications}
          disabled={loading}
          className="w-full sm:w-fit"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Memuat..." : "Refresh Data"}
        </Button>
      </div>

      <PublicationStatCards
        total={publications.length}
        complete={completeCount}
        partial={partialCount}
        withoutReferences={withoutReferencesCount}
      />

      {message ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          {message}
        </div>
      ) : null}

      <PublicationTable
        publications={paginatedPublications}
        loading={loading}
        page={activePage}
        totalPages={totalPages}
        itemsPerPage={ITEMS_PER_PAGE}
        query={query}
        statusFilter={statusFilter}
        categoryFilter={categoryFilter}
        yearFilter={yearFilter}
        categoryOptions={categoryOptions}
        yearOptions={yearOptions}
        hasUncategorizedPublications={hasUncategorizedPublications}
        hasPublicationsWithoutYear={hasPublicationsWithoutYear}
        onQueryChange={(value) => {
          setQuery(value);
          setPage(1);
        }}
        onStatusFilterChange={(value) => {
          setStatusFilter(value);
          setPage(1);
        }}
        onCategoryFilterChange={(value) => {
          setCategoryFilter(value);
          setPage(1);
        }}
        onYearFilterChange={(value) => {
          setYearFilter(value);
          setPage(1);
        }}
        onPageChange={setPage}
        onDetail={openDetail}
        onEdit={(publication) => openDialog("edit", publication)}
        onDelete={(publication) => openDialog("delete", publication)}
      />

      <PublicationDetailDialog
        open={detailOpen}
        publication={selectedPublication}
        onOpenChange={(open) => {
          setDetailOpen(open);
          if (!open && !dialogOpen) setSelectedPublication(null);
        }}
      />

      <PublicationDialog
        open={dialogOpen}
        mode={dialogMode}
        publication={selectedPublication}
        loading={dialogLoading}
        onOpenChange={setDialogOpen}
        onSubmit={handleDialogSubmit}
      />
    </div>
  );
}
