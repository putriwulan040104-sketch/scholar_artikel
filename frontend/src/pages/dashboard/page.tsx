import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { SlidersHorizontal, X } from "lucide-react";
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
import {
  getAnalysisTypeOptions,
  getCategoryOptions,
  searchArticles,
  type AnalysisTypeOption,
  type CategoryOption,
} from "@/api/api";

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
  jumlah_kemunculan?: number | string;
  occurrence?: number | string;
  occurrences?: number | string;
}

interface SearchFilters {
  jenisArtikel: string;
  jenisAnalisis: string;
  yearStart: string;
  yearEnd: string;
  kategori: string;
  jumlahKemunculan: string;
}

type FilterKey = keyof SearchFilters | "year";

const JENIS_ARTIKEL_LABEL: Record<string, string> = {
  open: "Open Source",
  close: "Close Source",
};

const JENIS_ANALISIS_LABEL: Record<string, string> = {
  bibliographic_coupling: "Bibliographic Coupling",
  keyword_cooccurrence: "Keyword Co-occurrence",
  co_authorship: "Co-authorship",
};

const TREND_TOP_K = 5000;

function buildChips(filters: SearchFilters): { key: FilterKey; label: string }[] {
  const chips: { key: FilterKey; label: string }[] = [];

  if (filters.jenisArtikel) {
    chips.push({
      key: "jenisArtikel",
      label: JENIS_ARTIKEL_LABEL[filters.jenisArtikel] ?? filters.jenisArtikel,
    });
  }

  if (filters.jenisAnalisis) {
    chips.push({
      key: "jenisAnalisis",
      label:
        JENIS_ANALISIS_LABEL[filters.jenisAnalisis] ??
        filters.jenisAnalisis.replaceAll("_", " "),
    });
  }

  if (filters.yearStart || filters.yearEnd) {
    chips.push({
      key: "year",
      label: `Tahun: ${filters.yearStart || "-"} - ${filters.yearEnd || "-"}`,
    });
  }

  if (filters.kategori) {
    chips.push({
      key: "kategori",
      label: filters.kategori,
    });
  }

  if (filters.jumlahKemunculan) {
    chips.push({
      key: "jumlahKemunculan",
      label: `Kemunculan >= ${filters.jumlahKemunculan}`,
    });
  }

  return chips;
}

