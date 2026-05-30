import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  SlidersHorizontal,
  Lightbulb,
  Filter,
  Network,
} from "lucide-react";
import { getUser, searchArticles } from "@/api/api";

export interface SearchFilters {
  jenisArtikel: string;
  yearStart: string;
  yearEnd: string;
  jenisAnalisis: string;
  jumlahKemunculan: string;
}

const POPULAR_QUERIES = [
  "Web Development",
  "Mobile Application",
  "Cyber Security",
  "Machine Learning",
];

const HISTORY_STORAGE_KEY = "search_history";

export function Searchpage() {
  const navigate = useNavigate();

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [noResult, setNoResult] = useState(false);

  const [user, setUser] = useState(() => getUser());
  const [yearStart, setYearStart] = useState<string>("");
  const [yearEnd, setYearEnd] = useState<string>("");
  const [jenisArtikel, setJenisArtikel] = useState<string>("");
  const [jenisAnalisis, setJenisAnalisis] = useState<string>("");
  const [jumlahKemunculan, setJumlahKemunculan] = useState<string>("");

  const [searchHistory, setSearchHistory] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    const syncUser = () => setUser(getUser());

    window.addEventListener("user-updated", syncUser);
    window.addEventListener("storage", syncUser);

    return () => {
      window.removeEventListener("user-updated", syncUser);
      window.removeEventListener("storage", syncUser);
    };
  }, []);

  const displayName = user?.name?.trim() || "User";

  const saveHistory = (keyword: string) => {
    const clean = keyword.trim();
    if (!clean) return;

    const updated = [clean, ...searchHistory.filter((item) => item !== clean)].slice(0, 6);
    setSearchHistory(updated);
    window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
  };

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setNoResult(false);

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
        yearEnd ? parseInt(yearEnd) : undefined,
        jenisArtikel || undefined,
        jenisAnalisis || undefined,
        jumlahKemunculan || undefined
      );

      if (res.status === "success" && res.data && res.data.length > 0) {
        saveHistory(query);
        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          state: {
            results: res.data,
            query,
            filters: activeFilters,
            total_occurrences: res.total_occurrences ?? 0,
            paper_count: res.paper_count ?? res.data.length,
          },
        });
      } else {
        setNoResult(true);
        setLoading(false);
      }
    } catch (error) {
      console.error(error);
      setNoResult(true);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header + Search tanpa card kotak */}
      <div className="flex items-center justify-center">
        <section className="w-full max-w-4xl px-2 py-4">
          <div className="text-center">
            <h1 className="md:text-xl text-3xl font-bold leading-tight">
              Hai, <span className="text-black font-bold">{displayName}</span>
            </h1>
            <p className="mx-auto mt-5 max-w-2xl text-md text-slate-500">
              Mau cari publikasi apa hari ini?
            </p>
          </div>

          <div className="mx-auto mt-10 flex max-w-4xl items-center gap-2 rounded-3xl border bg-white p-2 shadow-sm">
            <Search className="h-5 w-5 ml-2 text-slate-400" />

            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSearch();
                }
              }}
              placeholder="Cari artikel, topik, atau keyword..."
              className="flex-1 border-none bg-transparent outline-none"
            />

            <Dialog>
              <DialogTrigger asChild>
                <button className="hover:bg-black/8 rounded-xl py-2 px-2">
                  <SlidersHorizontal className="w-4 h-4" />
                </button>
              </DialogTrigger>

              <DialogContent className="max-w-xl min-h-[350px] rounded-2xl border border-black shadow-md">
                <DialogHeader>
                  <DialogTitle className="text-center">Pencarian Publikasi</DialogTitle>
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
                        min={0}
                      />
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <Button onClick={handleSearch} className="px-16">
                      Terapkan Filter
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>

            <button
              onClick={handleSearch}
              disabled={loading}
              className="rounded-xl bg-gradient-to-r from-indigo-500 to-blue-500 px-5 py-2 font-medium text-white transition hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Mencari..." : "Cari"}
            </button>
          </div>

          <div className="mt-6">
            <p className="text-sm text-slate-500 mb-3">Coba pencarian populer</p>
            <div className="flex flex-wrap gap-2">
              {POPULAR_QUERIES.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setQuery(item)}
                  className="rounded-full border px-4 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>

      {noResult && !loading && (
        <div className="text-center">
          <p className="text-slate-500 font-medium">
            Data tidak ditemukan untuk "{query}"
          </p>
          <button
            type="button"
            className="mt-3 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-500 px-6 py-2 font-medium text-white transition hover:opacity-90"
          >
            Request
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="w-full shadow-sm rounded-xl p-6">
          <h3 className="font-semibold mb-4">Pencarian Terakhir</h3>
          {searchHistory.length === 0 ? (
            <p className="text-sm text-slate-400">Belum ada riwayat pencarian.</p>
          ) : (
            <div className="space-y-2">
              {searchHistory.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setQuery(item)}
                  className="w-full text-left rounded-lg border px-3 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card className="w-full shadow-sm rounded-xl p-6">
          <h3 className="font-semibold mb-4">Tips Pencarian</h3>
          <div className="space-y-4 text-sm">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-emerald-50 p-2 text-emerald-600">
                <Lightbulb className="h-4 w-4" />
              </div>
              <div>
                <p className="font-medium text-slate-800">Gunakan kata kunci spesifik</p>
                <p className="text-slate-500">Semakin spesifik kata kunci, semakin akurat hasilnya.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-blue-50 p-2 text-blue-600">
                <Filter className="h-4 w-4" />
              </div>
              <div>
                <p className="font-medium text-slate-800">Gunakan filter untuk hasil terbaik</p>
                <p className="text-slate-500">Manfaatkan filter tahun, bidang, dan jenis publikasi.</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-amber-50 p-2 text-amber-600">
                <Network className="h-4 w-4" />
              </div>
              <div>
                <p className="font-medium text-slate-800">Eksplorasi jaringan sitasi</p>
                <p className="text-slate-500">Temukan artikel penting melalui hubungan sitasi.</p>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}