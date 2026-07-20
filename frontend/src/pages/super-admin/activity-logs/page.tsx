import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, CircleCheck, CircleX, RefreshCw, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { getActivityLogs, type ActivityLog } from "@/api/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ActivityLogDetailDialog } from "./detail-dialog";
import ActivityLogTable from "./table";

const PAGE_SIZE = 10;

interface ActivityStatCard {
  label: string;
  value: number;
  icon: LucideIcon;
}

export default function SuperAdminActivityLogsPage() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [entityFilter, setEntityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [activityDate, setActivityDate] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<ActivityLog | null>(null);

  useEffect(() => {
    const timeout = window.setTimeout(
      () => setDebouncedQuery(query.trim()),
      300,
    );
    return () => window.clearTimeout(timeout);
  }, [query]);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setMessage("");

    const result = await getActivityLogs({
      page,
      pageSize: PAGE_SIZE,
      search: debouncedQuery,
      action: actionFilter,
      entityType: entityFilter,
      status: statusFilter,
      dateFrom: activityDate ? `${activityDate}T00:00:00.000+07:00` : "",
      dateTo: activityDate ? `${activityDate}T23:59:59.999+07:00` : "",
    });

    if (result.status === "error") {
      setLogs([]);
      setTotal(0);
      setTotalPages(1);
      setMessage(result.message || "Gagal mengambil log aktivitas.");
    } else {
      setLogs(result.data || []);
      setTotal(result.total || 0);
      setTotalPages(result.totalPages || 1);
    }
    setLoading(false);
  }, [
    actionFilter,
    activityDate,
    debouncedQuery,
    entityFilter,
    page,
    statusFilter,
  ]);

  useEffect(() => {
    void loadLogs();
  }, [loadLogs]);

  const successfulOnPage = useMemo(
    () => logs.filter((log) => log.status !== "failed").length,
    [logs],
  );
  const failedOnPage = useMemo(
    () => logs.filter((log) => log.status === "failed").length,
    [logs],
  );
  const actorsOnPage = useMemo(
    () => new Set(logs.map((log) => log.userName).filter(Boolean)).size,
    [logs],
  );

  const resetPage = (callback: () => void) => {
    callback();
    setPage(1);
  };

  const statCards: ActivityStatCard[] = [
    { label: "Total Aktivitas", value: total, icon: Activity },
    {
      label: "Status Berhasil",
      value: successfulOnPage,
      icon: CircleCheck,
    },
    { label: "Status Gagal", value: failedOnPage, icon: CircleX },
    { label: "Role", value: actorsOnPage, icon: Users },
  ];

  return (
    <div className="flex w-full min-w-0 max-w-full flex-1 flex-col gap-4 px-0 py-3 sm:gap-6 sm:px-4 sm:py-4 lg:px-6">
      <div className="flex justify-stretch sm:justify-end">
        <Button
          onClick={loadLogs}
          disabled={loading}
          className="w-full sm:w-fit"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          {loading ? "Memuat..." : "Refresh Data"}
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {statCards.map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="flex flex-row items-center justify-between p-4 sm:p-6">
              <div>
                <CardDescription>{label}</CardDescription>
                <CardTitle className="mt-1 text-2xl sm:text-3xl">
                  {value}
                </CardTitle>
              </div>
              <Icon className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
          </Card>
        ))}
      </div>

      {message ? (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {message}
        </div>
      ) : null}

      <ActivityLogTable
        logs={logs}
        loading={loading}
        page={page}
        totalPages={totalPages}
        query={query}
        actionFilter={actionFilter}
        entityFilter={entityFilter}
        statusFilter={statusFilter}
        activityDate={activityDate}
        onQueryChange={(value) => resetPage(() => setQuery(value))}
        onActionFilterChange={(value) =>
          resetPage(() => setActionFilter(value))
        }
        onEntityFilterChange={(value) =>
          resetPage(() => setEntityFilter(value))
        }
        onStatusFilterChange={(value) =>
          resetPage(() => setStatusFilter(value))
        }
        onActivityDateChange={(value) =>
          resetPage(() => setActivityDate(value))
        }
        onPageChange={setPage}
        onDetail={(log) => {
          setSelectedLog(log);
          setDetailOpen(true);
        }}
      />

      <ActivityLogDetailDialog
        open={detailOpen}
        log={selectedLog}
        onOpenChange={(open) => {
          setDetailOpen(open);
          if (!open) setSelectedLog(null);
        }}
      />
    </div>
  );
}
