import type { ManagedUser } from "@/api/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Pencil, Plus, Search, Trash2 } from "lucide-react";

interface UserTableProps {
  users: ManagedUser[];
  loading: boolean;
  page: number;
  itemsPerPage: number;
  hasFilteredUsers: boolean;
  query: string;
  roleFilter: string;

  onQueryChange: (query: string) => void;
  onRoleFilterChange: (role: string) => void;
  onCreate: () => void;
  onEdit: (user: ManagedUser) => void;
  onDelete: (user: ManagedUser) => void;
}

function normalizeRoleValue(role?: string | null) {
  return String(role || "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}

function isSuperAdminRole(role?: string | null) {
  return normalizeRoleValue(role) === "super_admin";
}

function normalizeRoleLabel(role?: string | null) {
  return (role || "user")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatUserDate(value?: string | null) {
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

export default function UserTable({
  users,
  loading,
  page,
  itemsPerPage,
  hasFilteredUsers,
  query,
  roleFilter,
  onQueryChange,
  onRoleFilterChange,
  onCreate,
  onEdit,
  onDelete,
}: UserTableProps) {
  return (
    <div className="min-w-0 space-y-4">
      <div className="flex flex-col justify-between gap-3 xl:flex-row xl:items-center">
        <div className="grid w-full grid-cols-2 gap-3 xl:max-w-3xl">
          <Select value={roleFilter} onValueChange={onRoleFilterChange}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Filter role" />
            </SelectTrigger>

            <SelectContent>
              <SelectItem value="all">Semua</SelectItem>
              <SelectItem value="user">User</SelectItem>
              <SelectItem value="super_admin">Super Admin</SelectItem>
            </SelectContent>
          </Select>

          <div className="relative w-full">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Cari nama, email, role..."
              className="pl-9"
            />
          </div>
        </div>

        <Button onClick={onCreate} className="w-full md:w-fit">
          <Plus className="h-4 w-4" />
          Tambah User
        </Button>
      </div>

      <div className="min-w-0 overflow-hidden rounded-xl border bg-background">
        <div className="w-full max-w-full overflow-x-auto">
          <Table className="min-w-[920px]">
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="w-[70px] whitespace-nowrap">No</TableHead>
                <TableHead className="w-[190px] whitespace-nowrap">Nama</TableHead>
                <TableHead className="w-[260px] whitespace-nowrap">Email</TableHead>
                <TableHead className="w-[150px] whitespace-nowrap">Role</TableHead>
                <TableHead className="w-[180px] whitespace-nowrap">Dibuat</TableHead>
                <TableHead className="w-[170px] whitespace-nowrap text-center">
                  Aksi
                </TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-28 text-center text-muted-foreground"
                  >
                    Mengambil data pengguna...
                  </TableCell>
                </TableRow>
              ) : hasFilteredUsers ? (
                users.map((user, index) => (
                  <TableRow key={String(user.id)} className="hover:bg-muted/40">
                    <TableCell className="whitespace-nowrap font-medium text-muted-foreground">
                      {(page - 1) * itemsPerPage + index + 1}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <div className="space-y-1">
                        <div className="font-medium">{user.name || "-"}</div>
                        <div className="text-xs text-muted-foreground sm:hidden">
                          {user.email || "-"}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      {user.email || "-"}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <Badge
                        variant={
                          isSuperAdminRole(user.role) ? "default" : "secondary"
                        }
                        className="capitalize"
                      >
                        {normalizeRoleLabel(user.role)}
                      </Badge>
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-muted-foreground">
                      {formatUserDate(user.createdAt)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-8 px-2 sm:px-3"
                          onClick={() => onEdit(user)}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only sm:not-sr-only sm:ml-1">Edit</span>
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="h-8 border-red-200 px-2 text-red-600 hover:bg-red-50 hover:text-red-700 sm:px-3"
                          onClick={() => onDelete(user)}
                        >
                          <Trash2 className="h-4 w-4" />
                          <span className="sr-only sm:not-sr-only sm:ml-1">Hapus</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="h-28 text-center text-muted-foreground"
                  >
                    Tidak ada pengguna ditemukan.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
