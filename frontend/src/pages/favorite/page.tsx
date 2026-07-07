"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2, Info, ChevronRight, ChevronLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { readFavorites, writeFavorites } from "@/lib/favorites";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

interface FavoriteItem {
  id: number;
  title: string;
  authors: string;
  year?: number;
  similarity_score: number;
  pdf_url?: string | null;
  url?: string | null;
  access_url?: string | null;
  is_pdf?: boolean | string;
}

export default function FavoritPage() {
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  const PAGE_SIZE = 5;

  useEffect(() => {
    const syncFavorites = () => {
      setFavorites(readFavorites<FavoriteItem>());
      setPage(1);
    };

    syncFavorites();
    window.addEventListener("favorites-updated", syncFavorites);
    window.addEventListener("user-updated", syncFavorites);
    window.addEventListener("storage", syncFavorites);

    return () => {
      window.removeEventListener("favorites-updated", syncFavorites);
      window.removeEventListener("user-updated", syncFavorites);
      window.removeEventListener("storage", syncFavorites);
    };
  }, []);

  const handleDelete = (id: number) => {
    const updated = favorites.filter((item) => item.id !== id);
    setFavorites(updated);
    writeFavorites(updated);
    setConfirmId(null);
  };

  const handleGoToDetail = (id: number) => {
    navigate(`/detail/${id}`);
  };

  const totalPages = Math.max(1, Math.ceil(favorites.length / PAGE_SIZE));

  const pagedFavorites = favorites.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE,
  );

  const goToPage = (next: number) => {
    const safe = Math.max(1, Math.min(totalPages, next));
    setPage(safe);
  };

  useEffect(() => {
    if (page > totalPages) {
      setPage(totalPages);
    }
  }, [page, totalPages]);

  const confirmItem = favorites.find((f) => f.id === confirmId);

  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Artikel Favorit</h1>
        <span className="text-sm text-muted-foreground">
          {favorites.length} artikel tersimpan
        </span>
      </div>

      {/* LIST DATA */}
      <div className="grid gap-4">
        {pagedFavorites.map((item) => (
          <Card key={item.id} className="hover:shadow-md transition">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-4">
                {/* JUDUL */}
                <CardTitle className="text-base leading-snug flex-1">
                  <button
                    type="button"
                    onClick={() => handleGoToDetail(item.id)}
                    className="text-left font-semibold hover:underline hover:text-primary transition-colors"
                  >
                    {item.title}
                  </button>
                </CardTitle>

                {/* RIGHT ICONS */}
                <div className="flex items-center gap-2 shrink-0">
                  {/* DETAIL */}
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => handleGoToDetail(item.id)}
                  >
                    <Info className="w-4 h-4" />
                  </Button>

                  {/* DELETE */}
                  <Button
                    variant="destructive"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => setConfirmId(item.id)}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-0">
              <div className="text-sm text-muted-foreground space-y-1">
                <p>{item.authors}</p>
                <p className="text-xs">{item.year ?? "-"}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* PAGINATION */}
      {favorites.length > 0 && totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <Button
              key={p}
              variant={p === page ? "default" : "outline"}
              size="sm"
              onClick={() => goToPage(p)}
              className="min-w-8"
            >
              {p}
            </Button>
          ))}

          <Button
            variant="outline"
            size="sm"
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      {favorites.length === 0 && (
        <div className="text-center text-muted-foreground py-10">
          Belum ada artikel favorit
        </div>
      )}

      {/* DIALOG KONFIRMASI HAPUS */}
      <Dialog open={confirmId !== null} onOpenChange={() => setConfirmId(null)}>
        <DialogContent className="max-w-sm rounded-2xl">
          <DialogHeader>
            <DialogTitle>Hapus artikel dari Favorit?</DialogTitle>
          </DialogHeader>

          <p className="text-sm text-muted-foreground">
            Artikel{" "}
            <span className="font-medium text-foreground">
              "{confirmItem?.title}"
            </span>{" "}
            akan dihapus dari daftar favorit kamu.
          </p>

          <DialogFooter className="flex gap-2 mt-2">
            <Button variant="outline" onClick={() => setConfirmId(null)}>
              Tidak
            </Button>

            <Button
              variant="destructive"
              onClick={() => confirmId !== null && handleDelete(confirmId)}
            >
              Ya
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
