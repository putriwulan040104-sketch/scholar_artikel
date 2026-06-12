import type { ActivityLog } from "@/api/api";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface ActivityLogDetailDialogProps {
  open: boolean;
  log: ActivityLog | null;
  onOpenChange: (open: boolean) => void;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "long",
    timeStyle: "medium",
  }).format(date);
}

function JsonData({
  title,
  value,
}: {
  title: string;
  value?: Record<string, unknown> | null;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{title}</p>
      <pre className="max-h-64 overflow-auto rounded-md border bg-muted/30 p-3 text-xs leading-relaxed">
        {value ? JSON.stringify(value, null, 2) : "Tidak ada data."}
      </pre>
    </div>
  );
}

export function ActivityLogDetailDialog({
  open,
  log,
  onOpenChange,
}: ActivityLogDetailDialogProps) {
  if (!log) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Detail Aktivitas</DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          <div className="grid gap-4 rounded-md border bg-muted/20 p-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Waktu</p>
              <p className="text-sm font-medium">{formatDate(log.createdAt)}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Role</p>
              <p className="text-sm font-medium">{log.userName || "System"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Objek</p>
              <p className="text-sm font-medium">
                {log.entityType || "-"} {log.entityId ? `#${log.entityId}` : ""}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
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
            </div>
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground">Deskripsi</p>
              <p className="text-sm">{log.description || "-"}</p>
            </div>
            <div className="sm:col-span-2">
              <p className="text-xs text-muted-foreground">Alamat IP</p>
              <p className="text-sm">{log.ipAddress || "-"}</p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <JsonData title="Data Sebelum" value={log.oldData} />
            <JsonData title="Data Sesudah" value={log.newData} />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
