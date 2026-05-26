import { useState, useEffect } from "react";
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
import { Search, SlidersHorizontal } from "lucide-react";
import { getUser, searchArticles } from "@/api/api";

export interface SearchFilters {
  jenisArtikel: string;
  yearStart: string;
  yearEnd: string;
  jenisAnalisis: string;
  jumlahKemunculan: string;
}

export function Searchpage() {
  const navigate = useNavigate();

  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [user, setUser] = useState(() => getUser());
  const [yearStart, setYearStart] = useState<string>("");
  const [yearEnd, setYearEnd] = useState<string>("");
  const [jenisArtikel, setJenisArtikel] = useState<string>("");
  const [jenisAnalisis, setJenisAnalisis] = useState<string>("");
  const [jumlahKemunculan, setJumlahKemunculan] = useState<string>("");

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

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setSearched(true);

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

      // kalau ada hasil → pindah dashboard
      if (res.status === "success" && res.data && res.data.length > 0) {
        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          state: {
            results: res.data,
            query: query,
            filters: activeFilters,
          },
        });
      }

      // kalau tidak ada hasil → tetap di halaman search
      else {
        setLoading(false);
      }
    } catch (error) {
      console.error(error);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">

      <div className="flex items-center justify-center">
        <Card className="w-full max-w-4xl shadow-md rounded-xl">
          <section className="mx-auto max-w-6xl px-8 py-10">
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
                onKeyDown={(e) =>  {
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
                className="rounded-xl bg-gradient-to-r from-indigo-500 to-blue-500 px-5 py-2 font-medium text-white transition hover:opacity-90"
              >
                {loading ? "Mencari..." : "Cari"}
              </button>
            </div>

          </section>
        </Card>
      </div>

      {/* ===== PESAN JIKA TIDAK ADA HASIL ===== */}
      {searched && !loading && (
        <div className="flex items-center justify-center">
          <Card className="w-full max-w-4xl shadow-md rounded-xl p-6">
            <p className="text-center text-slate-400 py-8">
              Tidak ada artikel ditemukan untuk "{query}"
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}