import { Link2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { ArticleRelationType } from "@/api/api";
import type {
  GraphNode,
  SelectedRelations,
} from "./citation-graph.types";
import { shortTitle } from "./citation-graph.utils";

interface RelationDetailsProps {
  selectedNode: GraphNode | null;
  selectedRelations: SelectedRelations;
  relationType: ArticleRelationType | string;
  onSelectNode: (nodeId: number) => void;
}

const RELATION_COPY: Record<
  string,
  {
    description: string;
    emptyText: string;
    weightLabel: string;
    detailLabel: string;
  }
> = {
  bibliographic_coupling: {
    description:
      "Artikel terhubung ketika memiliki satu atau lebih referensi yang sama.",
    emptyText:
      "Tidak ada artikel dengan referensi yang sama dalam jaringan ini.",
    weightLabel: "referensi yang sama",
    detailLabel: "Referensi yang sama",
  },
  keyword_cooccurrence: {
    description:
      "Artikel terhubung ketika memiliki satu atau lebih keyword yang sama.",
    emptyText:
      "Tidak ada artikel dengan keyword yang sama dalam jaringan ini.",
    weightLabel: "keyword yang sama",
    detailLabel: "Keyword yang sama",
  },
  co_authorship: {
    description:
      "Artikel terhubung ketika memiliki satu atau lebih penulis yang sama.",
    emptyText:
      "Tidak ada artikel dengan penulis yang sama dalam jaringan ini.",
    weightLabel: "penulis yang sama",
    detailLabel: "Penulis yang sama",
  },
};

function getRelationCopy(relationType: string) {
  return RELATION_COPY[relationType] ?? RELATION_COPY.bibliographic_coupling;
}

function getRelationItems(
  relationType: string,
  relation: SelectedRelations["connected"][number],
) {
  if (relationType === "keyword_cooccurrence") {
    return relation.sharedKeywords || [];
  }
  if (relationType === "co_authorship") {
    return relation.sharedAuthors || [];
  }
  return relation.sharedReferences || [];
}

export default function RelationDetails({
  selectedNode,
  selectedRelations,
  relationType,
  onSelectNode,
}: RelationDetailsProps) {
  const relationCopy = getRelationCopy(String(relationType || ""));

  return (
    <Card className="min-w-0 p-4">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Detail Relasi Artikel</h2>
        <p className="text-sm text-muted-foreground">
          {relationCopy.description}
        </p>
      </div>

      {!selectedNode ? (
        <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
          Pilih salah satu titik pada grafik untuk melihat artikel mana yang
          saling berelasi.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
            <p className="text-xs font-medium text-amber-700">
              Artikel dipilih
            </p>
            <p className="mt-1 font-semibold">
              {selectedNode.title || `Publication ${selectedNode.id}`}
            </p>
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-blue-700">
              Terhubung dengan {selectedRelations.connected.length} artikel
            </h3>
            {selectedRelations.connected.length > 0 ? (
              <div className="space-y-2">
                {selectedRelations.connected.map((relation) => {
                  const { node, weight } = relation;
                  const relationItems = getRelationItems(
                    String(relationType || ""),
                    relation,
                  );

                  return (
                  <button
                    key={`connected-${node.id}`}
                    type="button"
                    onClick={() => onSelectNode(node.id)}
                    className="flex w-full items-start gap-2 rounded-lg border p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
                  >
                    <Link2 className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                    <span className="min-w-0">
                      <span className="block text-sm">
                        <strong>{shortTitle(selectedNode.title, 48)}</strong>{" "}
                        memiliki relasi dengan{" "}
                        <strong>
                          {node.title || `Publication ${node.id}`}
                        </strong>
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        {weight} {relationCopy.weightLabel}
                      </span>
                      {relationItems.length > 0 && (
                        <span className="mt-2 block space-y-1 border-t pt-2">
                          <span className="block text-xs font-semibold text-slate-700">
                            {relationCopy.detailLabel}
                          </span>
                          {relationItems.map((item, index) => (
                            <span
                              key={`${node.id}-relation-item-${index}`}
                              className="block text-xs text-slate-600"
                            >
                              {index + 1}. {item}
                            </span>
                          ))}
                        </span>
                      )}
                    </span>
                  </button>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {relationCopy.emptyText}
              </p>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
