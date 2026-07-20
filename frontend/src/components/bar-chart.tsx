"use client";

import { useId, useMemo } from "react";
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Network } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

type TrendArticle = {
  year?: number | string | null;
};

type ChartRow = {
  year: string;
  count: number;
};

interface ChartBarLabelProps {
  articles: TrendArticle[];
  yearStart?: string;
  yearEnd?: string;
  onOpenCitationGraph?: () => void;
}

const chartConfig = {
  count: {
    label: "Jumlah Publikasi",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

function toYearNumber(value?: string): number | undefined {
  if (!value) return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function getArticleYear(value: TrendArticle["year"]): number | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

export function ChartBarLabel({
  articles,
  yearStart,
  yearEnd,
  onOpenCitationGraph,
}: ChartBarLabelProps) {
  const gradientId = useId().replace(/:/g, "");
  const { chartData, subtitle } = useMemo(() => {
    const yearCount = new Map<number, number>();

    for (const row of articles || []) {
      const y = getArticleYear(row.year);
      if (!y) continue;
      yearCount.set(y, (yearCount.get(y) || 0) + 1);
    }

    const start = toYearNumber(yearStart);
    const end = toYearNumber(yearEnd);

    let years: number[] = [];
    if (start && end && start <= end) {
      years = Array.from({ length: end - start + 1 }, (_, i) => start + i);
    } else if (start && !end) {
      const inferredEnd =
        yearCount.size > 0 ? Math.max(...Array.from(yearCount.keys())) : start;
      years = Array.from(
        { length: Math.max(1, inferredEnd - start + 1) },
        (_, i) => start + i,
      );
    } else if (!start && end) {
      const inferredStart =
        yearCount.size > 0 ? Math.min(...Array.from(yearCount.keys())) : end;
      years = Array.from(
        { length: Math.max(1, end - inferredStart + 1) },
        (_, i) => inferredStart + i,
      );
    } else {
      years = Array.from(yearCount.keys()).sort((a, b) => a - b);
    }

    const data: ChartRow[] = years.map((y) => ({
      year: String(y),
      count: yearCount.get(y) || 0,
    }));

    const desc =
      years.length > 0 ? `${years[0]} - ${years[years.length - 1]}` : "No data";

    return { chartData: data, subtitle: desc };
  }, [articles, yearStart, yearEnd]);
  const shouldTiltTicks = chartData.length > 8;

  return (
    <Card className="overflow-hidden border-border/70 shadow-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle>Penelitian per Tahun</CardTitle>
            <CardDescription>{subtitle}</CardDescription>
          </div>
          {onOpenCitationGraph && (
            <Button
              variant="outline"
              size="lg"
              className="shrink-0"
              onClick={onOpenCitationGraph}
            >
              <Network className="h-4 w-4" />
              <span>Jaringan Artikel</span>
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={chartConfig}
          className="h-[300px] w-full sm:h-[320px]"
        >
          <AreaChart
            accessibilityLayer
            data={chartData}
            margin={{
              top: 16,
              left: 4,
              right: 18,
              bottom: shouldTiltTicks ? 10 : 2,
            }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor="var(--color-count)"
                  stopOpacity={0.32}
                />
                <stop
                  offset="95%"
                  stopColor="var(--color-count)"
                  stopOpacity={0.08}
                />
              </linearGradient>
            </defs>
            <CartesianGrid vertical={false} strokeDasharray="4 4" />
            <XAxis
              dataKey="year"
              tickLine={false}
              tickMargin={shouldTiltTicks ? 14 : 10}
              axisLine={false}
              interval={0}
              minTickGap={0}
              angle={shouldTiltTicks ? -35 : 0}
              textAnchor={shouldTiltTicks ? "end" : "middle"}
              height={shouldTiltTicks ? 58 : 36}
            />
            <YAxis
              allowDecimals={false}
              axisLine={false}
              tickLine={false}
              tickMargin={8}
              width={36}
            />
            <ChartTooltip
              cursor={{
                stroke: "var(--color-count)",
                strokeWidth: 1,
                strokeDasharray: "4 4",
                opacity: 0.45,
              }}
              content={
                <ChartTooltipContent
                  indicator="dot"
                  labelFormatter={(label) => `Tahun ${String(label)}`}
                  formatter={(value) => (
                    <div className="flex w-full items-center justify-between gap-3">
                      <span className="text-muted-foreground">
                        Jumlah Publikasi
                      </span>
                      <span className="font-mono font-medium tabular-nums">
                        {Number(value || 0).toLocaleString()}
                      </span>
                    </div>
                  )}
                />
              }
            />
            <Area
              dataKey="count"
              type="monotone"
              fill={`url(#${gradientId})`}
              stroke="var(--color-count)"
              strokeWidth={2.5}
              dot={
                chartData.length <= 12
                  ? {
                      r: 3,
                      fill: "var(--card)",
                      stroke: "var(--color-count)",
                      strokeWidth: 2,
                    }
                  : false
              }
              activeDot={{
                r: 5,
                fill: "var(--color-count)",
                stroke: "var(--card)",
                strokeWidth: 2,
              }}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
