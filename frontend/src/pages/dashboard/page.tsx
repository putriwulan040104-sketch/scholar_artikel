// import { Avatar, AvatarFallback } from "@/components/ui/avatar";
// import {
//   DropdownMenu,
//   DropdownMenuContent,
//   DropdownMenuItem,
//   DropdownMenuLabel,
//   DropdownMenuSeparator,
//   DropdownMenuTrigger,
// } from "@/components/ui/dropdown-menu";
// import { SidebarTrigger } from "@/components/ui/sidebar";
// import { ChevronDown, User } from "lucide-react";
import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { SlidersHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { SectionCards } from "@/components/section-cards";
import { DataTable } from "@/components/data-table";
import { ChartBarLabel } from "@/components/bar-chart";
import { searchArticles } from "@/api/api";

interface Article {
  rank: number;
  id: number;
  title: string;
  authors: string;
  year: number;
  source: string;
  category: string;
  similarity_score: number;
  favorite: boolean;
  pdf_url?: string | null;
  url?: string | null;
  access_url?: string | null;
  is_pdf?: boolean | string;

  // kemungkinan field kemunculan dari backend
  jumlah_kemunculan?: number | string;
  occurrence?: number | string;
  occurrences?: number | string;
}

interface SearchFilters {
  jenisArtikel: string;
  yearStart: string;
  yearEnd: string;
  jenisAnalisis: string;
  jumlahKemunculan: string;
}

const JENIS_ARTIKEL_LABEL: Record<string, string> = {
  open: "Open Source",
  close: "Close Source",
};

const JENIS_ANALISIS_LABEL: Record<string, string> = {
  co: "Co-citation",
  bib: "Bibliographic",
};

function buildChips(filters: SearchFilters): string[] {
  const chips: string[] = [];
  if (filters.jenisArtikel) {
    chips.push(JENIS_ARTIKEL_LABEL[filters.jenisArtikel] ?? filters.jenisArtikel);
  }
  if (filters.yearStart || filters.yearEnd) {
    chips.push(`Tahun: ${filters.yearStart || "—"} – ${filters.yearEnd || "—"}`);
  }
  if (filters.jenisAnalisis) {
    chips.push(JENIS_ANALISIS_LABEL[filters.jenisAnalisis] ?? filters.jenisAnalisis);
  }
  if (filters.jumlahKemunculan) {
    chips.push(`Kemunculan ≥ ${filters.jumlahKemunculan}`);
  }
  return chips;
}

function FilterChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-700 shadow-sm whitespace-nowrap">
      {label}
    </span>
  );
}

function getOccurrenceValue(article: Article): number {
  const raw =
    article.jumlah_kemunculan ??
    article.occurrence ??
    article.occurrences ??
    (article as any).term_frequency ??
    0;

  const num = typeof raw === "string" ? Number(raw) : raw;
  return Number.isFinite(num) ? Number(num) : 0;
}

