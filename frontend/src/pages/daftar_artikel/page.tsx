    "use client"

    import { getCosineResults, type CategoryOption, type CosineArticle } from "@/api/api"
    import { useCallback, useEffect, useMemo, useState } from "react"
    import { useNavigate } from "react-router-dom"
    import {
    ChevronLeft,
    ChevronRight,
    Download,
    ExternalLink,
    FileText,
    RotateCcw,
    Search,
    Star,
    } from "lucide-react"

    const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
    "machine learning": { bg: "bg-blue-50", text: "text-blue-600", border: "border-blue-200" },
    "cyber security": { bg: "bg-emerald-50", text: "text-emerald-600", border: "border-emerald-200" },
    "web application": { bg: "bg-sky-50", text: "text-sky-600", border: "border-sky-200" },
    "web development": { bg: "bg-sky-50", text: "text-sky-600", border: "border-sky-200" },
    "mobile application": { bg: "bg-teal-50", text: "text-teal-600", border: "border-teal-200" },
    }

    const SORT_OPTIONS = [
    { value: "query_rank", label: "Rank per Kategori" },
    { value: "similarity_desc", label: "Similarity Tertinggi" },
    { value: "similarity_asc", label: "Similarity Terendah" },
    { value: "year_desc", label: "Tahun Terbaru" },
    { value: "year_asc", label: "Tahun Terlama" },
    ]

    const ALL_CATEGORIES = "Semua Kategori"
    const PER_PAGE = 10

    function getCategoryColor(cat: string) {
    return (
        CATEGORY_COLORS[cat?.toLowerCase()] ?? {
        bg: "bg-gray-50",
        text: "text-gray-500",
        border: "border-gray-200",
        }
    )
    }

    function getScoreColor(score: number) {
    if (score >= 0.45) return "text-green-600"
    if (score >= 0.30) return "text-amber-500"
    return "text-red-500"
    }

    function formatLabel(value?: string | null) {
    if (!value) return "-"
    return value
        .split(" ")
        .filter(Boolean)
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ")
    }

    function isPdfFlag(value?: boolean | string) {
    if (typeof value === "boolean") return value
    return String(value).toLowerCase() === "true"
    }

    function loadFavorites(): CosineArticle[] {
    try {
        const parsed = JSON.parse(localStorage.getItem("favorites") || "[]")
        return Array.isArray(parsed) ? parsed : []
    } catch {
        return []
    }
    }

    export default function DaftarArtikelPage() {
    const navigate = useNavigate()
    const [articles, setArticles] = useState<CosineArticle[]>([])
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [totalAll, setTotalAll] = useState(0)
    const [categories, setCategories] = useState<CategoryOption[]>([])

    const [selectedCategory, setSelectedCategory] = useState(ALL_CATEGORIES)
    const [sortBy, setSortBy] = useState("query_rank")
    const [searchText, setSearchText] = useState("")
    const [page, setPage] = useState(1)
    const [favoriteIds, setFavoriteIds] = useState<number[]>(() =>
        loadFavorites().map((item) => Number(item.id)).filter(Number.isFinite)
    )

    const fetchArticles = useCallback(async () => {
        setLoading(true)
        setError(null)

        try {
        const res = await getCosineResults({
            kategori: selectedCategory === ALL_CATEGORIES ? undefined : selectedCategory,
            sortBy,
        })

        if (res.status !== "success") {
            throw new Error(res.message || "Gagal mengambil hasil cosine")
        }

        setArticles(res.data || [])
        setTotalAll(res.total_all || 0)
        setCategories(res.categories || [])
        } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Terjadi kesalahan")
        } finally {
        setLoading(false)
        }
    }, [selectedCategory, sortBy])

    useEffect(() => {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        void fetchArticles()
    }, [fetchArticles])

    useEffect(() => {
        const syncFavorites = () => {
        setFavoriteIds(loadFavorites().map((item) => Number(item.id)).filter(Number.isFinite))
        }

        window.addEventListener("storage", syncFavorites)
        return () => window.removeEventListener("storage", syncFavorites)
    }, [])

    const visibleArticles = useMemo(() => {
        const keyword = searchText.trim().toLowerCase()
        if (!keyword) return articles

        return articles.filter((article) => {
        return (
            article.title?.toLowerCase().includes(keyword) ||
            article.authors?.toLowerCase().includes(keyword)
        )
        })
    }, [articles, searchText])

    const totalPages = Math.max(1, Math.ceil(visibleArticles.length / PER_PAGE))
    const paginated = visibleArticles.slice((page - 1) * PER_PAGE, page * PER_PAGE)

    const pageNumbers = () => {
        const delta = 2
        const range: number[] = []
        for (let i = Math.max(1, page - delta); i <= Math.min(totalPages, page + delta); i += 1) {
        range.push(i)
        }
        return range
    }

    const toggleFavorite = (article: CosineArticle) => {
        const favorites = loadFavorites()
        const exists = favorites.some((item) => Number(item.id) === Number(article.id))
        const next = exists
        ? favorites.filter((item) => Number(item.id) !== Number(article.id))
        : [...favorites, article]

        localStorage.setItem("favorites", JSON.stringify(next))
        setFavoriteIds(next.map((item) => Number(item.id)).filter(Number.isFinite))
    }

    const resetFilter = () => {
        setSelectedCategory(ALL_CATEGORIES)
        setSortBy("query_rank")
        setSearchText("")
    }

    const showingStart = visibleArticles.length === 0 ? 0 : (page - 1) * PER_PAGE + 1
    const showingEnd = Math.min(page * PER_PAGE, visibleArticles.length)

    return (
        <div className="min-h-screen bg-gray-50 p-6 space-y-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-wrap items-start justify-between gap-4">
            <div>
            <h1 className="text-xl font-bold text-gray-900">Daftar Artikel</h1>
            <p className="text-sm text-gray-500 mt-1">
                Katalog hasil score similarity dari topik dataset yang sudah tersedia.
            </p>
            </div>

            <div className="flex items-center gap-3 bg-blue-50 rounded-xl px-5 py-3 shrink-0">
            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
            </div>
            <div>
                <p className="text-xs text-gray-500">Total Katalog</p>
                <p className="text-xl font-bold text-blue-700">{visibleArticles.length} Artikel</p>
                <p className="text-xs text-gray-400">Dari {totalAll} hasil score valid</p>
            </div>
            </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600">Kategori</label>
            <select
                value={selectedCategory}
                onChange={(e) => {
                setSelectedCategory(e.target.value)
                setPage(1)
                }}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white min-w-[190px] focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
                <option value={ALL_CATEGORIES}>{ALL_CATEGORIES}</option>
                {categories.map((category) => (
                <option key={category.value} value={category.value}>
                    {category.label} ({category.count})
                </option>
                ))}
            </select>
            </div>

            <div className="flex flex-col gap-1">
            <label className="text-xs font-semibold text-gray-600">Urutkan</label>
            <select
                value={sortBy}
                onChange={(e) => {
                setSortBy(e.target.value)
                setPage(1)
                }}
                className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white min-w-[180px] focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
                {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                    {option.label}
                </option>
                ))}
            </select>
            </div>

            <div className="flex flex-col gap-1 flex-1 min-w-[220px]">
            <label className="text-xs font-semibold text-gray-600">Cari dalam katalog</label>
            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                type="text"
                placeholder="Cari judul atau penulis..."
                value={searchText}
                onChange={(e) => {
                    setSearchText(e.target.value)
                    setPage(1)
                }}
                className="w-full border border-gray-200 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
            </div>
            </div>

            <button
            onClick={resetFilter}
            className="flex items-center gap-2 border border-gray-200 rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
            <RotateCcw className="w-4 h-4" />
            Reset
            </button>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
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
                    <tr className="bg-gray-50 border-b border-gray-100">
                        {[
                        "Topik",
                        "Rank",
                        "Judul Artikel",
                        "Penulis",
                        "Tahun",
                        "Kategori",
                        "Similarity",
                        "Akses",
                        "Favorit",
                        ].map((header) => (
                        <th
                            key={header}
                            className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap"
                        >
                            {header}
                        </th>
                        ))}
                    </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                    {paginated.length === 0 ? (
                        <tr>
                        <td colSpan={9} className="text-center py-16 text-gray-400 text-sm">
                            Tidak ada artikel ditemukan
                        </td>
                        </tr>
                    ) : (
                        paginated.map((article) => {
                        const catColor = getCategoryColor(article.category)
                        const isFavorite = favoriteIds.includes(Number(article.id))
                        const accessUrl = article.access_url || article.pdf_url || article.url
                        const isPdf = isPdfFlag(article.is_pdf)

                        return (
                            <tr key={`${article.query}-${article.id}`} className="hover:bg-gray-50 transition-colors">
                            <td className="px-4 py-3 w-40">
                                <span className="inline-block rounded-md border border-blue-100 bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-600">
                                {formatLabel(article.query)}
                                </span>
                            </td>

                            <td className="px-4 py-3 text-center text-sm font-semibold text-gray-400 w-14">
                                {article.rank ?? "-"}
                            </td>

                            <td className="px-4 py-3 max-w-xs">
                                <button
                                type="button"
                                onClick={() => navigate(`/detail/${article.id}`)}
                                className="text-left text-sm text-gray-800 font-medium leading-snug line-clamp-2 hover:text-blue-600 hover:underline"
                                >
                                {article.title}
                                </button>
                            </td>

                            <td className="px-4 py-3 max-w-[180px]">
                                <span className="text-sm text-gray-600 truncate block" title={article.authors}>
                                {article.authors?.length > 40
                                    ? `${article.authors.slice(0, 40)}...`
                                    : article.authors || "-"}
                                </span>
                            </td>

                            <td className="px-4 py-3 text-center text-sm text-gray-600 w-16">
                                {article.year ?? "-"}
                            </td>

                            <td className="px-4 py-3 w-36">
                                <span
                                className={`inline-block px-2.5 py-0.5 rounded-md text-xs font-medium border ${catColor.bg} ${catColor.text} ${catColor.border}`}
                                >
                                {formatLabel(article.category)}
                                </span>
                            </td>

                            <td className="px-4 py-3 text-center w-28">
                                <span className={`text-sm font-bold ${getScoreColor(article.similarity_score)}`}>
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
                                    {isPdf ? <Download className="w-3.5 h-3.5" /> : <ExternalLink className="w-3.5 h-3.5" />}
                                    {isPdf ? "PDF" : "Artikel"}
                                </a>
                                ) : (
                                <span className="text-xs text-gray-400">-</span>
                                )}
                            </td>

                            <td className="px-4 py-3 text-center w-16">
                                <button
                                onClick={() => toggleFavorite(article)}
                                title={isFavorite ? "Hapus dari favorit" : "Simpan ke favorit"}
                                className="p-1 rounded-full hover:bg-yellow-50 transition-colors"
                                >
                                <Star
                                    className={`w-4 h-4 transition-colors ${
                                    isFavorite ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
                                    }`}
                                />
                                </button>
                            </td>
                            </tr>
                        )
                        })
                    )}
                    </tbody>
                </table>
                </div>

                {visibleArticles.length > 0 && (
                <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-t border-gray-100">
                    <span className="text-xs text-gray-500">
                    Menampilkan {showingStart}-{showingEnd} dari {visibleArticles.length} artikel
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
                        onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
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
    )
    }
