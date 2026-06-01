"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis } from "recharts";
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

  return (
    <Card>
      <CardHeader>
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
              <span>Jaringan Sitasi</span>
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart
            accessibilityLayer
            data={chartData}
            margin={{
              top: 20,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="year"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  indicator="dot"
                  labelFormatter={(label) => `Tahun ${String(label)}`}
                  formatter={(value) => (
                    <div className="flex w-full items-center justify-between gap-3">
                      <span className="text-muted-foreground">Jumlah Publikasi</span>
                      <span className="font-mono font-medium tabular-nums">
                        {Number(value || 0).toLocaleString()}
                      </span>
                    </div>
                  )}
                />
              }
            />
            <Bar dataKey="count" fill="var(--primary)" radius={8}>
              <LabelList
                position="top"
                offset={12}
                className="fill-foreground"
                fontSize={12}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
