import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Activity,
  ClipboardList,
  RefreshCw,
  UsersRound,
} from "lucide-react";
import {
  getActivityLogs,
  getArticleRequests,
  getUsers,
  type ArticleRequest,
  type ArticleRequestStatus,
  type ManagedUser,
} from "@/api/api";
import { Badge } from "@/components/ui/badge";
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
import { RequestCharts } from "./charts";

function normalizeRole(role?: string | null) {
  return String(role || "user")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");
}

function normalizeStatus(status?: string | null): ArticleRequestStatus {
  const value = String(status || "pending").toLowerCase();

  if (value === "processing" || value === "done" || value === "rejected") {
    return value;
  }

  return "pending";
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

function statusLabel(status?: string | null) {
  const labels: Record<ArticleRequestStatus, string> = {
    pending: "Pending",
    processing: "Diproses",
    done: "Selesai",
    rejected: "Ditolak",
  };

  return labels[normalizeStatus(status)];
}

function statusClassName(status?: string | null) {
  const normalized = normalizeStatus(status);

  if (normalized === "done") {
    return "border-emerald-200 bg-emerald-100 text-emerald-700";
  }
  if (normalized === "processing") {
    return "border-blue-200 bg-blue-100 text-blue-700";
  }
  if (normalized === "rejected") {
    return "border-red-200 bg-red-100 text-red-700";
  }

  return "border-yellow-200 bg-yellow-100 text-yellow-700";
}

export default function SuperAdminDashboardPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [requests, setRequests] = useState<ArticleRequest[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setMessage("");

    const [usersResult, requestsResult, activityResult] = await Promise.all([
      getUsers(),
      getArticleRequests(),
      getActivityLogs({ page: 1, pageSize: 1 }),
    ]);

    setUsers(usersResult.status === "success" ? usersResult.data || [] : []);
    setRequests(
      requestsResult.status === "success" ? requestsResult.data || [] : [],
    );
    setActivityTotal(
      activityResult.status === "success" ? activityResult.total || 0 : 0,
    );

    const errors = [usersResult, requestsResult, activityResult]
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
        .slice(0, 5),
    [regularUsers],
  );

  const latestRequests = useMemo(
    () =>
      [...requests]
        .sort((left, right) => timestamp(right.createdAt) - timestamp(left.createdAt))
        .slice(0, 5),
    [requests],
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
      label: "Total Request",
      value: requests.length,
      icon: ClipboardList,
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
            Pantau pengguna dan permintaan artikel dari satu tempat.
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

      <div className="grid gap-4 grid-cols-3">
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

      <RequestCharts requests={requests} />

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <Card className="min-w-0">
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Request Terbaru</CardTitle>
              <CardDescription>Permintaan artikel terakhir</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/super-admin/requests")}
            >
              Lihat Semua
            </Button>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border">
              <Table className="min-w-[560px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Pengguna</TableHead>
                    <TableHead>Judul Artikel</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Tanggal</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {latestRequests.length > 0 ? (
                    latestRequests.map((request) => (
                      <TableRow key={String(request.id)}>
                        <TableCell className="whitespace-nowrap font-medium">
                          {request.nama || request.email || "-"}
                        </TableCell>
                        <TableCell className="max-w-[220px] truncate">
                          {request.judulArtikel || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={statusClassName(request.status)}
                          >
                            {statusLabel(request.status)}
                          </Badge>
                        </TableCell>
                        <TableCell className="whitespace-nowrap">
                          {formatDate(request.createdAt)}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        className="h-24 text-center text-muted-foreground"
                      >
                        {loading ? "Mengambil data..." : "Belum ada request."}
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
