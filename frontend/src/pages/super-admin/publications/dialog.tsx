import { useEffect, useState } from "react";
import type { ManagedPublication, PublicationMutationPayload } from "@/api/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

function parseListText(value: string) {
  const trimmedValue = value.trim();
  if (!trimmedValue) return [];

  if (trimmedValue.startsWith("[") && trimmedValue.endsWith("]")) {
    try {
      const parsed = JSON.parse(trimmedValue);
      if (Array.isArray(parsed)) {
        return parsed.map((item) => String(item).trim()).filter(Boolean);
      }
    } catch {
      // Fall back to comma splitting for manually edited values.
    }
  }

  return trimmedValue
    .split(",")
    .map((item) => item.trim().replace(/^["']|["']$/g, ""))
    .filter(Boolean);
}

function joinValues(values?: string[] | string | null) {
  if (Array.isArray(values)) {
    return values.flatMap((item) => parseListText(String(item))).join(", ");
  }

  return parseListText(String(values || "")).join(", ");
}

function splitValues(value: string) {
  return parseListText(value);
}

function joinReferenceValues(values?: string[]) {
  return Array.isArray(values) ? values.join("\n") : "";
}

function splitReferences(value: string) {
  return value
    .split(/\r?\n/)
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
  const [references, setReferences] = useState("");

  useEffect(() => {
    if (!open || !publication) return;

    const timeoutId = window.setTimeout(() => {
      setTitle(publication.title || "");
      setAuthors(joinValues(publication.authors));
      setKeywords(joinValues(publication.keywords));
      setDoi(publication.doi || "");
      setJournal(publication.journal || "");
      setYear(publication.year ? String(publication.year) : "");
      setArticleUrl(publication.articleUrl || "");
      setPdfUrl(publication.pdfUrl || "");
      setReferences(joinReferenceValues(publication.referenceList));
    }, 0);

    return () => window.clearTimeout(timeoutId);
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
      referenceList: splitReferences(references),
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
              Publikasi <strong>{publication?.title || "-"}</strong> akan
              dihapus permanen. Relasi artikel yang masih terhubung dapat
              membuat penghapusan ditolak database.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Batal
              </Button>
              <Button
                variant="destructive"
                onClick={handleSubmit}
                disabled={loading}
              >
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
                required
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
                  required
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
                required
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

            <div className="grid gap-2">
              <Label htmlFor="publication-references">
                Referensi
                <span className="ml-1 text-xs font-normal text-muted-foreground">
                  (satu referensi per baris)
                </span>
              </Label>
              <textarea
                id="publication-references"
                value={references}
                onChange={(event) => setReferences(event.target.value)}
                placeholder="Tulis satu referensi per baris"
                rows={8}
                className="min-h-36 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
              />
              <p className="text-xs text-muted-foreground">
                Total referensi: {splitReferences(references).length}
              </p>
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
