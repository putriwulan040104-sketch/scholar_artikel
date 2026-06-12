import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import type { ArticleRequest, ArticleRequestStatus } from "@/api/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

const ITEMS_PER_PAGE = 10;

const STATUS_OPTIONS: { value: ArticleRequestStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Diproses" },
  { value: "done", label: "Selesai" },
  { value: "rejected", label: "Ditolak" },
];

function formatDate(value?: string | null) {
  if (!value) return "-";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function normalizeStatus(status?: string | null): ArticleRequestStatus {
  const value = String(status || "pending").toLowerCase();

  if (value === "processing" || value === "done" || value === "rejected") {
    return value;
  }

  return "pending";
}

function getStatusLabel(status?: string | null) {
  const normalized = normalizeStatus(status);
  return (
    STATUS_OPTIONS.find((item) => item.value === normalized)?.label || "Pending"
  );
}

function getStatusClassName(status?: string | null) {
  const normalized = normalizeStatus(status);

  if (normalized === "done") {
    return "bg-emerald-100 text-emerald-700 border-emerald-200";
  }

  if (normalized === "rejected") {
    return "bg-red-100 text-red-700 border-red-200";
  }

  if (normalized === "processing") {
    return "bg-blue-100 text-blue-700 border-blue-200";
  }

  return "bg-yellow-100 text-yellow-700 border-yellow-200";
}

interface ArticleRequestTableProps {
  requests: ArticleRequest[];
  loading: boolean;
  updatingId: string | number | null;
  onStatusChange: (
    requestId: string | number,
    status: ArticleRequestStatus,
  ) => void;
}

export default function ArticleRequestTable({
  requests,
  loading,
  updatingId,
  onStatusChange,
}: ArticleRequestTableProps) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);

  const filteredRequests = useMemo(() => {
    const keyword = query.trim().toLowerCase();

    return requests.filter((request) => {
      const haystack = [
        request.nama,
        request.email,
        request.kataKunci,
        request.judulArtikel,
        request.keterangan,
        request.status,
        String(request.id),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchSearch = haystack.includes(keyword);
      const matchStatus =
        statusFilter === "all"
          ? true
          : normalizeStatus(request.status) === statusFilter;

      return matchSearch && matchStatus;
    });
  }, [query, requests, statusFilter]);

  const totalPages = Math.ceil(filteredRequests.length / ITEMS_PER_PAGE);
  const activePage = Math.min(page, Math.max(totalPages, 1));

  const paginatedRequests = useMemo(() => {
    const start = (activePage - 1) * ITEMS_PER_PAGE;
    return filteredRequests.slice(start, start + ITEMS_PER_PAGE);
  }, [activePage, filteredRequests]);

  const goToPage = (targetPage: number) => {
    if (targetPage < 1 || targetPage > totalPages) return;
    setPage(targetPage);
  };

  return (
    <Card className="w-full min-w-0 max-w-full">
      <CardContent className="min-w-0 space-y-4 p-3 sm:p-6">
        <div className="grid w-full grid-cols-2 gap-3 xl:max-w-3xl">
          <Select
            value={statusFilter}
            onValueChange={(value) => {
              setStatusFilter(value);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Filter status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua</SelectItem>
              {STATUS_OPTIONS.map((status) => (
                <SelectItem key={status.value} value={status.value}>
                  {status.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="relative w-full">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              placeholder="Cari request artikel..."
              className="pl-9"
            />
          </div>
        </div>

        <div className="w-full min-w-0 max-w-full overflow-hidden rounded-xl border bg-background">
          <div className="w-full max-w-full overflow-x-auto">
            <Table className="min-w-[1180px]">
              <TableHeader>
                <TableRow className="bg-muted/60">
                  <TableHead className="w-[70px] whitespace-nowrap">No</TableHead>
                  <TableHead className="w-[150px] whitespace-nowrap">Nama</TableHead>
                  <TableHead className="w-[220px] whitespace-nowrap">Email</TableHead>
                  <TableHead className="w-[220px] whitespace-nowrap">Judul Artikel</TableHead>
                  <TableHead className="w-[180px] whitespace-nowrap">Kata Kunci</TableHead>
                  <TableHead className="w-[240px] whitespace-nowrap">Keterangan</TableHead>
                  <TableHead className="w-[170px] whitespace-nowrap">Tanggal</TableHead>
                  <TableHead className="w-[130px] whitespace-nowrap">Status</TableHead>
                  <TableHead className="w-[160px] whitespace-nowrap">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell
                      colSpan={9}
                      className="h-24 text-center text-muted-foreground"
                    >
                      Mengambil data request artikel...
                    </TableCell>
                  </TableRow>
                ) : filteredRequests.length > 0 ? (
                  paginatedRequests.map((request, index) => (
                    <TableRow key={String(request.id)}>
                      <TableCell className="whitespace-nowrap">
                        {(activePage - 1) * ITEMS_PER_PAGE + index + 1}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {request.nama || "-"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {request.email || "-"}
                      </TableCell>
                      <TableCell className="max-w-[220px] truncate whitespace-nowrap">
                        {request.judulArtikel || "-"}
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate whitespace-nowrap">
                        {request.kataKunci || "-"}
                      </TableCell>
                      <TableCell className="max-w-[240px] truncate whitespace-nowrap">
                        {request.keterangan || "-"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {formatDate(request.createdAt)}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <Badge
                          variant="outline"
                          className={getStatusClassName(request.status)}
                        >
                          {getStatusLabel(request.status)}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <Select
                          value={normalizeStatus(request.status)}
                          disabled={updatingId === request.id}
                          onValueChange={(value) =>
                            onStatusChange(
                              request.id,
                              value as ArticleRequestStatus,
                            )
                          }
                        >
                          <SelectTrigger className="w-36">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {STATUS_OPTIONS.map((status) => (
                              <SelectItem
                                key={status.value}
                                value={status.value}
                              >
                                {status.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={9}
                      className="h-24 text-center text-muted-foreground"
                    >
                      Tidak ada request artikel yang cocok.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </div>

        {filteredRequests.length > 0 && totalPages > 1 ? (
          <PaginationControls
            currentPage={activePage}
            totalPages={totalPages}
            onPageChange={goToPage}
          />
        ) : null}
      </CardContent>
    </Card>
  );
}