export default function Page() {
  const location = useLocation();
  const navigate = useNavigate();

  const query: string =
    location.state?.query ||
    new URLSearchParams(location.search).get("query") ||
    "";

  const initFilters: SearchFilters = location.state?.filters ?? {
    jenisArtikel: "",
    yearStart: "",
    yearEnd: "",
    jenisAnalisis: "",
    jumlahKemunculan: "",
  };

  const [tableData, setTableData] = useState<Article[]>(
    Array.isArray(location.state?.results) ? location.state.results : []
  );
  const [totalOccurrences, setTotalOccurrences] = useState<number>(
    location.state?.total_occurrences ?? 0
  );

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeFilters, setActiveFilters] = useState<SearchFilters>(initFilters);

  const [jenisArtikel, setJenisArtikel] = useState(initFilters.jenisArtikel);
  const [yearStart, setYearStart] = useState(initFilters.yearStart);
  const [yearEnd, setYearEnd] = useState(initFilters.yearEnd);
  const [jenisAnalisis, setJenisAnalisis] = useState(initFilters.jenisAnalisis);
  const [jumlahKemunculan, setJumlahKemunculan] = useState(initFilters.jumlahKemunculan);

  if (!location.state?.results && tableData.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500">
        Data tidak ditemukan. Silakan lakukan pencarian ulang.
      </div>
    );
  }

  const chips = buildChips(activeFilters);

  // Statistik cards: selalu sinkron dengan hasil tabel terbaru.
  const paperCount = tableData.length;

  const sumOccurrencesFromRows = useMemo(() => {
    return tableData.reduce((acc, row) => acc + getOccurrenceValue(row), 0);
  }, [tableData]);

  const cardTotalOccurrences =
    sumOccurrencesFromRows > 0 ? sumOccurrencesFromRows : totalOccurrences;

  // Force chart re-mount saat filter/data berubah agar tidak menampilkan state awal.
  const chartKey = [
    query,
    activeFilters.jenisArtikel,
    activeFilters.yearStart,
    activeFilters.yearEnd,
    activeFilters.jenisAnalisis,
    activeFilters.jumlahKemunculan,
    tableData.length,
    cardTotalOccurrences,
  ].join("|");

  const handleApplyFilter = async () => {
  if (!query.trim()) return;
  setLoading(true);

  const newFilters: SearchFilters = {
    jenisArtikel,
    yearStart,
    yearEnd,
    jenisAnalisis,
    jumlahKemunculan,
  };

  const minOccurrence =
    jumlahKemunculan.trim() !== "" ? Number(jumlahKemunculan) : undefined;

  const safeMinOccurrence =
    typeof minOccurrence === "number" && !Number.isNaN(minOccurrence)
      ? minOccurrence
      : undefined;

  try {
    const res = await searchArticles(
      query,
      10,
      yearStart ? parseInt(yearStart) : undefined,
      yearEnd ? parseInt(yearEnd) : undefined,
      jenisArtikel || undefined,
      jenisAnalisis || undefined,
      safeMinOccurrence
    );

    if (res.status === "success" && res.data) {
      const nextData = Array.isArray(res.data) ? res.data : [];

      const nextPaperCount = nextData.length;
      const nextTotalOccurrences = nextData.reduce(
        (acc, row) => acc + getOccurrenceValue(row as Article),
        0
      );

      setTableData(nextData);
      setTotalOccurrences(nextTotalOccurrences);
      setActiveFilters(newFilters);

      navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
        replace: true,
        state: {
          results: nextData,
          query,
          filters: newFilters,
          total_occurrences: nextTotalOccurrences,
          paper_count: nextPaperCount,
        },
      });
    }
  } catch (error) {
    console.error(error);
  } finally {
    setLoading(false);
    setOpen(false);
  }
};

  return (
    <div className="flex flex-1 flex-col">
      <div className="@container/main flex flex-1 flex-col gap-2">
        <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
          <div className="px-4 lg:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                  <button className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-500 shadow-sm hover:bg-slate-50 transition">
                    <SlidersHorizontal className="h-3.5 w-3.5" />
                    Filter
                  </button>
                </DialogTrigger>

                <DialogContent className="max-w-xl min-h-[350px] rounded-2xl border border-black shadow-md">
                  <DialogHeader>
                    <DialogTitle className="text-center">
                      Pencarian Publikasi
                    </DialogTitle>
                  </DialogHeader>

                  <div className="space-y-8 py-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex flex-col gap-2">
                        <label className="text-sm">Jenis artikel</label>
                        <Select onValueChange={setJenisArtikel} value={jenisArtikel}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Jenis artikel" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="open">Open Source</SelectItem>
                            <SelectItem value="close">Close Source</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-sm">Tahun terbit</label>
                        <div className="flex gap-2">
                          <Select onValueChange={setYearStart} value={yearStart}>
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder="Awal" />
                            </SelectTrigger>
                            <SelectContent>
                              {Array.from({ length: 6 }, (_, i) => {
                                const year = 2021 + i;
                                return (
                                  <SelectItem key={year} value={year.toString()}>
                                    {year}
                                  </SelectItem>
                                );
                              })}
                            </SelectContent>
                          </Select>

                          <Select onValueChange={setYearEnd} value={yearEnd}>
                            <SelectTrigger className="w-full">
                              <SelectValue placeholder="Akhir" />
                            </SelectTrigger>
                            <SelectContent>
                              {Array.from({ length: 6 }, (_, i) => {
                                const year = 2021 + i;
                                return (
                                  <SelectItem key={year} value={year.toString()}>
                                    {year}
                                  </SelectItem>
                                );
                              })}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-sm">Jenis analisis</label>
                        <Select onValueChange={setJenisAnalisis} value={jenisAnalisis}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Co-citation" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="co">Co-citation</SelectItem>
                            <SelectItem value="bib">Bibliographic</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-sm font-medium">Jumlah kemunculan</label>
                        <Input
                          type="number"
                          placeholder="Contoh: 5"
                          value={jumlahKemunculan}
                          onChange={(e) => setJumlahKemunculan(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.preventDefault();
                              handleApplyFilter();
                            }
                          }}
                          min={0}
                        />
                      </div>
                    </div>

                    <div className="flex justify-center">
                      <Button onClick={handleApplyFilter} className="px-16" disabled={loading}>
                        {loading ? "Menerapkan..." : "Terapkan Filter"}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {chips.length > 0 && <span className="h-5 w-px bg-slate-300" />}
              {chips.map((chip) => (
                <FilterChip key={chip} label={chip} />
              ))}
            </div>
          </div>

          <SectionCards
            query={query}
            jumlahKemunculan={activeFilters.jumlahKemunculan}
            totalOccurrences={cardTotalOccurrences}
            paperCount={paperCount}
          />

          <div className="px-4 lg:px-6">
            <ChartBarLabel key={chartKey} />
          </div>

          <div className="px-4 lg:px-6">
            <h2 className="text-lg font-semibold text-slate-700">
              Hasil pencarian: "{query}"
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Total {tableData.length} artikel ditemukan
            </p>
          </div>

          <DataTable data={tableData} />
        </div>
      </div>
    </div>
  );
}
