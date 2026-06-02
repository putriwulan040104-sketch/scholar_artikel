"use client";

import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, ExternalLink, FileText, Star } from "lucide-react";

interface FavoriteItem {
  id: number;
  title: string;
  authors: string;
  abstract?: string;
  keywords?: string[] | string;
  journal?: string;
  year?: number;
  similarity_score: number;
  pdf_url?: string | null;
  url?: string | null;
  access_url?: string | null;
  is_pdf?: boolean | string;
}

export default function DetailPublicationPage() {
  const navigate = useNavigate();
  const { id } = useParams();

  const [article, setArticle] = useState<FavoriteItem | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(true);

  const parseKeywords = (value?: string[] | string): string[] => {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value.map((v) => String(v).trim()).filter(Boolean);
    }

    const raw = String(value).trim();
    if (!raw) return [];

    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed.map((v) => String(v).trim()).filter(Boolean);
      }
    } catch (_error) {
      // ignore JSON parse error
    }

    if (raw.includes(";")) {
      return raw.split(";").map((v) => v.trim()).filter(Boolean);
    }
    if (raw.includes(",")) {
      return raw.split(",").map((v) => v.trim()).filter(Boolean);
    }
    return [raw];
  };

  useEffect(() => {
    const fetchDetail = async () => {
      try {
        setLoading(true);

        // Ambil similarity_score dari localStorage favorites dulu
        const stored = localStorage.getItem("favorites");
        const favorites: FavoriteItem[] = stored ? JSON.parse(stored) : [];
        const fromFavorite = favorites.find((f) => f.id === Number(id));
        const savedScore = fromFavorite?.similarity_score ?? 0;

        const response = await fetch(`http://127.0.0.1:5000/api/detail/${id}`);
        const result = await response.json();

        if (result.status === "success") {
          // Gunakan score dari favorite jika ada, fallback ke backend
          setArticle({
            ...result.data,
            similarity_score: savedScore || result.data.similarity_score,
          });
          setIsFavorite(!!fromFavorite);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    if (id) fetchDetail();
  }, [id]);

  const handleFavorite = () => {
    if (!article) return;

    const stored = localStorage.getItem("favorites");
    const favorites: FavoriteItem[] = stored ? JSON.parse(stored) : [];
    const exists = favorites.some((f) => f.id === article.id);

    if (exists) {
      const updated = favorites.filter((f) => f.id !== article.id);
      localStorage.setItem("favorites", JSON.stringify(updated));
      setIsFavorite(false);
    } else {
      const updated = [...favorites, article];
      localStorage.setItem("favorites", JSON.stringify(updated));
      setIsFavorite(true);
    }
  };

  const handleOpenPDF = () => {
    const link = article?.pdf_url || article?.access_url || article?.url;
    if (link) window.open(link, "_blank");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Memuat artikel...</p>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="min-h-screen bg-[#f5f5f5] p-6">
        <p className="text-muted-foreground">Artikel tidak ditemukan</p>
      </div>
    );
  }

  const keywordList = parseKeywords(article.keywords);

  return (
    <div className="min-h-screen px-6 py-8">

      {/* Back */}
      <Button
        variant="ghost"
        className="mb-6 gap-2 text-muted-foreground"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft className="w-4 h-4" />
        Kembali
      </Button>

      {/* Title */}
      <h1 className="text-3xl font-bold mb-8">Detail Publikasi</h1>

      {/* Card */}
      <Card className="rounded-2xl border bg-white shadow-sm p-8 max-w-5xl">

        {/* Header */}
        <div className="flex items-start justify-between gap-6">

          {/* LEFT - Title, Authors, Journal */}
          <div className="space-y-4 flex-1">
            <h2 className="text-3xl font-bold leading-tight">
              {article.title}
            </h2>
            <div className="space-y-1 text-[15px]">
              <p>
                <span className="font-semibold">Authors:</span>{" "}
                {article.authors}
              </p>
              <p>
                <span className="font-semibold">Journal:</span>{" "}
                {article.journal || "-"}
              </p>
            </div>
          </div>

          {/* RIGHT - Score atas, Year bawah */}
          <div className="flex flex-col items-end gap-3 shrink-0">
            <span className="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap">
              {article.similarity_score?.toFixed(4) ?? "—"}
            </span>
            <div className="text-sm text-muted-foreground">
              Year:{" "}
              <span className="font-semibold text-black">
                {article.year ?? "-"}
              </span>
            </div>
          </div>

        </div>

        {/* Abstract */}
        <div className="mt-10">
          <h3 className="text-xl font-bold mb-4">Abstrak</h3>
          <p className="text-[16px] leading-8 text-muted-foreground">
            {article.abstract || "Abstrak tidak tersedia."}
          </p>
        </div>

        {/* Keywords */}
        <div className="mt-8">
          <h3 className="text-xl font-bold mb-4">Keywords</h3>
          {keywordList.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {keywordList.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-full border bg-slate-50 px-3 py-1 text-sm text-slate-700"
                >
                  {keyword}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-[15px] text-muted-foreground">
              Keywords tidak tersedia.
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 mt-10">

          {/* Favorite */}
          <Button
            variant={isFavorite ? "default" : "outline"}
            onClick={handleFavorite}
            className="gap-2 rounded-xl"
          >
            <Star className={`w-4 h-4 ${isFavorite ? "fill-white" : ""}`} />
            {isFavorite ? "Tersimpan" : "Tambah Favorit"}
          </Button>

          {/* PDF */}
          <Button
            onClick={handleOpenPDF}
            className="bg-[#5d9ce2] hover:bg-[#4d8ed8] rounded-xl px-8 gap-2"
          >
            <FileText className="w-4 h-4" />
            PDF
          </Button>

          {/* Source */}
          {(article.url || article.access_url) && (
            <Button
              variant="outline"
              onClick={() =>
                window.open(article.url || article.access_url || "", "_blank")
              }
              className="rounded-xl gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Source
            </Button>
          )}

        </div>
      </Card>
    </div>
  );
}
