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
import { useEffect, useState } from "react";
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
  favorite?: boolean;
  pdf_url?: string | null;   // ← open access PDF
  url?: string | null;       // ← artikel/abstract page (closed access)
  access_url?: string | null; // ← sudah dipilih backend (prioritas: pdf > url)
  is_pdf?: boolean | string;
}

interface SearchFilters {
  jenisArtikel: string;
  yearStart: string;
  yearEnd: string;
  jenisAnalisis: string;
  jumlahKemunculan: string;
}

// ── Label maps ────────────────────────────────────────────────────────────────
const JENIS_ARTIKEL_LABEL: Record<string, string> = {
  open: "Open Source",
  close: "Close Source",
};

const JENIS_ANALISIS_LABEL: Record<string, string> = {
  co: "Co-citation",
  bib: "Bibliographic",
};

// ── Build chips dari filter aktif ─────────────────────────────────────────────
function buildChips(filters: SearchFilters): string[] {
  const chips: string[] = [];

  if (filters.jenisArtikel)
    chips.push(JENIS_ARTIKEL_LABEL[filters.jenisArtikel] ?? filters.jenisArtikel);

  if (filters.yearStart || filters.yearEnd)
    chips.push(`Tahun: ${filters.yearStart || "—"} – ${filters.yearEnd || "—"}`);

  if (filters.jenisAnalisis)
    chips.push(JENIS_ANALISIS_LABEL[filters.jenisAnalisis] ?? filters.jenisAnalisis);

  if (filters.jumlahKemunculan)
    chips.push(`Kemunculan ≥ ${filters.jumlahKemunculan}`);

  return chips;
}

// ── FilterChip ────────────────────────────────────────────────────────────────
function FilterChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-300 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-700 shadow-sm whitespace-nowrap">
      {label}
    </span>
  );
}

export default function Page() {
  const location = useLocation();
  const navigate = useNavigate();

  // hasil dari SearchPage
  const data: Article[] = location.state?.results || [];
  const query: string = location.state?.query || "";
  const filters: SearchFilters | undefined = location.state?.filters;

  // ── State filter dialog (pre-fill dari filter sebelumnya) ──
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [jenisArtikel, setJenisArtikel] = useState(filters?.jenisArtikel ?? "");
  const [yearStart, setYearStart] = useState(filters?.yearStart ?? "");
  const [yearEnd, setYearEnd] = useState(filters?.yearEnd ?? "");
  const [jenisAnalisis, setJenisAnalisis] = useState(filters?.jenisAnalisis ?? "");
  const [jumlahKemunculan, setJumlahKemunculan] = useState(filters?.jumlahKemunculan ?? "");

  const chips = filters ? buildChips(filters) : [];

  useEffect(() => {
    try {
      const ids = data
        .map((item) => Number(item.id))
        .filter((id) => Number.isFinite(id));
      localStorage.setItem("lastSearchPublicationIds", JSON.stringify(ids));
      localStorage.setItem("lastSearchQuery", query || "");
      if (filters) {
        localStorage.setItem("lastSearchFilters", JSON.stringify(filters));
      } else {
        localStorage.removeItem("lastSearchFilters");
      }
      window.dispatchEvent(new Event("search-context-updated"));
    } catch (_error) {
      // no-op
    }
  }, [data, query, filters]);

  // ── Terapkan filter → search ulang → update state ──
  const handleApplyFilter = async () => {
    if (!query.trim()) return;
    setLoading(true);

    const activeFilters: SearchFilters = {
      jenisArtikel,
      yearStart,
      yearEnd,
      jenisAnalisis,
      jumlahKemunculan,
    };

    try {
      const res = await searchArticles(
        query,
        10,
        yearStart ? parseInt(yearStart) : undefined,
        yearEnd ? parseInt(yearEnd) : undefined
      );

      if (res.status === "success" && res.data && res.data.length > 0) {
        // replace state di halaman yang sama
        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          replace: true,
          state: {
            results: res.data,
            query: query,
            filters: activeFilters,
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

          {/* ── Filter bar: icon filter (kiri) + chips LinkedIn-style ── */}
          <div className="px-4 lg:px-6">
            <div className="flex flex-wrap items-center gap-2">

              {/* Icon filter — selalu tampil permanen di kiri, bisa klik buka dialog */}
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

                      {/* Jenis Artikel */}
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

                      {/* Tahun terbit */}
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

                      {/* Jenis Analisis */}
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

                      {/* Jumlah Kemunculan */}
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

                    </div>{/* end grid */}

                    <div className="flex justify-center">
                      <Button onClick={handleApplyFilter} className="px-16" disabled={loading}>
                        {loading ? "Menerapkan..." : "Terapkan Filter"}
                      </Button>
                    </div>

                  </div>{/* end py-4 */}
                </DialogContent>
              </Dialog>

              {/* Divider tipis kalau ada chips */}
              {chips.length > 0 && (
                <span className="h-5 w-px bg-slate-300" />
              )}

              {/* Chips filter aktif — muncul kalau ada filter diterapkan */}
              {chips.map((chip) => (
                <FilterChip key={chip} label={chip} />
              ))}

            </div>
          </div>

          <SectionCards />

          <div className="px-4 lg:px-6">
            <ChartBarLabel />
          </div>

          {/* info query */}
          <div className="px-4 lg:px-6">
            <h2 className="text-lg font-semibold text-slate-700">
              Hasil pencarian: "{query}"
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Total {data.length} artikel ditemukan
            </p>
          </div>

          {/* tabel */}
          <DataTable data={data} />

        </div>
      </div>
    </div>
  );
}

    {/* <header className="flex h-18 bg-primary items-center px-4">
      <div className="flex items-center gap-2 px-4">
        <SidebarTrigger className="-ml-1 [&_svg]:h-5 [&_svg]:w-5" />
        <h1 className="text-black font-medium">Documents</h1>
      </div>
      <div className="ml-auto">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 rounded-full hover:bg-white/10 p-1 transition">
              <Avatar className="h-8 w-8">
                <AvatarFallback>
                  <User />
                </AvatarFallback>
              </Avatar>

              <ChevronDown className="h-4 w-4 text-white/80" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-500">
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header> */}

    {/* <div className="flex-1">}
    <div className="flex flex-1 flex-col">
      <div className="@container/main flex flex-1 flex-col gap-2">
        <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
          <SectionCards />
          <div className="px-4 lg:px-6">
            <ChartBarLabel />
          </div>
          <DataTable data={data} />
        </div>
      </div>
    </div>
  </div>
  */}
