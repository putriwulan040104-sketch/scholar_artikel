import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import {
  createUser,
  deleteUser,
  getUsers,
  updateUser,
  type ManagedUser,
} from "@/api/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { PaginationControls } from "@/components/ui/pagination-controls";
import {
  UserCrudDialog,
  type UserCrudMode,
  type UserCrudPayload,
} from "./crud";
import { UserStatCards } from "./cards";
import UserTable from "./table";

const ITEMS_PER_PAGE = 10;

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

export default function SuperAdminUsersPage() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);
  const [crudOpen, setCrudOpen] = useState(false);
  const [crudMode, setCrudMode] = useState<UserCrudMode>("create");
  const [crudLoading, setCrudLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState<ManagedUser | null>(null);

  const filteredUsers = useMemo(() => {
    const keyword = query.trim().toLowerCase();

    return users.filter((user) => {
      const haystack = [user.name, user.email, user.role, String(user.id)]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      const matchSearch = haystack.includes(keyword);
      const normalizedRole = normalizeRoleValue(user.role);
      const matchRole =
        roleFilter === "all"
          ? true
          : roleFilter === "super_admin"
            ? normalizedRole === "super_admin"
            : normalizedRole !== "super_admin";

      return matchSearch && matchRole;
    });
  }, [query, users, roleFilter]);

  const totalPages = Math.ceil(filteredUsers.length / ITEMS_PER_PAGE);

  const paginatedUsers = useMemo(() => {
    const start = (page - 1) * ITEMS_PER_PAGE;
    const end = start + ITEMS_PER_PAGE;

    return filteredUsers.slice(start, end);
  }, [filteredUsers, page]);

  const superAdminCount = useMemo(
    () => users.filter((user) => isSuperAdminRole(user.role)).length,
    [users],
  );
  const regularUserCount = useMemo(
    () => users.filter((user) => !isSuperAdminRole(user.role)).length,
    [users],
  );

  const goToPage = (targetPage: number) => {
    if (targetPage < 1 || targetPage > totalPages) return;

    setPage(targetPage);
  };

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setMessage("");

    const result = await getUsers();
    if (result.status === "error") {
      setUsers([]);
      setMessage(result.message || "Gagal mengambil data pengguna.");
      setLoading(false);
      return;
    }

    setUsers(result.data || []);
    setLoading(false);
  }, []);

  const openCreateDialog = () => {
    setSelectedUser(null);
    setCrudMode("create");
    setCrudOpen(true);
  };

  const openEditDialog = (user: ManagedUser) => {
    setSelectedUser(user);
    setCrudMode("edit");
    setCrudOpen(true);
  };

  const openDeleteDialog = (user: ManagedUser) => {
    setSelectedUser(user);
    setCrudMode("delete");
    setCrudOpen(true);
  };

  const handleCrudSubmit = async (payload: UserCrudPayload) => {
    setCrudLoading(true);
    setMessage("");

    const result =
      crudMode === "create"
        ? await createUser(payload)
        : crudMode === "edit" && selectedUser
          ? await updateUser(selectedUser.id, payload)
          : selectedUser
            ? await deleteUser(selectedUser.id)
            : {
                status: "error",
                message: "User belum dipilih.",
              };

    setCrudLoading(false);

    if (result.status === "error") {
      setMessage(result.message || "Operasi user gagal.");
      return;
    }

    setCrudOpen(false);
    setSelectedUser(null);
    setMessage(result.message || "Operasi user berhasil.");
    await loadUsers();
  };

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  useEffect(() => {
    setPage(1);
  }, [query, roleFilter]);

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-4 px-2 py-3 sm:gap-6 sm:px-4 sm:py-4 lg:px-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/super-admin/dashboard">Dashboard Super Admin</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Pengguna</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-col gap-2">
        <div className="flex justify-stretch gap-2 sm:justify-end">
          <Button onClick={loadUsers} disabled={loading} className="w-full sm:w-fit">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Memuat..." : "Refresh Data"}
          </Button>
        </div>
      </div>

      <UserStatCards
        totalUsers={users.length}
        regularUserCount={regularUserCount}
        superAdminCount={superAdminCount}
      />

      <Card className="min-w-0">
        <CardContent className="min-w-0 p-3 sm:p-6">
          {message ? (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {message}
            </div>
          ) : null}

          <UserTable
            users={paginatedUsers}
            loading={loading}
            page={page}
            itemsPerPage={ITEMS_PER_PAGE}
            hasFilteredUsers={filteredUsers.length > 0}
            query={query}
            roleFilter={roleFilter}
            onQueryChange={setQuery}
            onRoleFilterChange={setRoleFilter}
            onCreate={openCreateDialog}
            onEdit={openEditDialog}
            onDelete={openDeleteDialog}
          />

          {filteredUsers.length > 0 && totalPages > 1 ? (
            <PaginationControls
              currentPage={page}
              totalPages={totalPages}
              onPageChange={goToPage}
              className="mt-4"
            />
          ) : null}
        </CardContent>
      </Card>

      <UserCrudDialog
        open={crudOpen}
        mode={crudMode}
        user={selectedUser}
        loading={crudLoading}
        onOpenChange={setCrudOpen}
        onSubmit={handleCrudSubmit}
      />
    </div>
  );
}
