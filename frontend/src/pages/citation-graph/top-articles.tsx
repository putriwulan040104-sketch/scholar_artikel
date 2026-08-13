import { useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Info,
  Link2,
  Quote,
  Star,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import type { GraphModel, GraphNode } from "./citation-graph.types";
import { buildPageItems, formatAuthors } from "./citation-graph.utils";

const LIST_PAGE_SIZE = 5;

interface TopArticlesProps {
  graphModel: GraphModel;
  favoriteIds: Set<number>;
  selectedNodeId: number | null;
  connectedNodeIds: Set<number>;
  onFocusNode: (node: GraphNode) => void;
  onToggleFavorite: (node: GraphNode) => void;
}

export default function TopArticles({
  graphModel,
  favoriteIds,
  selectedNodeId,
  connectedNodeIds,
  onFocusNode,
  onToggleFavorite,
}: TopArticlesProps) {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);

  // diurutkan secara descending
  const rankedNodes = useMemo(
    () =>
      [...graphModel.gNodes].sort((left, right) => {
        return right.degree - left.degree;
      }),
    [graphModel],
  );

  const totalPages = Math.max(
    1,
    Math.ceil(rankedNodes.length / LIST_PAGE_SIZE),
  );
  const activePage = Math.min(page, totalPages);
  const pagedNodes = useMemo(() => {
    const start = (activePage - 1) * LIST_PAGE_SIZE;
    return rankedNodes.slice(start, start + LIST_PAGE_SIZE);
  }, [activePage, rankedNodes]);
  const pageItems = useMemo(
    () => buildPageItems(activePage, totalPages),
    [activePage, totalPages],
  );

  return (
    <Card className="p-4">
      <h2 className="mb-4 text-2xl font-semibold">Artikel Teratas</h2>
      {!pagedNodes.length ? (
        <p className="text-sm text-muted-foreground">Belum ada data.</p>
      ) : (
        <div className="space-y-3">
          {pagedNodes.map((node) => {
            const relationCount = graphModel.degreeById.get(node.id) || 0;
            const referenceCount = Number(node.referenceCount || 0);
            const detailId = Number(node.articleId ?? node.id);
            const isSelected = node.id === selectedNodeId;
            const isConnected = connectedNodeIds.has(node.id);

            return (
              <div
                key={node.id}
                role="button"
                tabIndex={0}
                onClick={() => onFocusNode(node)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onFocusNode(node);
                  }
                }}
                className={`rounded-lg border bg-white px-4 py-3 text-left transition hover:border-blue-300 hover:bg-blue-50/40 ${
                  isSelected
                    ? "border-amber-300 bg-amber-50/60"
                    : isConnected
                      ? "border-blue-200 bg-blue-50/50"
                      : ""
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="line-clamp-2 text-base font-semibold">
                      {node.title || `Publication ${node.id}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Authors: {formatAuthors(node.authors)} | Year:{" "}
                      {node.year ?? "-"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      DOI: {node.doi || "-"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        if (Number.isFinite(detailId)) {
                          navigate(`/detail/${detailId}`);
                        }
                      }}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-md border text-slate-500 hover:bg-slate-50 hover:text-blue-600"
                      aria-label="Lihat detail artikel"
                    >
                      <Info className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        onToggleFavorite(node);
                      }}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-md border text-slate-500 hover:bg-slate-50"
                      aria-label="Tambah ke favorit"
                    >
                      <Star
                        className={`h-3.5 w-3.5 ${
                          favoriteIds.has(node.id)
                            ? "fill-yellow-400 text-yellow-400"
                            : ""
                        }`}
                      />
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(event) => {
                      event.stopPropagation();
                      onFocusNode(node);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        event.stopPropagation();
                        onFocusNode(node);
                      }
                    }}
                    className={`inline-flex cursor-pointer items-center gap-1.5 font-medium transition hover:underline ${
                      isSelected
                        ? "text-amber-700"
                        : "text-indigo-700 hover:text-indigo-800"
                    }`}
                    aria-label={`Pilih circle artikel dengan ${relationCount} relasi`}
                  >
                    <Link2 className="h-3 w-3" />
                    {relationCount} Relasi
                  </span>
                  <span className="inline-flex h-8 items-center gap-1.5 px-1.5 font-medium text-sky-700">
                    <Quote className="h-3 w-3" />
                    {referenceCount} Referensi
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={activePage <= 1}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>

          {pageItems.map((item, index) =>
            item === "..." ? (
              <span
                key={`ellipsis-${index}`}
                className="px-1 text-sm text-muted-foreground"
              >
                ...
              </span>
            ) : (
              <button
                key={`page-${item}`}
                type="button"
                onClick={() => setPage(Number(item))}
                className={`inline-flex h-8 min-w-8 items-center justify-center rounded-md border px-2 text-sm ${
                  activePage === item
                    ? "border-blue-500 bg-blue-500 text-white"
                    : "bg-white hover:bg-slate-50"
                }`}
              >
                {item}
              </button>
            ),
          )}

          <button
            type="button"
            onClick={() =>
              setPage((current) => Math.min(totalPages, current + 1))
            }
            disabled={activePage >= totalPages}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border disabled:cursor-not-allowed disabled:opacity-50"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </Card>
  );
}
