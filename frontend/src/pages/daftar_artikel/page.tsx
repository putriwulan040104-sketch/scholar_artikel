"use client";

import {
  searchArticles,
  type CosineArticle,
} from "@/api/api";
import { readFavorites, writeFavorites } from "@/lib/favorites";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  Download,
  ExternalLink,
  Star,
} from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

const RANK_SORT_OPTIONS = [
  { value: "query_rank", label: "Rank Hasil Search" },
  { value: "similarity_desc", label: "Similarity Tertinggi" },
  { value: "similarity_asc", label: "Similarity Terendah" },
];

const YEAR_SORT_OPTIONS = [
  { value: "", label: "Semua Tahun" },
  { value: "year_desc", label: "Tahun Terbaru" },
  { value: "year_asc", label: "Tahun Terlama" },
];

const PER_PAGE = 10;
const RESULT_LIMIT = 50;

interface StoredFilters {
  jenisArtikel?: string;
  yearStart?: string;
  yearEnd?: string;
  jumlahKemunculan?: string;
}

function getScoreColor(score: number) {
  if (score >= 0.7) return "text-green-600";
  if (score >= 0.4) return "text-amber-500";
  return "text-red-500";
}

function formatLabel(value?: string | null) {
  if (!value) return "-";
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function isPdfFlag(value?: boolean | string) {
  if (typeof value === "boolean") return value;
  return String(value).toLowerCase() === "true";
}

function loadFavorites(): CosineArticle[] {
  return readFavorites<CosineArticle>();
}

export default function DaftarArtikelPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const query = (
    (location.state as { query?: string } | null)?.query ||
    new URLSearchParams(location.search).get("query") ||
    localStorage.getItem("lastSearchQuery") ||
    ""
  ).trim();

  const [articles, setArticles] = useState<CosineArticle[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalMatched, setTotalMatched] = useState(0);

  const [rankSortBy, setRankSortBy] = useState("query_rank");
  const [yearSortBy, setYearSortBy] = useState("");
  const [page, setPage] = useState(1);
  const [favoriteIds, setFavoriteIds] = useState<number[]>(() =>
    loadFavorites()
      .map((item) => Number(item.id))
      .filter(Number.isFinite),
  );

  const readStoredFilters = useCallback((): StoredFilters => {
    try {
      const raw = localStorage.getItem("lastSearchFilters");
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch {
      return {};
    }
  }, []);

  const fetchArticles = useCallback(async () => {
    if (!query) {
      navigate("/search", { replace: true });
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const filters = readStoredFilters();
      const yearStart = filters.yearStart
        ? Number(filters.yearStart)
        : undefined;
      const yearEnd = filters.yearEnd ? Number(filters.yearEnd) : undefined;
      const jumlahKemunculan =
        filters.jumlahKemunculan && filters.jumlahKemunculan.trim() !== ""
          ? filters.jumlahKemunculan
          : undefined;

      const res = await searchArticles(
        query,
        RESULT_LIMIT,
        Number.isFinite(yearStart) ? yearStart : undefined,
        Number.isFinite(yearEnd) ? yearEnd : undefined,
        filters.jenisArtikel || undefined,
        undefined,
        jumlahKemunculan,
      );

      if (res.status !== "success") {
        throw new Error(res.message || "Gagal mengambil hasil cosine");
      }

      setArticles((res.data || []) as CosineArticle[]);
      setTotalMatched(res.total_matched ?? res.total ?? res.data?.length ?? 0);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Terjadi kesalahan");
    } finally {
      setLoading(false);
    }
  }, [navigate, query, readStoredFilters]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchArticles();
  }, [fetchArticles]);

  useEffect(() => {
    const syncFavorites = () => {
      setFavoriteIds(
        loadFavorites()
          .map((item) => Number(item.id))
          .filter(Number.isFinite),
      );
    };

    window.addEventListener("storage", syncFavorites);
    window.addEventListener("favorites-updated", syncFavorites);
    window.addEventListener("user-updated", syncFavorites);
    return () => {
      window.removeEventListener("storage", syncFavorites);
      window.removeEventListener("favorites-updated", syncFavorites);
      window.removeEventListener("user-updated", syncFavorites);
    };
  }, []);

  const sortedArticles = useMemo(() => {
    const rows = [...articles];

    if (yearSortBy === "year_desc") {
      return rows.sort((a, b) => Number(b.year || 0) - Number(a.year || 0));
    }

    if (yearSortBy === "year_asc") {
      return rows.sort((a, b) => Number(a.year || 0) - Number(b.year || 0));
    }

    if (rankSortBy === "similarity_asc") {
      return rows.sort(
        (a, b) => (a.similarity_score || 0) - (b.similarity_score || 0),
      );
    }

    if (rankSortBy === "similarity_desc") {
      return rows.sort(
        (a, b) => (b.similarity_score || 0) - (a.similarity_score || 0),
      );
    }

    return rows.sort((a, b) => Number(a.rank || 0) - Number(b.rank || 0));
  }, [articles, rankSortBy, yearSortBy]);

  const totalPages = Math.max(1, Math.ceil(sortedArticles.length / PER_PAGE));
  const paginated = sortedArticles.slice(
    (page - 1) * PER_PAGE,
    page * PER_PAGE,
  );

  const pageNumbers = () => {
    const delta = 2;
    const range: number[] = [];
    for (
      let i = Math.max(1, page - delta);
      i <= Math.min(totalPages, page + delta);
      i += 1
    ) {
      range.push(i);
    }
    return range;
  };

  const toggleFavorite = (article: CosineArticle) => {
    const favorites = loadFavorites();
    const exists = favorites.some(
      (item) => Number(item.id) === Number(article.id),
    );
    const next = exists
      ? favorites.filter((item) => Number(item.id) !== Number(article.id))
      : [...favorites, article];

    writeFavorites(next);
    setFavoriteIds(next.map((item) => Number(item.id)).filter(Number.isFinite));
  };

  const showingStart =
    sortedArticles.length === 0 ? 0 : (page - 1) * PER_PAGE + 1;
  const showingEnd = Math.min(page * PER_PAGE, sortedArticles.length);

  const goBackToDashboard = () => {
    if (!query) {
      navigate("/search");
      return;
    }

    const topTen = [...articles]
      .sort((a, b) => Number(a.rank || 0) - Number(b.rank || 0))
      .slice(0, 10);

    navigate(`/dashboard?query=${encodeURIComponent(query)}`, {
      state: {
        results: topTen,
        query,
        filters: readStoredFilters(),
        total_matched: totalMatched || articles.length,
        total_occurrences: topTen.reduce(
          (acc, row) => acc + Number(row.occurrence || 0),
          0,
        ),
        paper_count: topTen.length,
      },
    });
  };

  return (
    <div className="min-h-screen p-6 space-y-4">
      <Breadcrumb className="mb-4">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <button type="button" onClick={goBackToDashboard}>
                Dashboard
              </button>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>Daftar Artikel</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Daftar Artikel</h1>
          <p className="text-sm text-gray-500 mt-1">
            Daftar hasil score similarity dari "{query}" yang sudah tersedia.
          </p>
        </div>

        <div className="w-full bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="flex flex-wrap items-end gap-4 border-b border-gray-100 p-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-600">
                Urutkan Rank
              </label>
              <select
                value={rankSortBy}
                onChange={(e) => {
                  setRankSortBy(e.target.value);
                  setPage(1);
                }}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white min-w-[180px] focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {RANK_SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-semibold text-gray-600">
                Urutkan Tahun
              </label>
              <select
                value={yearSortBy}
                onChange={(e) => {
                  setYearSortBy(e.target.value);
                  setPage(1);
                }}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white min-w-[180px] focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {YEAR_SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400 gap-3">
              <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-500 rounded-full animate-spin" />
              <span className="text-sm">Memuat katalog cosine...</span>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-20 text-red-400 gap-2">
              <span className="text-sm">{error}</span>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-primary border-b border-primary">
                      {[
                        "Rank",
                        "Judul Artikel",
                        "Penulis",
                        "Tahun",
                        "Similarity",
                        "Akses",
                        "Favorit",
                      ].map((header) => (
                        <th
                          key={header}
                          className="px-4 py-3 text-left text-xs font-semibold text-primary-foreground uppercase tracking-wide whitespace-nowrap"
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {paginated.length === 0 ? (
                      <tr>
                        <td
                          colSpan={7}
                          className="text-center py-16 text-gray-400 text-sm"
                        >
                          Tidak ada artikel ditemukan
                        </td>
                      </tr>
                    ) : (
                      paginated.map((article) => {
                        const isFavorite = favoriteIds.includes(
                          Number(article.id),
                        );
                        const accessUrl =
                          article.access_url || article.pdf_url || article.url;
                        const isPdf = isPdfFlag(article.is_pdf);

                        return (
                          <tr
                            key={`${article.query}-${article.id}`}
                            className="hover:bg-gray-50 transition-colors"
                          >
                            <td className="px-4 py-3 text-center text-sm font-semibold text-gray-400 w-14">
                              {article.rank ?? "-"}
                            </td>

                            <td className="px-4 py-3 max-w-xs">
                              <button
                                type="button"
                                onClick={() =>
                                  navigate(`/detail/${article.id}`)
                                }
                                className="text-left text-sm text-gray-800 font-medium leading-snug line-clamp-2 hover:text-blue-600 hover:underline"
                              >
                                {article.title}
                              </button>
                            </td>

                            <td className="px-4 py-3 max-w-[180px]">
                              <span
                                className="text-sm text-gray-600 truncate block"
                                title={article.authors}
                              >
                                {article.authors?.length > 40
                                  ? `${article.authors.slice(0, 40)}...`
                                  : article.authors || "-"}
                              </span>
                            </td>

                            <td className="px-4 py-3 text-center text-sm text-gray-600 w-16">
                              {article.year ?? "-"}
                            </td>

                            <td className="px-4 py-3 text-center w-28">
                              <span
                                className={`text-sm font-bold ${getScoreColor(article.similarity_score)}`}
                              >
                                {article.similarity_score?.toFixed(4) ?? "-"}
                              </span>
                            </td>

                            <td className="px-4 py-3 w-36">
                              {accessUrl ? (
                                <a
                                  href={accessUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`inline-flex items-center gap-1.5 text-xs font-medium rounded-md px-2.5 py-1 transition-colors ${
                                    isPdf
                                      ? "text-green-600 bg-green-50 border border-green-200 hover:bg-green-100"
                                      : "text-blue-600 bg-blue-50 border border-blue-200 hover:bg-blue-100"
                                  }`}
                                >
                                  {isPdf ? (
                                    <Download className="w-3.5 h-3.5" />
                                  ) : (
                                    <ExternalLink className="w-3.5 h-3.5" />
                                  )}
                                  {isPdf ? "PDF" : "Artikel"}
                                </a>
                              ) : (
                                <span className="text-xs text-gray-400">-</span>
                              )}
                            </td>

                            <td className="px-4 py-3 text-center w-16">
                              <button
                                type="button"
                                onClick={() => toggleFavorite(article)}
                                data-testid="favorite-toggle"
                                data-article-id={article.id}
                                title={
                                  isFavorite
                                    ? "Hapus dari favorit"
                                    : "Simpan ke favorit"
                                }
                                aria-label={
                                  isFavorite
                                    ? `Hapus ${article.title} dari favorit`
                                    : `Simpan ${article.title} ke favorit`
                                }
                                className="p-1 rounded-full hover:bg-yellow-50 transition-colors"
                              >
                                <Star
                                  className={`w-4 h-4 transition-colors ${
                                    isFavorite
                                      ? "fill-yellow-400 text-yellow-400"
                                      : "text-gray-300"
                                  }`}
                                />
                              </button>
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {articles.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-t border-gray-100">
                  <span className="text-xs text-gray-500">
                    Menampilkan {showingStart}-{showingEnd} dari{" "}
                    {sortedArticles.length} artikel
                  </span>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                      disabled={page === 1}
                      className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-4 h-4" />
                    </button>

                    {pageNumbers().map((pageNumber) => (
                      <button
                        key={pageNumber}
                        onClick={() => setPage(pageNumber)}
                        className={`w-8 h-8 flex items-center justify-center rounded-md text-sm font-medium transition-colors ${
                          pageNumber === page
                            ? "bg-blue-500 text-white border border-blue-500"
                            : "border border-gray-200 text-gray-600 hover:bg-gray-50"
                        }`}
                      >
                        {pageNumber}
                      </button>
                    ))}

                    <button
                      onClick={() =>
                        setPage((prev) => Math.min(totalPages, prev + 1))
                      }
                      disabled={page === totalPages}
                      className="w-8 h-8 flex items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
