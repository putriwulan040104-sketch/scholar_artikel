import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import {
  getCitationGraphData,
  searchArticles,
  type ArticleRelationType,
  type CitationGraphEdge,
  type CitationGraphNode,
} from "@/api/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type {
  FavoriteItem,
  GraphLink,
  GraphNode,
  QueryArticleLite,
  StoredFilters,
} from "./citation-graph.types";
import {
  formatAuthors,
  getLinkNodeId,
  readFavorites,
  writeFavorites,
} from "./citation-graph.utils";
import GraphCanvas from "./graph-canvas";
import RelationDetails from "./relation-details";
import TopArticles from "./top-articles";

const GRAPH_QUERY_TOP_K = 5000;

export default function CitationGraphPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const graphWrapRef = useRef<HTMLDivElement | null>(null);
  const autoFocusedGraphRef = useRef("");

  const stateIds =
    (location.state as { sourcePublicationIds?: number[] } | null)
      ?.sourcePublicationIds || [];
  const [savedIds, setSavedIds] = useState<number[]>(() => {
    try {
      const raw = localStorage.getItem("lastSearchPublicationIds");
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed)
        ? parsed
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id))
        : [];
    } catch {
      return [];
    }
  });
  const [queryMatchedIds, setQueryMatchedIds] = useState<number[]>([]);
  const [queryArticles, setQueryArticles] = useState<QueryArticleLite[]>([]);
  const [queryTotalMatched, setQueryTotalMatched] = useState<number>(0);
  const [relationType, setRelationType] = useState<ArticleRelationType>(
    "bibliographic_coupling",
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      try {
        const raw = localStorage.getItem("lastSearchPublicationIds");
        const parsed = raw ? JSON.parse(raw) : [];
        if (Array.isArray(parsed)) {
          setSavedIds(
            parsed
              .map((id) => Number(id))
              .filter((id) => Number.isFinite(id)),
          );
        } else {
          setSavedIds([]);
        }
      } catch {
        setSavedIds([]);
      }
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [location.key]);

  useEffect(() => {
    const run = async () => {
      try {
        const query = (localStorage.getItem("lastSearchQuery") || "").trim();
        if (!query) {
          setQueryMatchedIds([]);
          return;
        }

        let yearStart: number | undefined;
        let yearEnd: number | undefined;
        let jenisArtikel: string | undefined;
        let jenisAnalisis: ArticleRelationType | undefined;
        let jumlahKemunculan: string | undefined;
        const rawFilters = localStorage.getItem("lastSearchFilters");
        if (rawFilters) {
          const parsed = JSON.parse(rawFilters) as StoredFilters;
          if (parsed?.yearStart) yearStart = Number(parsed.yearStart);
          if (parsed?.yearEnd) yearEnd = Number(parsed.yearEnd);
          if (parsed?.jenisArtikel) jenisArtikel = parsed.jenisArtikel;
          if (parsed?.jenisAnalisis) {
            jenisAnalisis = parsed.jenisAnalisis as ArticleRelationType;
            setRelationType(jenisAnalisis);
          } else {
            setRelationType("bibliographic_coupling");
          }
          if (parsed?.jumlahKemunculan) {
            jumlahKemunculan = parsed.jumlahKemunculan;
          }
        }

        const res = await searchArticles(
          query,
          GRAPH_QUERY_TOP_K,
          yearStart,
          yearEnd,
          jenisArtikel,
          undefined,
          jumlahKemunculan,
          undefined,
          jenisAnalisis,
        );
        if (res.status !== "success" || !Array.isArray(res.data)) {
          setQueryMatchedIds([]);
          setQueryArticles([]);
          setQueryTotalMatched(0);
          return;
        }

        const ids = res.data
          .map((item: { id?: number | string }) => Number(item.id))
          .filter((id: number) => Number.isFinite(id));
        const normalizedArticles: QueryArticleLite[] = res.data
          .map(
            (item: {
              id?: number | string;
              title?: string;
              authors?: string[] | string;
              year?: number | string;
              doi?: string;
            }) => ({
              id: Number(item.id),
              title: item.title || null,
              authors: item.authors || null,
              year:
                item.year !== undefined && item.year !== null && item.year !== ""
                  ? Number(item.year)
                  : null,
              doi: item.doi || null,
            }),
          )
          .filter((item) => Number.isFinite(item.id));

        setQueryMatchedIds(ids);
        setQueryArticles(normalizedArticles);
        setQueryTotalMatched(
          Number(
            res.total_matched ?? res.total ?? normalizedArticles.length ?? 0,
          ) || 0,
        );

        localStorage.setItem("lastSearchPublicationIds", JSON.stringify(ids));
        window.dispatchEvent(new Event("search-context-updated"));
      } catch {
        setQueryMatchedIds([]);
        setQueryArticles([]);
        setQueryTotalMatched(0);
      }
    };

    run();
  }, [location.key]);

  const activeIds = stateIds.length
    ? stateIds
    : queryMatchedIds.length
      ? queryMatchedIds
      : savedIds;
  const activeArticleIds = useMemo(
    () =>
      Array.from(
        new Set(
          (activeIds || [])
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id)),
        ),
      ),
    [activeIds],
  );
  const filterIds = useMemo(
    () =>
      new Set(
        activeArticleIds,
      ),
    [activeArticleIds],
  );

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(
    () => new Set(readFavorites().map((item) => Number(item.id))),
  );
  const [nodes, setNodes] = useState<CitationGraphNode[]>([]);
  const [edges, setEdges] = useState<CitationGraphEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      setError("");
      if (!activeArticleIds.length) {
        setNodes([]);
        setEdges([]);
        setLoading(false);
        return;
      }

      const res = await getCitationGraphData(activeArticleIds, relationType);
      if (res.status === "error") {
        setError(res.message || "Gagal memuat graph.");
        setLoading(false);
        return;
      }
      const graphData = res.data || { nodes: [], edges: [] };
      setNodes(graphData.nodes || []);
      setEdges(graphData.edges || []);
      setLoading(false);
    };
    run();
  }, [activeArticleIds, relationType]);

  const displayNodes = useMemo(() => {
    if (!filterIds.size) return [];

    const matchedGraphNodes = nodes.filter((n) => {
      const articleId = Number(n.article_id);
      if (Number.isFinite(articleId)) {
        return filterIds.has(articleId);
      }

      const publicationId = Number(n.id);
      return filterIds.has(publicationId);
    });
    const usedArticleIds = new Set(
      matchedGraphNodes
        .map((n) => Number(n.article_id))
        .filter((id) => Number.isFinite(id)),
    );
    const usedNodeIds = new Set(
      matchedGraphNodes
        .map((n) => Number(n.id))
        .filter((id) => Number.isFinite(id)),
    );

    const syntheticNodes: CitationGraphNode[] = queryArticles
      .filter((a) => Number.isFinite(a.id))
      .filter((a) => !usedArticleIds.has(a.id) && !usedNodeIds.has(a.id))
      .map((a) => ({
        // pakai negatif supaya tidak bentrok dengan id node graph
        id: -Math.abs(a.id),
        article_id: a.id,
        title: a.title || `Publication ${a.id}`,
        year: a.year ?? null,
        doi: a.doi ?? null,
        authors: a.authors ?? null,
        reference_count: 0,
      }));

    return [...matchedGraphNodes, ...syntheticNodes];
  }, [nodes, filterIds, queryArticles]);

  const displayEdges = useMemo(() => {
    if (!displayNodes.length) return [];
    const nodeIds = new Set(
      displayNodes.map((n) => Number(n.id)).filter((id) => Number.isFinite(id)),
    );
    return edges.filter(
      (e) => nodeIds.has(Number(e.source)) && nodeIds.has(Number(e.target)),
    );
  }, [edges, displayNodes]);

  const graphModel = useMemo(() => {
    const degreeById = new Map<number, number>();
    const inDegreeById = new Map<number, number>();
    const outDegreeById = new Map<number, number>();

    for (const n of displayNodes) degreeById.set(Number(n.id), 0);
    for (const n of displayNodes) {
      const id = Number(n.id);
      inDegreeById.set(id, 0);
      outDegreeById.set(id, 0);
    }

    for (const e of displayEdges) {
      const s = Number(e.source);
      const t = Number(e.target);
      degreeById.set(s, (degreeById.get(s) || 0) + 1);
      degreeById.set(t, (degreeById.get(t) || 0) + 1);
      outDegreeById.set(s, (outDegreeById.get(s) || 0) + 1);
      inDegreeById.set(t, (inDegreeById.get(t) || 0) + 1);
    }

    const gNodes: GraphNode[] = displayNodes.map((n) => ({
      id: Number(n.id),
      articleId: n.article_id ?? null,
      title: n.title || null,
      year: n.year ?? null,
      doi: n.doi ?? null,
      authors: n.authors ?? null,
      referenceCount: Number(n.reference_count || 0),
      degree: degreeById.get(Number(n.id)) || 0,
    }));

    const nodeIdSet = new Set(gNodes.map((n) => n.id));
    const gLinks: GraphLink[] = displayEdges
      .map((e) => ({
        source: Number(e.source),
        target: Number(e.target),
        weight: Number(e.weight || 1),
        sharedReferences: e.details?.shared_references || [],
        sharedKeywords: e.details?.shared_keywords || [],
        sharedAuthors: e.details?.shared_authors || [],
        relationType: e.relation_type || relationType,
      }))
      .filter(
        (e) =>
          Number.isFinite(Number(e.source)) &&
          Number.isFinite(Number(e.target)) &&
          nodeIdSet.has(Number(e.source)) &&
          nodeIdSet.has(Number(e.target)),
      );

    return { gNodes, gLinks, degreeById, inDegreeById, outDegreeById };
  }, [displayNodes, displayEdges]);

  const nodeById = useMemo(
    () => new Map(graphModel.gNodes.map((node) => [node.id, node])),
    [graphModel.gNodes],
  );

  const graphIdentity = useMemo(
    () =>
      [
        graphModel.gNodes.map((node) => node.id).join(","),
        graphModel.gLinks
          .map(
            (link) =>
              `${getLinkNodeId(link.source)}-${getLinkNodeId(link.target)}`,
          )
          .join(","),
      ].join("|"),
    [graphModel.gLinks, graphModel.gNodes],
  );

  useEffect(() => {
    if (!graphIdentity || autoFocusedGraphRef.current === graphIdentity) return;

    autoFocusedGraphRef.current = graphIdentity;
    const mostConnectedNode = [...graphModel.gNodes]
      .filter((node) => node.degree > 0)
      .sort((left, right) => right.degree - left.degree)[0];

    const timeoutId = window.setTimeout(() => {
      setSelectedNodeId(mostConnectedNode?.id ?? null);
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [graphIdentity, graphModel]);

  const selectedNode = useMemo(
    () =>
      selectedNodeId === null
        ? null
        : nodeById.get(selectedNodeId) || null,
    [nodeById, selectedNodeId],
  );

  const selectedRelations = useMemo(() => {
    if (selectedNodeId === null) {
      return { connected: [] };
    }

    const connected = graphModel.gLinks
      .filter((link) => {
        const sourceId = getLinkNodeId(link.source);
        const targetId = getLinkNodeId(link.target);
        return sourceId === selectedNodeId || targetId === selectedNodeId;
      })
      .map((link) => {
        const sourceId = getLinkNodeId(link.source);
        const otherId =
          sourceId === selectedNodeId
            ? getLinkNodeId(link.target)
            : sourceId;
        return {
          node: nodeById.get(otherId),
          weight: link.weight,
          sharedReferences: link.sharedReferences,
          sharedKeywords: link.sharedKeywords,
          sharedAuthors: link.sharedAuthors,
          relationType: link.relationType || null,
        };
      })
      .filter(
        (
          relation,
        ): relation is {
          node: GraphNode;
          weight: number;
          sharedReferences: string[];
          sharedKeywords: string[];
          sharedAuthors: string[];
          relationType: string | null;
        } =>
          Boolean(relation.node),
      )
      .sort((left, right) => right.weight - left.weight);

    return { connected };
  }, [graphModel.gLinks, nodeById, selectedNodeId]);

  const connectedNodeIds = useMemo(
    () =>
      new Set(
        selectedRelations.connected.map((relation) => relation.node.id),
      ),
    [selectedRelations.connected],
  );

  const toggleFavorite = (node: GraphNode) => {
    const current = readFavorites();
    const exists = current.some((item) => Number(item.id) === Number(node.id));

    if (exists) {
      const updated = current.filter(
        (item) => Number(item.id) !== Number(node.id),
      );
      writeFavorites(updated);
      setFavoriteIds(new Set(updated.map((item) => Number(item.id))));
      return;
    }

    const score = graphModel.degreeById.get(node.id) || 0;

    const payload: FavoriteItem = {
      id: node.id,
      title: node.title || `Publication ${node.id}`,
      authors: formatAuthors(node.authors),
      year: node.year ?? undefined,
      similarity_score: score,
      pdf_url: null,
      url: null,
      access_url: null,
      is_pdf: false,
    };

    const updated = [...current, payload];
    writeFavorites(updated);
    setFavoriteIds(new Set(updated.map((item) => Number(item.id))));
  };

  const focusNodeFromList = (node: GraphNode) => {
    setSelectedNodeId(node.id);
    graphWrapRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };

  return (
    <div className="space-y-4">
      <Button
        variant="ghost"
        className="mb-6 gap-2 text-muted-foreground"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft className="w-4 h-4" />
        Kembali
      </Button>
      <div>
        <h1 className="text-xl font-semibold">Jaringan Relasi Artikel</h1>
        <p className="text-sm text-muted-foreground">
          Visualisasi hubungan artikel berdasarkan referensi yang sama.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-3 md:grid-cols-3">
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Total Publikasi</p>
          <p className="text-2xl font-semibold">
            {queryTotalMatched > 0 ? queryTotalMatched : displayNodes.length}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Total Relasi Artikel</p>
          <p className="text-2xl font-semibold">{displayEdges.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-muted-foreground">Rata-rata Degree</p>
          <p className="text-2xl font-semibold">
            {displayNodes.length
              ? ((displayEdges.length * 2) / displayNodes.length).toFixed(2)
              : "0.00"}
          </p>
        </Card>
      </div>

      <GraphCanvas
        graphModel={graphModel}
        selectedNodeId={selectedNodeId}
        selectedRelations={selectedRelations}
        loading={loading}
        error={error}
        hasFilter={filterIds.size > 0}
        graphWrapRef={graphWrapRef}
        onSelectNode={setSelectedNodeId}
      />

      <RelationDetails
        selectedNode={selectedNode}
        selectedRelations={selectedRelations}
        relationType={relationType}
        onSelectNode={setSelectedNodeId}
      />

      <TopArticles
        graphModel={graphModel}
        favoriteIds={favoriteIds}
        selectedNodeId={selectedNodeId}
        connectedNodeIds={connectedNodeIds}
        onFocusNode={focusNodeFromList}
        onToggleFavorite={toggleFavorite}
      />
    </div>
  );
}
