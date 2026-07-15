import type { ActivityLog } from "@/api/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
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
import { Ellipsis, Eye, Search } from "lucide-react";

export const ACTION_OPTIONS = [
  ["update_profile", "Ubah Profil"],
  ["create_user", "Tambah Pengguna"],
  ["update_user", "Ubah Pengguna"],
  ["delete_user", "Hapus Pengguna"],
  ["update_request_status", "Ubah Status Request"],
  ["update_publication", "Ubah Publikasi"],
  ["delete_publication", "Hapus Publikasi"],
] as const;

const ACTION_LABELS = Object.fromEntries(ACTION_OPTIONS);

const ENTITY_OPTIONS = [
  ["user", "Pengguna"],
  ["publication", "Publikasi"],
  ["article_request", "Request Artikel"],
] as const;

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

interface ActivityLogTableProps {
  logs: ActivityLog[];
  loading: boolean;
  page: number;
  totalPages: number;
  query: string;
  actionFilter: string;
  entityFilter: string;
  statusFilter: string;
  activityDate: string;
  onQueryChange: (value: string) => void;
  onActionFilterChange: (value: string) => void;
  onEntityFilterChange: (value: string) => void;
  onStatusFilterChange: (value: string) => void;
  onActivityDateChange: (value: string) => void;
  onPageChange: (page: number) => void;
  onDetail: (log: ActivityLog) => void;
}

export default function ActivityLogTable({
  logs,
  loading,
  page,
  totalPages,
  query,
  actionFilter,
  entityFilter,
  statusFilter,
  activityDate,
  onQueryChange,
  onActionFilterChange,
  onEntityFilterChange,
  onStatusFilterChange,
  onActivityDateChange,
  onPageChange,
  onDetail,
}: ActivityLogTableProps) {
  return (
    <Card className="w-full min-w-0 max-w-full">
      <CardContent className="min-w-0 space-y-4 p-3 sm:p-6">
        <div className="grid grid-cols-2 gap-2 xl:grid-cols-6">
          <Select value={actionFilter} onValueChange={onActionFilterChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Aktivitas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Aktivitas</SelectItem>
              {ACTION_OPTIONS.map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={entityFilter} onValueChange={onEntityFilterChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Jenis objek" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Objek</SelectItem>
              {ENTITY_OPTIONS.map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua Status</SelectItem>
              <SelectItem value="success">Berhasil</SelectItem>
              <SelectItem value="failed">Gagal</SelectItem>
            </SelectContent>
          </Select>

          <Input
            type="date"
            value={activityDate}
            onChange={(event) => onActivityDateChange(event.target.value)}
            aria-label="Tanggal aktivitas"
            title="Filter tanggal aktivitas"
          />

          <div className="relative w-full col-span-2 xl:col-span-2">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Cari role, aktivitas, deskripsi..."
              className="pl-9"
            />
          </div>
        </div>

        <div className="w-full min-w-0 overflow-hidden rounded-xl border bg-background">
          <div className="w-full overflow-x-auto">
            <Table className="min-w-[1180px]">
              <TableHeader>
                <TableRow className="bg-muted/60">
                  <TableHead className="w-[65px] whitespace-nowrap">No</TableHead>
                  <TableHead className="w-[180px] whitespace-nowrap">Waktu</TableHead>
                  <TableHead className="w-[180px] whitespace-nowrap">Role</TableHead>
                  <TableHead className="w-[190px] whitespace-nowrap">Aktivitas</TableHead>
                  <TableHead className="w-[160px] whitespace-nowrap">Objek</TableHead>
                  <TableHead className="w-[300px] whitespace-nowrap">Deskripsi</TableHead>
                  <TableHead className="w-[120px] whitespace-nowrap">Status</TableHead>
                  <TableHead className="w-[130px] whitespace-nowrap">IP</TableHead>
                  <TableHead className="w-[70px] text-center">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                      Mengambil log aktivitas...
                    </TableCell>
                  </TableRow>
                ) : logs.length ? (
                  logs.map((log, index) => (
                    <TableRow key={log.id}>
                      <TableCell>{(page - 1) * 10 + index + 1}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {formatDate(log.createdAt)}
                      </TableCell>
                      <TableCell className="max-w-[180px] truncate whitespace-nowrap">
                        {log.userName || "System"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {ACTION_LABELS[log.action || ""] || log.action || "-"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {log.entityType || "-"}
                        {log.entityId ? ` #${log.entityId}` : ""}
                      </TableCell>
                      <TableCell className="max-w-[300px] truncate whitespace-nowrap">
                        {log.description || "-"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        <Badge
                          variant="outline"
                          className={
                            log.status === "failed"
                              ? "border-red-200 bg-red-100 text-red-700"
                              : "border-emerald-200 bg-emerald-100 text-emerald-700"
                          }
                        >
                          {log.status === "failed" ? "Gagal" : "Berhasil"}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {log.ipAddress || "-"}
                      </TableCell>
                      <TableCell className="text-center">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm" aria-label="Aksi log">
                              <Ellipsis className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onSelect={() => onDetail(log)}>
                              <Eye />
                              Lihat Detail
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={9} className="h-24 text-center text-muted-foreground">
                      Belum ada log aktivitas yang sesuai.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </div>

        <PaginationControls
          currentPage={page}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      </CardContent>
    </Card>
  );
}
