import { ArrowRight } from "lucide-react";
import { Card } from "@/components/ui/card";
import type {
  GraphNode,
  SelectedRelations,
} from "./citation-graph.types";
import { shortTitle } from "./citation-graph.utils";

interface RelationDetailsProps {
  selectedNode: GraphNode | null;
  selectedRelations: SelectedRelations;
  onSelectNode: (nodeId: number) => void;
}

export default function RelationDetails({
  selectedNode,
  selectedRelations,
  onSelectNode,
}: RelationDetailsProps) {
  return (
    <Card className="min-w-0 p-4">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Detail Relasi Artikel</h2>
        <p className="text-sm text-muted-foreground">
          Arah panah dibaca dari artikel pengutip menuju artikel yang dikutip.
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
              Mengutip {selectedRelations.outgoing.length} artikel
            </h3>
            {selectedRelations.outgoing.length > 0 ? (
              <div className="space-y-2">
                {selectedRelations.outgoing.map(({ node, weight }) => (
                  <button
                    key={`outgoing-${node.id}`}
                    type="button"
                    onClick={() => onSelectNode(node.id)}
                    className="flex w-full items-start gap-2 rounded-lg border p-3 text-left transition hover:border-blue-300 hover:bg-blue-50"
                  >
                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" />
                    <span className="min-w-0">
                      <span className="block text-sm">
                        <strong>{shortTitle(selectedNode.title, 48)}</strong>{" "}
                        mengutip{" "}
                        <strong>
                          {node.title || `Publication ${node.id}`}
                        </strong>
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        Bobot relasi: {weight}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Tidak ada referensi ke artikel lain dalam jaringan ini.
              </p>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-semibold text-emerald-700">
              Dikutip oleh {selectedRelations.incoming.length} artikel
            </h3>
            {selectedRelations.incoming.length > 0 ? (
              <div className="space-y-2">
                {selectedRelations.incoming.map(({ node, weight }) => (
                  <button
                    key={`incoming-${node.id}`}
                    type="button"
                    onClick={() => onSelectNode(node.id)}
                    className="flex w-full items-start gap-2 rounded-lg border p-3 text-left transition hover:border-emerald-300 hover:bg-emerald-50"
                  >
                    <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                    <span className="min-w-0">
                      <span className="block text-sm">
                        <strong>
                          {node.title || `Publication ${node.id}`}
                        </strong>{" "}
                        mengutip{" "}
                        <strong>{shortTitle(selectedNode.title, 48)}</strong>
                      </span>
                      <span className="mt-1 block text-xs text-muted-foreground">
                        Bobot relasi: {weight}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Belum ada artikel dalam jaringan ini yang mengutipnya.
              </p>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