function FilterChip({
  label,
  onClick,
  onRemove,
}: {
  label: string;
  onClick?: () => void;
  onRemove?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-700 shadow-sm whitespace-nowrap hover:bg-slate-50 transition"
    >
      <span>{label}</span>
      <span
        role="button"
        tabIndex={0}
        onClick={(event) => {
          event.stopPropagation();
          onRemove?.();
        }}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            event.stopPropagation();
            onRemove?.();
          }
        }}
        className="rounded-full p-0.5 text-slate-400 hover:bg-slate-100 hover:text-red-500"
        aria-label={`Hapus filter ${label}`}
      >
        <X className="h-3.5 w-3.5" />
      </span>
    </button>
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

  const initFilters: SearchFilters = {
    jenisArtikel: "",
    jenisAnalisis: "",
    yearStart: "",
    yearEnd: "",
    kategori: "",
    jumlahKemunculan: "",
    ...(location.state?.filters ?? {}),
  };

  const [tableData, setTableData] = useState<Article[]>(
    Array.isArray(location.state?.results) ? location.state.results : []
  );
  const [trendData, setTrendData] = useState<Article[]>(
    Array.isArray(location.state?.results) ? location.state.results : []
  );
  const [totalMatched, setTotalMatched] = useState<number>(
    location.state?.total_matched ??
      location.state?.total ??
      (Array.isArray(location.state?.results) ? location.state.results.length : 0)
  );
  const [totalOccurrences, setTotalOccurrences] = useState<number>(
    location.state?.total_occurrences ?? 0
  );

  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [activeFilters, setActiveFilters] = useState<SearchFilters>(initFilters);
  const [jenisArtikel, setJenisArtikel] = useState(initFilters.jenisArtikel);
  const [jenisAnalisis, setJenisAnalisis] = useState(initFilters.jenisAnalisis);
  const [yearStart, setYearStart] = useState(initFilters.yearStart);
  const [yearEnd, setYearEnd] = useState(initFilters.yearEnd);
  const [kategori, setKategori] = useState(initFilters.kategori);
  const [jumlahKemunculan, setJumlahKemunculan] = useState(
    initFilters.jumlahKemunculan
  );
  const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
  const [analysisTypeOptions, setAnalysisTypeOptions] = useState<AnalysisTypeOption[]>([]);

  const chips = buildChips(activeFilters);

  const paperCount = tableData.length;

  const sumOccurrencesFromRows = useMemo(() => {
    return tableData.reduce((acc, row) => acc + getOccurrenceValue(row), 0);
  }, [tableData]);

  const cardTotalOccurrences =
    sumOccurrencesFromRows > 0 ? sumOccurrencesFromRows : totalOccurrences;

  const chartKey = [
    query,
    activeFilters.jenisArtikel,
    activeFilters.jenisAnalisis,
    activeFilters.yearStart,
    activeFilters.yearEnd,
    activeFilters.kategori,
    activeFilters.jumlahKemunculan,
    trendData.length,
    cardTotalOccurrences,
  ].join("|");

  const openFilterEditor = () => {
    setJenisArtikel(activeFilters.jenisArtikel);
    setJenisAnalisis(activeFilters.jenisAnalisis);
    setYearStart(activeFilters.yearStart);
    setYearEnd(activeFilters.yearEnd);
    setKategori(activeFilters.kategori);
    setJumlahKemunculan(activeFilters.jumlahKemunculan);
    setOpen(true);
  };

  useEffect(() => {
    const loadFilterOptions = async () => {
      const [categoryRes, analysisRes] = await Promise.all([
        getCategoryOptions(),
        getAnalysisTypeOptions(),
      ]);
      if (categoryRes.status === "success" && Array.isArray(categoryRes.data)) {
        setCategoryOptions(categoryRes.data);
      }
      if (analysisRes.status === "success" && Array.isArray(analysisRes.data)) {
        setAnalysisTypeOptions(analysisRes.data);
      }
    };

    loadFilterOptions();
  }, []);

  const fetchWithFilters = async (filters: SearchFilters, topK = 10) => {
    if (!query.trim()) return null;

    const minOccurrence =
      filters.jumlahKemunculan.trim() !== ""
        ? Number(filters.jumlahKemunculan)
        : undefined;

    const safeMinOccurrence =
      typeof minOccurrence === "number" && !Number.isNaN(minOccurrence)
        ? minOccurrence
        : undefined;

    return searchArticles(
      query,
      topK,
      filters.yearStart ? parseInt(filters.yearStart) : undefined,
      filters.yearEnd ? parseInt(filters.yearEnd) : undefined,
      filters.jenisArtikel || undefined,
      filters.kategori || undefined,
      safeMinOccurrence,
      undefined,
      filters.jenisAnalisis || undefined,
    );
  };

  const handleApplyFilter = async () => {
    if (!query.trim()) return;

    setLoading(true);

    const newFilters: SearchFilters = {
      jenisArtikel,
      jenisAnalisis,
      yearStart,
      yearEnd,
      kategori,
      jumlahKemunculan,
    };

    try {
      const res = await fetchWithFilters(newFilters);

      if (res?.status === "success" && res.data) {
        const nextData = Array.isArray(res.data) ? res.data : [];
        const nextTotalMatched = res.total_matched ?? res.total ?? nextData.length;
        const nextTotalOccurrences = nextData.reduce(
          (acc, row) => acc + getOccurrenceValue(row as Article),
          0
        );

        setTableData(nextData);
        setTotalMatched(nextTotalMatched);
        setTotalOccurrences(nextTotalOccurrences);
        setActiveFilters(newFilters);

        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          replace: true,
          state: {
            results: nextData,
            query,
            filters: newFilters,
            total_matched: nextTotalMatched,
            total_occurrences: nextTotalOccurrences,
            paper_count: nextData.length,
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

  const handleRemoveFilter = async (key: FilterKey) => {
    const nextFilters: SearchFilters = { ...activeFilters };

    if (key === "jenisArtikel") {
      nextFilters.jenisArtikel = "";
      setJenisArtikel("");
    }

    if (key === "jenisAnalisis") {
      nextFilters.jenisAnalisis = "";
      setJenisAnalisis("");
    }

    if (key === "year") {
      nextFilters.yearStart = "";
      nextFilters.yearEnd = "";
      setYearStart("");
      setYearEnd("");
    }

    if (key === "kategori") {
      nextFilters.kategori = "";
      setKategori("");
    }

    if (key === "jumlahKemunculan") {
      nextFilters.jumlahKemunculan = "";
      setJumlahKemunculan("");
    }

    setLoading(true);
    try {
      const res = await fetchWithFilters(nextFilters);

      if (res?.status === "success" && res.data) {
        const nextData = Array.isArray(res.data) ? res.data : [];
        const nextTotalMatched = res.total_matched ?? res.total ?? nextData.length;
        const nextTotalOccurrences = nextData.reduce(
          (acc, row) => acc + getOccurrenceValue(row as Article),
          0
        );

        setTableData(nextData);
        setTotalMatched(nextTotalMatched);
        setTotalOccurrences(nextTotalOccurrences);
        setActiveFilters(nextFilters);

        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          replace: true,
          state: {
            results: nextData,
            query,
            filters: nextFilters,
            total_matched: nextTotalMatched,
            total_occurrences: nextTotalOccurrences,
            paper_count: nextData.length,
          },
        });
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    try {
      const ids = tableData
        .map((item) => Number(item.id))
        .filter((id) => Number.isFinite(id));
      localStorage.setItem("lastSearchPublicationIds", JSON.stringify(ids));
      localStorage.setItem("lastSearchQuery", query || "");
      localStorage.setItem("lastSearchFilters", JSON.stringify(activeFilters));
      window.dispatchEvent(new Event("search-context-updated"));
    } catch (_error) {
      // no-op
    }
  }, [tableData, query, activeFilters]);

  useEffect(() => {
    const run = async () => {
      if (!query.trim()) {
        setTrendData([]);
        return;
      }

      try {
        const res = await fetchWithFilters(activeFilters, TREND_TOP_K);
        if (res?.status === "success" && Array.isArray(res.data)) {
          setTrendData(res.data as Article[]);
        } else {
          setTrendData([]);
        }
      } catch (_error) {
        setTrendData([]);
      }
    };

    run();
  }, [query, activeFilters]);

  if (!location.state?.results && tableData.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500">
        Data tidak ditemukan. Silakan lakukan pencarian ulang.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <div className="@container/main flex flex-1 flex-col gap-2">
        <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
          <div className="px-4 lg:px-6">
            <div className="flex flex-wrap items-center gap-2">
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                  <button
                    type="button"
                    onClick={openFilterEditor}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-500 shadow-sm hover:bg-slate-50 transition"
                  >
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
                        <Select
                          onValueChange={setJenisArtikel}
                          value={jenisArtikel}
                        >
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
                        <label className="text-sm">Kategori penelitian</label>
                        <Select onValueChange={setKategori} value={kategori}>
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Pilih kategori" />
                          </SelectTrigger>
                          <SelectContent>
                            {categoryOptions.length === 0 ? (
                              <SelectItem value="category-empty" disabled>
                                Kategori belum tersedia
                              </SelectItem>
                            ) : (
                              categoryOptions.map((category) => (
                                <SelectItem key={category.value} value={category.value}>
                                  {category.label}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-sm">Jenis analisis</label>
                        <Select
                          onValueChange={setJenisAnalisis}
                          value={jenisAnalisis}
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue placeholder="Pilih analisis" />
                          </SelectTrigger>
                          <SelectContent>
                            {analysisTypeOptions.length === 0 ? (
                              <SelectItem value="analysis-empty" disabled>
                                Jenis analisis belum tersedia
                              </SelectItem>
                            ) : (
                              analysisTypeOptions.map((option) => (
                                <SelectItem key={option.value} value={option.value}>
                                  {option.label}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex flex-col gap-2">
                        <label className="text-sm font-medium">
                          Jumlah kemunculan
                        </label>
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
                      <Button
                        onClick={handleApplyFilter}
                        className="px-16"
                        disabled={loading}
                      >
                        {loading ? "Menerapkan..." : "Terapkan Filter"}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {chips.length > 0 && <span className="h-5 w-px bg-slate-300" />}

              {chips.map((chip) => (
                <FilterChip
                  key={chip.key}
                  label={chip.label}
                  onClick={openFilterEditor}
                  onRemove={() => handleRemoveFilter(chip.key)}
                />
              ))}
            </div>
          </div>

          <SectionCards
            query={query}
            jumlahKemunculan={activeFilters.jumlahKemunculan}
            totalOccurrences={cardTotalOccurrences}
            paperCount={paperCount}
            totalMatched={totalMatched}
            kategori={activeFilters.kategori}
          />

          <div className="px-4 lg:px-6">
            <ChartBarLabel
              key={chartKey}
              articles={trendData}
              yearStart={activeFilters.yearStart}
              yearEnd={activeFilters.yearEnd}
              onOpenCitationGraph={() => navigate("/citation-graph")}
            />
          </div>

          <DataTable data={tableData} />
        </div>
      </div>
    </div>
  );
}
