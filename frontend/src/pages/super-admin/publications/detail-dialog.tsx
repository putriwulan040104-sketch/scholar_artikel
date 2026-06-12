import type { ManagedPublication } from "@/api/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ExternalLink } from "lucide-react";

interface PublicationDetailDialogProps {
  open: boolean;
  publication: ManagedPublication | null;
  onOpenChange: (open: boolean) => void;
}

function DetailItem({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="text-sm text-foreground">{children || "-"}</div>
    </div>
  );
}

export function PublicationDetailDialog({
  open,
  publication,
  onOpenChange,
}: PublicationDetailDialogProps) {
  if (!publication) return null;

  const authors = publication.authors || [];
  const keywords = publication.keywords || [];
  const references = publication.referenceList || [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Detail Publikasi</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          <div className="space-y-2 border-b pb-4">
            <h3 className="pr-6 text-base font-semibold leading-relaxed">
              {publication.title || "Publikasi tanpa judul"}
            </h3>
            <p className="text-xs text-muted-foreground">
              ID Publikasi: {publication.id}
              {publication.articleId
                ? ` | ID Artikel: ${publication.articleId}`
                : ""}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <DetailItem label="Kategori Penelitian">
              {publication.category || "Tanpa kategori"}
            </DetailItem>
            <DetailItem label="Tahun">{publication.year || "-"}</DetailItem>
            <DetailItem label="Jurnal">
              {publication.journal || "-"}
            </DetailItem>
            <DetailItem label="DOI">{publication.doi || "-"}</DetailItem>
          </div>

          <DetailItem label="Penulis">
            {authors.length ? authors.join(", ") : "-"}
          </DetailItem>

          <DetailItem label="Keyword">
            {keywords.length ? (
              <div className="flex flex-wrap gap-2">
                {keywords.map((keyword, index) => (
                  <Badge key={`${keyword}-${index}`} variant="secondary">
                    {keyword}
                  </Badge>
                ))}
              </div>
            ) : (
              "-"
            )}
          </DetailItem>

          <DetailItem label={`Daftar Referensi (${references.length})`}>
            {references.length ? (
              <ol className="max-h-64 space-y-2 overflow-y-auto rounded-md border bg-muted/20 p-3 pl-8 text-sm">
                {references.map((reference, index) => (
                  <li key={`${index}-${reference.slice(0, 24)}`} className="list-decimal">
                    {reference}
                  </li>
                ))}
              </ol>
            ) : (
              "Referensi tidak tersedia."
            )}
          </DetailItem>

          <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
            {publication.articleUrl ? (
              <Button variant="outline" asChild>
                <a
                  href={publication.articleUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink className="h-4 w-4" />
                  Buka Artikel
                </a>
              </Button>
            ) : null}
            {publication.pdfUrl ? (
              <Button variant="outline" asChild>
                <a href={publication.pdfUrl} target="_blank" rel="noreferrer">
                  <ExternalLink className="h-4 w-4" />
                  Buka PDF
                </a>
              </Button>
            ) : null}
            <Button onClick={() => onOpenChange(false)}>Tutup</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
