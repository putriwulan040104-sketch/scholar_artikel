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
  Loader2,
} from "lucide-react";
import {
  getAnalysisTypeOptions,
  getCategoryOptions,
  getUser,
  searchArticles,
  type AnalysisTypeOption,
  type CategoryOption,
} from "@/api/api";

export interface SearchFilters {
  jenisArtikel: string;
  jenisAnalisis: string;
  yearStart: string;
  yearEnd: string;
  kategori: string;
  jumlahKemunculan: string;
}

const popularSearches = [
  "Machine Learning",
  "Deep Learning",
  "Data Mining",
  "Web Application",
  "Website Application",
  "Web System",
  "Cyber Security",
  "Network Security",
  "Mobile Application",
  "Android Application",
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
  const [kategori, setKategori] = useState<string>("");
  const [jumlahKemunculan, setJumlahKemunculan] = useState<string>("");
  const [categoryOptions, setCategoryOptions] = useState<CategoryOption[]>([]);
  const [analysisTypeOptions, setAnalysisTypeOptions] = useState<AnalysisTypeOption[]>([]);

  const [openRequestDialog, setOpenRequestDialog] = useState(false);
  const [requestForm, setRequestForm] = useState({
    nama: "",
    email: "",
    kataKunci: "",
    judulArtikel: "",
    keterangan: "",
  });

  const [requestLoading, setRequestLoading] = useState(false);
  const [requestNotif, setRequestNotif] = useState("");
  const [requestNotifType, setRequestNotifType] = useState<"success" | "error">("success");

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
    // Saat kembali ke Eksplorasi, reset konteks hasil pencarian
    localStorage.removeItem("lastSearchPublicationIds");
    localStorage.removeItem("lastSearchQuery");
    localStorage.removeItem("lastSearchFilters");
    window.dispatchEvent(new Event("search-context-updated"));
  }, []);

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

  const handleChangeRequest = (
    key: "nama" | "email" | "kataKunci" | "judulArtikel" | "keterangan",
    value: string
  ) => {
    setRequestForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmitRequest = async () => {
    try {
      setRequestLoading(true);
      setRequestNotif("");

      const res = await fetch("http://127.0.0.1:5000/api/request-article", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestForm),
      });

      const data = await res.json();

      if (!res.ok || data?.status === "error") {
        setRequestNotifType("error");
        setRequestNotif(data?.message || "Gagal mengirim permintaan.");
        return;
      }

      setRequestNotifType(data?.email_sent === false ? "error" : "success");
      setRequestNotif(data?.message || "pesan email terkirim");

      setOpenRequestDialog(false);
      setRequestForm({
        nama: "",
        email: "",
        kataKunci: "",
        judulArtikel: "",
        keterangan: "",
      });
    } catch (error: any) {
      setRequestNotifType("error");
      setRequestNotif(error?.message || "Gagal mengirim permintaan.");
    } finally {
      setRequestLoading(false);
      setTimeout(() => setRequestNotif(""), 5000);
    }
  };

  const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setNoResult(false);

    const activeFilters: SearchFilters = {
      jenisArtikel,
      jenisAnalisis,
      yearStart,
      yearEnd,
      kategori,
      jumlahKemunculan,
    };
    const startedAt = Date.now();
    const minLoadingTime = 1800;

    try {
      const res = await searchArticles(
        query,
        10,
        yearStart ? parseInt(yearStart) : undefined,
        yearEnd ? parseInt(yearEnd) : undefined,
        jenisArtikel || undefined,
        kategori || undefined,
        jumlahKemunculan || undefined,
        undefined,
        jenisAnalisis || undefined,
      );

      const elapsed = Date.now() - startedAt;
      if (elapsed < minLoadingTime) {
        await wait(minLoadingTime - elapsed);
      }

      if (res.status === "success" && res.data && res.data.length > 0) {
        saveHistory(query);
        navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
          state: {
            results: res.data,
            query,
            filters: activeFilters,
            total_matched: res.total_matched ?? res.total ?? res.data.length,
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

      const elapsed = Date.now() - startedAt;
      if (elapsed < minLoadingTime) {
        await wait(minLoadingTime - elapsed);
      }
      setNoResult(true);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {requestNotif && (
        <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[100]">
          <div
            className={`rounded-lg px-4 py-2 text-sm font-medium shadow-md ${
              requestNotifType === "success" ? "bg-emerald-600 text-white" : "bg-red-600 text-white"
            }`}
          >
            {requestNotif}
          </div>
        </div>
      )}

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
                      <Select onValueChange={setJenisAnalisis} value={jenisAnalisis}>
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
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-blue-500 px-5 py-2 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? "Mencari..." : "Cari"}
            </button>
          </div>

          {loading && (
            <div className="mt-4 flex items-center justify-center gap-2 text-sm font-medium text-blue-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Artikel sedang dicari...</span>
            </div>
          )}

          <div className="mt-6">
            <p className="text-sm text-slate-500 mb-3">Coba pencarian lainnya</p>
            <div className="flex flex-wrap gap-3">
              {popularSearches.map((keyword) => (
                <button
                  key={keyword}
                  type="button"
                  onClick={() => {
                    setQuery(keyword);
                    setNoResult(false);
                  }}
                  className="px-5 py-2 rounded-full border border-slate-200 bg-white text-slate-600 hover:bg-blue-50 hover:text-blue-600 hover:border-blue-300 transition"
                >
                  {keyword}
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>

      {noResult && !loading && query.trim() !== "" && (
        <div className="text-center">
          <p className="text-slate-500 font-medium">
            Artikel "{query}" belum tersedia dalam sistem. Silakan kirim permintaan kepada developer.
          </p>
          <button
            type="button"
            onClick={() => {
              setRequestForm((prev) => ({ ...prev, kataKunci: query }));
              setOpenRequestDialog(true);
            }}
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
                <p className="font-medium text-slate-800">Eksplorasi relasi artikel</p>
                <p className="text-slate-500">
                  Temukan artikel yang terhubung melalui referensi yang sama.
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      <Dialog open={openRequestDialog} onOpenChange={setOpenRequestDialog}>
        <DialogContent className="max-w-xl min-h-[470px] rounded-2xl border border-black shadow-md">
          <DialogHeader>
            <DialogTitle className="text-center">Kirim Permintaan</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex flex-col gap-2">
              <label className="text-sm">Nama</label>
              <Input
                value={requestForm.nama}
                onChange={(e) => handleChangeRequest("nama", e.target.value)}
                placeholder="Nama lengkap"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm">Email</label>
              <Input
                type="email"
                value={requestForm.email}
                onChange={(e) => handleChangeRequest("email", e.target.value)}
                placeholder="email@contoh.com"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm">Kata Kunci Pencarian</label>
              <Input
                value={requestForm.kataKunci}
                onChange={(e) => handleChangeRequest("kataKunci", e.target.value)}
                placeholder="Contoh: web accessibility"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm">Judul Artikel (Opsional)</label>
              <Input
                value={requestForm.judulArtikel}
                onChange={(e) => handleChangeRequest("judulArtikel", e.target.value)}
                placeholder="Jika ada judul spesifik"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm">Keterangan Tambahan (Opsional)</label>
              <textarea
                value={requestForm.keterangan}
                onChange={(e) => handleChangeRequest("keterangan", e.target.value)}
                placeholder="Tambahkan detail permintaan..."
                className="min-h-[110px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>

            <div className="flex justify-center pt-2">
              <Button
                onClick={handleSubmitRequest}
                className="px-10"
                disabled={
                  requestLoading ||
                  !requestForm.nama.trim() ||
                  !requestForm.email.trim() ||
                  !requestForm.kataKunci.trim()
                }
              >
                {requestLoading ? "Mengirim..." : "Kirim Permintaan"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
