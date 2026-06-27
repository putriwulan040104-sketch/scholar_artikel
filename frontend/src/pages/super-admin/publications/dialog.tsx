import { useEffect, useState } from "react";
import type {
  ManagedPublication,
  PublicationMutationPayload,
} from "@/api/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export type PublicationDialogMode = "edit" | "delete";

interface PublicationDialogProps {
  open: boolean;
  mode: PublicationDialogMode;
  publication: ManagedPublication | null;
  loading: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload?: PublicationMutationPayload) => void;
}

function joinValues(values?: string[]) {
  return Array.isArray(values) ? values.join(", ") : "";
}

function splitValues(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function PublicationDialog({
  open,
  mode,
  publication,
  loading,
  onOpenChange,
  onSubmit,
}: PublicationDialogProps) {
  const [title, setTitle] = useState("");
  const [authors, setAuthors] = useState("");
  const [keywords, setKeywords] = useState("");
  const [doi, setDoi] = useState("");
  const [journal, setJournal] = useState("");
  const [year, setYear] = useState("");
  const [articleUrl, setArticleUrl] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");

  useEffect(() => {
    if (!open || !publication) return;

    setTitle(publication.title || "");
    setAuthors(joinValues(publication.authors));
    setKeywords(joinValues(publication.keywords));
    setDoi(publication.doi || "");
    setJournal(publication.journal || "");
    setYear(publication.year ? String(publication.year) : "");
    setArticleUrl(publication.articleUrl || "");
    setPdfUrl(publication.pdfUrl || "");
  }, [open, publication]);

  const handleSubmit = () => {
    if (mode === "delete") {
      onSubmit();
      return;
    }

    onSubmit({
      title: title.trim(),
      authors: splitValues(authors),
      keywords: splitValues(keywords),
      doi: doi.trim(),
      journal: journal.trim(),
      year: year ? Number(year) : null,
      articleUrl: articleUrl.trim(),
      pdfUrl: pdfUrl.trim(),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {mode === "delete" ? "Hapus Publikasi" : "Edit Publikasi"}
          </DialogTitle>
        </DialogHeader>

        {mode === "delete" ? (
          <div className="space-y-5">
            <p className="text-sm text-muted-foreground">
              Publikasi <strong>{publication?.title || "-"}</strong> akan dihapus permanen.
              Relasi artikel yang masih terhubung dapat membuat penghapusan ditolak database.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Batal
              </Button>
              <Button variant="destructive" onClick={handleSubmit} disabled={loading}>
                {loading ? "Menghapus..." : "Hapus"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="publication-title">Judul</Label>
              <Input
                id="publication-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>

            <div className="grid gap-2 md:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="publication-journal">Jurnal</Label>
                <Input
                  id="publication-journal"
                  value={journal}
                  onChange={(event) => setJournal(event.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="publication-year">Tahun</Label>
                <Input
                  id="publication-year"
                  type="number"
                  value={year}
                  onChange={(event) => setYear(event.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="publication-authors">Penulis</Label>
              <Input
                id="publication-authors"
                value={authors}
                onChange={(event) => setAuthors(event.target.value)}
                placeholder="Pisahkan penulis dengan koma"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="publication-keywords">Keywords</Label>
              <Input
                id="publication-keywords"
                value={keywords}
                onChange={(event) => setKeywords(event.target.value)}
                placeholder="Pisahkan keyword dengan koma"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="publication-doi">DOI</Label>
              <Input
                id="publication-doi"
                value={doi}
                onChange={(event) => setDoi(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="publication-url">URL Artikel</Label>
              <Input
                id="publication-url"
                value={articleUrl}
                onChange={(event) => setArticleUrl(event.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="publication-pdf-url">URL PDF</Label>
              <Input
                id="publication-pdf-url"
                value={pdfUrl}
                onChange={(event) => setPdfUrl(event.target.value)}
              />
            </div>

            <div className="flex justify-end gap-2 border-t pt-4">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Batal
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={loading || !title.trim()}
              >
                {loading ? "Menyimpan..." : "Simpan Perubahan"}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
