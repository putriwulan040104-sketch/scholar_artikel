"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Star, Trash2, ExternalLink } from "lucide-react";

const dummyData = [
  {
    id: 1,
    title: "Sistem Information Retrieval Berbasis VSM",
    author: "Zulfa Ramadani",
    year: 2024,
  },
  {
    id: 2,
    title: "Visualisasi Citation Graph untuk Analisis Tren",
    author: "Putut Suharso",
    year: 2023,
  },
];

export default function FavoritPage() {
  return (
    <div className="p-6 space-y-6">
      {/* HEADER */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold flex items-center gap-2">
          {/* <Star className="text-yellow-500" /> */}
          Favorit
        </h1>
      </div>

      {/* LIST DATA */}
      <div className="grid gap-4">
        {dummyData.map((item) => (
          <Card key={item.id} className="hover:shadow-md transition">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">
                {item.title}
              </CardTitle>
            </CardHeader>

            <CardContent className="flex items-center justify-between">
              {/* Info */}
              <div className="text-sm text-muted-foreground">
                <p>{item.author}</p>
                <p>{item.year}</p>
              </div>

              {/* Action */}
              <div className="flex gap-2">
                <Button variant="outline" size="icon">
                  <ExternalLink className="w-4 h-4" />
                </Button>

                <Button variant="destructive" size="icon">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* EMPTY STATE (kalau nanti kosong) */}
      {dummyData.length === 0 && (
        <div className="text-center text-muted-foreground py-10">
          Belum ada data favorit
        </div>
      )}
    </div>
  );
}