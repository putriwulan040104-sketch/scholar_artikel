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
  paperCount?       : number;  // jumlah yang sedang ditampilkan di tabel
  totalMatched?     : number;  // jumlah keseluruhan hasil query
}

export function SectionCards({
  query: _query,
  jumlahKemunculan: _jumlahKemunculan,
  totalOccurrences = 0,
  paperCount       = 0,
  totalMatched     = 0,
}: SectionCardsProps) {

const safeTotalOccurrences = Number.isFinite(totalOccurrences)
    ? totalOccurrences
    : 0;
  const safePaperCount = Number.isFinite(paperCount) ? paperCount : 0;
  const safeTotalMatched = Number.isFinite(totalMatched) ? totalMatched : 0;
  const finalTotalMatched = safeTotalMatched > 0 ? safeTotalMatched : safePaperCount;


  return (
    <>
      <div className="px-4 lg:px-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-800">
          Hasil pencarian: "{_query}"
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Total {finalTotalMatched} artikel ditemukan
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 px-4 text-center *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-3 @5xl/main:grid-cols-3 dark:*:data-[slot=card]:bg-card">

        <Card className="@container/card">
          <CardHeader>
            <CardDescription>Jumlah Publikasi</CardDescription>
            <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
              {finalTotalMatched}
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
