import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, XAxis } from "recharts";
import type { ManagedPublication, PublicationExtractionStatus } from "@/api/api";
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
    label: "Jumlah Publikasi: ",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

const qualityChartConfig = {
  total: {
    label: "Jumlah Publikasi: ",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

const QUALITY_ITEMS: {
  status: PublicationExtractionStatus;
  label: string;
  color: string;
}[] = [
  { status: "complete", label: "Lengkap", color: "#10b981" },
  { status: "partial", label: "Sebagian", color: "#f59e0b" },
  { status: "empty", label: "Kosong", color: "#ef4444" },
];

function normalizeStatus(status?: string | null): PublicationExtractionStatus {
  const value = String(status || "empty").toLowerCase();

  if (value === "complete" || value === "partial") {
    return value;
  }

  return "empty";
}

function buildMonthlyData(publications: ManagedPublication[]) {
  const formatter = new Intl.DateTimeFormat("id-ID", {
    month: "short",
  });
  const now = new Date();

  return Array.from({ length: 6 }, (_, index) => {
    const month = new Date(now.getFullYear(), now.getMonth() - 5 + index, 1);
    const nextMonth = new Date(month.getFullYear(), month.getMonth() + 1, 1);
    const total = publications.filter((publication) => {
      if (!publication.updatedAt) return false;
      const updatedAt = new Date(publication.updatedAt);
      return (
        !Number.isNaN(updatedAt.getTime()) &&
        updatedAt >= month &&
        updatedAt < nextMonth
      );
    }).length;

    return {
      month: formatter.format(month),
      total,
    };
  });
}

export function PublicationCharts({
  publications,
}: {
  publications: ManagedPublication[];
}) {
  const monthlyData = buildMonthlyData(publications);
  const qualityData = QUALITY_ITEMS.map((item) => ({
    ...item,
    total: publications.filter(
      (publication) => normalizeStatus(publication.extractionStatus) === item.status,
    ).length,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Publikasi Diperbarui</CardTitle>
          <CardDescription>Jumlah publikasi berdasarkan update enam bulan terakhir</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={monthChartConfig}
            className="h-[280px] w-full"
          >
            <AreaChart
              accessibilityLayer
              data={monthlyData}
              margin={{ left: 12, right: 12 }}
            >
              <defs>
                <linearGradient id="publicationAreaFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--color-total)" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="var(--color-total)" stopOpacity={0.12} />
                </linearGradient>
              </defs>
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
              <Area
                dataKey="total"
                type="monotone"
                fill="url(#publicationAreaFill)"
                stroke="var(--color-total)"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ChartContainer>
        </CardContent>
      </Card>

      <Card className="min-w-0">
        <CardHeader>
          <CardTitle>Kelengkapan Data</CardTitle>
          <CardDescription>Distribusi publikasi berdasarkan hasil ekstraksi</CardDescription>
        </CardHeader>
        <CardContent>
          <ChartContainer
            config={qualityChartConfig}
            className="h-[280px] w-full"
          >
            <BarChart accessibilityLayer data={qualityData}>
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
                {qualityData.map((item) => (
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
