import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  BookOpenText,
  RefreshCw,
  UsersRound,
} from "lucide-react";
import {
  getActivityLogs,
  getManagedPublications,
  getUsers,
  type ManagedPublication,
  type ManagedUser,
} from "@/api/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PublicationCharts } from "./charts";

function normalizeRole(role?: string | null) {
  return String(role || "user")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";

  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

function timestamp(value?: string | null) {
  if (!value) return 0;
  const date = new Date(value).getTime();
  return Number.isNaN(date) ? 0 : date;
}

export default function SuperAdminDashboardPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [publications, setPublications] = useState<ManagedPublication[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setMessage("");

    const [usersResult, publicationsResult, activityResult] = await Promise.all([
      getUsers(),
      getManagedPublications(),
      getActivityLogs({ page: 1, pageSize: 1 }),
    ]);

    setUsers(usersResult.status === "success" ? usersResult.data || [] : []);
    setPublications(
      publicationsResult.status === "success" ? publicationsResult.data || [] : [],
    );
    setActivityTotal(
      activityResult.status === "success" ? activityResult.total || 0 : 0,
    );

    const errors = [usersResult, publicationsResult, activityResult]
      .filter((result) => result.status === "error")
      .map((result) => result.message)
      .filter(Boolean);

    if (errors.length > 0) {
      setMessage(errors.join(" "));
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadDashboard();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadDashboard]);

  const regularUsers = useMemo(
    () => users.filter((user) => normalizeRole(user.role) === "user"),
    [users],
  );

  const latestUsers = useMemo(
    () =>
      [...regularUsers]
        .sort((left, right) => timestamp(right.createdAt) - timestamp(left.createdAt))
        .slice(0, 6),
    [regularUsers],
  );

  const latestPublications = useMemo(
    () =>
      [...publications]
        .sort(
          (left, right) =>
            timestamp(right.updatedAt) - timestamp(left.updatedAt) ||
            Number(right.id) - Number(left.id),
        )
        .slice(0, 6),
    [publications],
  );

  const statCards = [
    {
      label: "Total User",
      value: regularUsers.length,
      icon: UsersRound,
      color: "text-violet-600",
      background: "bg-violet-100",
    },
    {
      label: "Total Publikasi",
      value: publications.length,
      icon: BookOpenText,
      color: "text-slate-700",
      background: "bg-slate-100",
    },
    {
      label: "Total Log Aktivitas",
      value: activityTotal,
      icon: Activity,
      color: "text-primary",
      background: "bg-primary/10",
    },
  ];

  return (
    <div className="flex min-w-0 flex-1 flex-col gap-6 px-2 py-3 sm:px-4 sm:py-4 lg:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">
            Ringkasan Sistem
          </h2>
          <p className="text-sm text-muted-foreground">
            Pantau pengguna, publikasi, dan aktivitas sistem dari satu tempat.
          </p>
        </div>
        <Button
          onClick={loadDashboard}
          disabled={loading}
          className="w-full sm:w-fit"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Memuat..." : "Refresh Data"}
        </Button>
      </div>

      {message ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {message}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <Card key={card.label}>
              <CardContent className="flex items-center justify-between p-5">
                <div>
                  <p className="text-sm text-muted-foreground">{card.label}</p>
                  <p className="mt-1 text-3xl font-semibold">
                    {loading ? "-" : card.value}
                  </p>
                </div>
                <div className={`rounded-xl p-3 ${card.background}`}>
                  <Icon className={`h-6 w-6 ${card.color}`} />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <PublicationCharts publications={publications} />

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Publikasi Terbaru</CardTitle>
              <CardDescription>Data publikasi yang terakhir diperbarui</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/super-admin/publications")}
            >
              Lihat Semua
            </Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <Table className="min-w-[560px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Judul</TableHead>
                    <TableHead>Kategori</TableHead>
                    <TableHead>Tahun</TableHead>
                    <TableHead>Diperbarui</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {latestPublications.length > 0 ? (
                    latestPublications.map((publication) => (
                      <TableRow key={String(publication.id)}>
                        <TableCell className="max-w-[260px] truncate font-medium">
                          {publication.title || "-"}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {publication.category || "-"}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {publication.year || "-"}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {formatDate(publication.updatedAt)}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        className="h-24 text-center text-muted-foreground"
                      >
                        {loading ? "Mengambil data..." : "Belum ada publikasi."}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Pengguna Terbaru</CardTitle>
              <CardDescription>Akun pengguna yang baru terdaftar</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/super-admin/users")}
            >
              Lihat Semua
            </Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <Table className="min-w-[480px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Nama</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Tanggal Daftar</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {latestUsers.length > 0 ? (
                    latestUsers.map((user) => (
                      <TableRow key={String(user.id)}>
                        <TableCell className="whitespace-nowrap font-medium">
                          {user.name || "-"}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {user.email || "-"}
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {formatDate(user.createdAt)}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={3}
                        className="h-24 text-center text-muted-foreground"
                      >
                        {loading ? "Mengambil data..." : "Belum ada user."}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
