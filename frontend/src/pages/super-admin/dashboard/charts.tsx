import { Bar, BarChart, CartesianGrid, Cell, XAxis } from "recharts";
import type { ArticleRequest, ArticleRequestStatus } from "@/api/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

const monthChartConfig = {
  total: {
    label: "Jumlah Request: ",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

const statusChartConfig = {
  total: {
    label: "Jumlah Request: ",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

const STATUS_ITEMS: {
  status: ArticleRequestStatus;
  label: string;
  color: string;
}[] = [
  { status: "pending", label: "Pending", color: "#eab308" },
  { status: "processing", label: "Diproses", color: "#3b82f6" },
  { status: "done", label: "Selesai", color: "#10b981" },
  { status: "rejected", label: "Ditolak", color: "#ef4444" },
];

function normalizeStatus(status?: string | null): ArticleRequestStatus {
  const value = String(status || "pending").toLowerCase();

  if (value === "processing" || value === "done" || value === "rejected") {
    return value;
  }

  return "pending";
}

function buildMonthlyData(requests: ArticleRequest[]) {
  const formatter = new Intl.DateTimeFormat("id-ID", {
    month: "short",
  });
  const now = new Date();

  return Array.from({ length: 6 }, (_, index) => {
    const month = new Date(now.getFullYear(), now.getMonth() - 5 + index, 1);
    const nextMonth = new Date(month.getFullYear(), month.getMonth() + 1, 1);
    const total = requests.filter((request) => {
      if (!request.createdAt) return false;
      const createdAt = new Date(request.createdAt);
      return (
        !Number.isNaN(createdAt.getTime()) &&
        createdAt >= month &&
        createdAt < nextMonth
      );
    }).length;

    return {
      month: formatter.format(month),
      total,
    };
  });
}

export function RequestCharts({ requests }: { requests: ArticleRequest[] }) {
  const monthlyData = buildMonthlyData(requests);
  const statusData = STATUS_ITEMS.map((item) => ({
    ...item,
    total: requests.filter(
      (request) => normalizeStatus(request.status) === item.status,
    ).length,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Request Artikel</CardTitle>
          <CardDescription>Jumlah request selama enam bulan terakhir</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={monthChartConfig}
            className="h-[280px] w-full"
          >
            <BarChart accessibilityLayer data={monthlyData}>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="month"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
              />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent indicator="dot" />}
              />
              <Bar dataKey="total" fill="var(--primary)" radius={8} />
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Status Request</CardTitle>
          <CardDescription>Distribusi request berdasarkan status</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={statusChartConfig}
            className="h-[280px] w-full"
          >
            <BarChart accessibilityLayer data={statusData}>
              <CartesianGrid vertical={false} />
              <XAxis
                dataKey="label"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
              />
              <ChartTooltip
                cursor={false}
                content={<ChartTooltipContent indicator="dot" />}
              />
              <Bar dataKey="total" radius={8}>
                {statusData.map((item) => (
                  <Cell key={item.status} fill={item.color} />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>
        </CardContent>
      </Card>
    </div>
  );
}
