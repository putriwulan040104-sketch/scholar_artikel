import type {
  ManagedPublication,
  PublicationExtractionStatus,
} from "@/api/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { PaginationControls } from "@/components/ui/pagination-controls";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Ellipsis,
  Eye,
  Pencil,
  Search,
  Trash2,
} from "lucide-react";

interface PublicationTableProps {
  publications: ManagedPublication[];
  loading: boolean;
  page: number;
  totalPages: number;
  itemsPerPage: number;
  query: string;
  statusFilter: string;
  categoryFilter: string;
  yearFilter: string;
  categoryOptions: Array<{ value: string; label: string }>;
  yearOptions: number[];
  hasUncategorizedPublications: boolean;
  hasPublicationsWithoutYear: boolean;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onCategoryFilterChange: (value: string) => void;
  onYearFilterChange: (value: string) => void;
  onPageChange: (page: number) => void;
  onDetail: (publication: ManagedPublication) => void;
  onEdit: (publication: ManagedPublication) => void;
  onDelete: (publication: ManagedPublication) => void;
}

const STATUS_LABELS: Record<PublicationExtractionStatus, string> = {
  complete: "Lengkap",
  partial: "Sebagian",
  empty: "Kosong",
};

function statusClass(status?: PublicationExtractionStatus) {
  if (status === "complete") return "border-emerald-200 bg-emerald-100 text-emerald-700";
  if (status === "partial") return "border-amber-200 bg-amber-100 text-amber-700";
  return "border-red-200 bg-red-100 text-red-700";
}

function formatAuthors(authors?: string[]) {
  return Array.isArray(authors) && authors.length ? authors.join(", ") : "-";
}

export default function PublicationTable({
  publications,
  loading,
  page,
  totalPages,
  itemsPerPage,
  query,
  statusFilter,
  categoryFilter,
  yearFilter,
  categoryOptions,
  yearOptions,
  hasUncategorizedPublications,
  hasPublicationsWithoutYear,
  onQueryChange,
  onStatusFilterChange,
  onCategoryFilterChange,
  onYearFilterChange,
  onPageChange,
  onDetail,
  onEdit,
  onDelete,
}: PublicationTableProps) {
  return (
    <Card className="w-full min-w-0 max-w-full">
      <CardContent className="min-w-0 space-y-4 p-3 sm:p-6">
      <div className="grid w-full grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-[190px_210px_160px_minmax(260px,1fr)]">
        <Select value={statusFilter} onValueChange={onStatusFilterChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Status ekstraksi" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua Status</SelectItem>
            <SelectItem value="complete">Lengkap</SelectItem>
            <SelectItem value="partial">Sebagian</SelectItem>
            <SelectItem value="empty">Kosong</SelectItem>
            <SelectItem value="no-references">Tanpa Referensi</SelectItem>
          </SelectContent>
        </Select>

        <Select value={categoryFilter} onValueChange={onCategoryFilterChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Kategori" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua Kategori</SelectItem>
            {categoryOptions.map((category) => (
              <SelectItem key={category.value} value={category.value}>
                {category.label}
              </SelectItem>
            ))}
            {hasUncategorizedPublications ? (
              <SelectItem value="uncategorized">Tanpa Kategori</SelectItem>
            ) : null}
          </SelectContent>
        </Select>

        <Select value={yearFilter} onValueChange={onYearFilterChange}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Tahun" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Semua Tahun</SelectItem>
            {yearOptions.map((year) => (
              <SelectItem key={year} value={String(year)}>
                {year}
              </SelectItem>
            ))}
            {hasPublicationsWithoutYear ? (
              <SelectItem value="unknown">Tanpa Tahun</SelectItem>
            ) : null}
          </SelectContent>
        </Select>

        <div className="relative w-full">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Cari judul, DOI, penulis, jurnal..."
            className="pl-9"
          />
        </div>
      </div>

      <div className="w-full min-w-0 max-w-full overflow-hidden rounded-xl border bg-background">
        <div className="w-full max-w-full overflow-x-auto">
          <Table className="min-w-[1380px]">
            <TableHeader>
              <TableRow className="bg-muted/60">
                <TableHead className="w-[70px] whitespace-nowrap">No</TableHead>
                <TableHead className="w-[320px] whitespace-nowrap">Publikasi</TableHead>
                <TableHead className="w-[220px] whitespace-nowrap">Penulis</TableHead>
                <TableHead className="w-[90px] whitespace-nowrap">Tahun</TableHead>
                <TableHead className="w-[190px] whitespace-nowrap">Jurnal / DOI</TableHead>
                <TableHead className="w-[180px] whitespace-nowrap">
                  Kategori Penelitian
                </TableHead>
                <TableHead className="w-[130px] whitespace-nowrap">Ekstraksi</TableHead>
                <TableHead className="w-[80px] whitespace-nowrap text-center">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    Mengambil data publikasi...
                  </TableCell>
                </TableRow>
              ) : publications.length ? (
                publications.map((publication, index) => (
                  <TableRow key={publication.id}>
                    <TableCell className="whitespace-nowrap">
                      {(page - 1) * itemsPerPage + index + 1}
                    </TableCell>
                    <TableCell className="max-w-[320px]">
                      <button
                        type="button"
                        onClick={() => onDetail(publication)}
                        className="block max-w-full text-left"
                      >
                        <span className="block truncate font-medium hover:text-primary">
                          {publication.title || "-"}
                        </span>
                      </button>
                    </TableCell>
                    <TableCell className="max-w-[220px] truncate whitespace-nowrap">
                      {formatAuthors(publication.authors)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{publication.year || "-"}</TableCell>
                    <TableCell className="max-w-[190px]">
                      <p className="truncate whitespace-nowrap text-sm">{publication.journal || "-"}</p>
                      <p className="truncate whitespace-nowrap text-xs text-muted-foreground">
                        {publication.doi || "DOI tidak tersedia"}
                      </p>
                    </TableCell>
                    <TableCell className="max-w-[180px] truncate whitespace-nowrap">
                      {publication.category || "Tanpa kategori"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <Badge
                        variant="outline"
                        className={statusClass(publication.extractionStatus)}
                      >
                        {STATUS_LABELS[publication.extractionStatus || "empty"]}
                      </Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-center">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Aksi untuk ${publication.title || "publikasi"}`}
                          >
                            <Ellipsis className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="min-w-44">
                          <DropdownMenuItem onSelect={() => onDetail(publication)}>
                            <Eye />
                            Lihat Detail
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => onEdit(publication)}>
                            <Pencil />
                            Edit Publikasi
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            variant="destructive"
                            onSelect={() => onDelete(publication)}
                          >
                            <Trash2 />
                            Hapus Publikasi
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                    Tidak ada publikasi yang cocok.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {totalPages > 1 ? (
        <PaginationControls
          currentPage={page}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      ) : null}
      </CardContent>
    </Card>
  );
}
