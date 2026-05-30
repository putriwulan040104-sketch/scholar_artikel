"use client";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface SectionCardsProps {
  query?            : string;
  jumlahKemunculan? : string;
  totalOccurrences? : number;  // ← ganti dari tfData
  paperCount?       : number;
}

export function SectionCards({
  query: _query,
  jumlahKemunculan: _jumlahKemunculan,
  totalOccurrences = 0,
  paperCount       = 0,
}: SectionCardsProps) {

const safeTotalOccurrences = Number.isFinite(totalOccurrences)
    ? totalOccurrences
    : 0;
  const safePaperCount = Number.isFinite(paperCount) ? paperCount : 0;


  return (
    <>
      <h1 className="px-4 lg:px-6 text-2xl font-normal tracking-tight">
        Selamat Datang,{" "}
        <span className="text-black font-bold">User</span>
      </h1>

      <div className="grid grid-cols-1 gap-4 px-4 text-center *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-3 @5xl/main:grid-cols-3 dark:*:data-[slot=card]:bg-card">

        <Card className="@container/card">
          <CardHeader>
            <CardDescription>Jumlah Publikasi</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {safePaperCount}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="@container/card">
          <CardHeader>
            <CardDescription>Jumlah Kemunculan</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {safeTotalOccurrences}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card className="@container/card">
          <CardHeader>
            <CardDescription>Sumber Data</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {safePaperCount > 0 ? 1 : 0}
            </CardTitle>
          </CardHeader>
        </Card>

      </div>
    </>
  );
}