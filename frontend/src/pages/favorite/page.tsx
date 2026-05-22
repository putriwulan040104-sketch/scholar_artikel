"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Trash2,Info} from "lucide-react";
import { useNavigate } from "react-router-dom";
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
  const navigate = useNavigate();
  useEffect(() => {
    try {
      const stored = localStorage.getItem("favorites");
      if (stored) setFavorites(JSON.parse(stored));
    } catch (_) {
      setFavorites([]);
    }
  }, []);

  const handleDelete = (id: number) => {
    const updated = favorites.filter((item) => item.id !== id);
    setFavorites(updated);
    localStorage.setItem("favorites", JSON.stringify(updated));
    setConfirmId(null);
  };

  const confirmItem = favorites.find((f) => f.id === confirmId);

  return (
    <div className="p-6 space-y-6">

      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Favorit</h1>
        <span className="text-sm text-muted-foreground">
          {favorites.length} artikel tersimpan
        </span>
      </div>

      {/* LIST DATA */}
      <div className="grid gap-4">
        {favorites.map((item) => (
          <Card key={item.id} className="hover:shadow-md transition">

            {/* ── Header: judul (kiri) + score + trash (kanan) ── */}
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-4">

                {/* Judul */}
                <CardTitle className="text-base leading-snug flex-1">
                  {item.title}
                </CardTitle>

                    {/* Similarity Score */}
                <div className="shrink-0">
                  <span className="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-semibold whitespace-nowrap">
                    {item.similarity_score?.toFixed(4) ?? "—"}
                  </span>
                </div>

              </div>
            </CardHeader>

            {/* ── Content: penulis + tahun ── */}
            <CardContent className="pt-0">
              <div className="flex items-end justify-between gap-4">

                {/* LEFT */}
                <div className="text-sm text-muted-foreground space-y-1">
                  <p>{item.authors}</p>

                  <p className="text-xs">
                    {item.year ?? "-"}
                  </p>
                </div>

                {/* RIGHT */}
                <div className="flex items-center gap-2">

                  {/* DETAIL */}
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-8 w-8"
                    onClick={() => navigate(`/detail/${item.id}`)}
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
            </CardContent>
          </Card>
        ))}
      </div>

      {/* EMPTY STATE */}
      {favorites.length === 0 && (
        <div className="text-center text-muted-foreground py-10">
          Belum ada artikel favorit
        </div>
      )}

      {/* Dialog konfirmasi hapus */}
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
              No
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmId !== null && handleDelete(confirmId)}
            >
              Yes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}