import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import * as d3 from "d3";
import { ArrowLeft, ChevronLeft, ChevronRight, Quote, Star } from "lucide-react";
import {
  getCitationGraphData,
  searchArticles,
  type CitationGraphEdge,
  type CitationGraphNode,
} from "@/api/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type {
  FavoriteItem,
  GraphLink,
  GraphNode,
  GraphTooltip,
  QueryArticleLite,
  StoredFilters,
} from "./citation-graph.types";
import {
  buildPageItems,
  formatAuthors,
  getNodeRadius,
  readFavorites,
  writeFavorites,
} from "./citation-graph.utils";

const WIDTH = 1100;
const HEIGHT = 620;
const LIST_PAGE_SIZE = 5;
const GRAPH_QUERY_TOP_K = 5000;

export default function CitationGraphPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const svgRef = useRef<SVGSVGElement | null>(null);
  const graphWrapRef = useRef<HTMLDivElement | null>(null);

  const stateIds =
    (location.state as { sourcePublicationIds?: number[] } | null)
      ?.sourcePublicationIds || [];
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [queryMatchedIds, setQueryMatchedIds] = useState<number[]>([]);
  const [queryArticles, setQueryArticles] = useState<QueryArticleLite[]>([]);
  const [queryTotalMatched, setQueryTotalMatched] = useState<number>(0);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("lastSearchPublicationIds");
      const parsed = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed)) {
        setSavedIds(
          parsed.map((id) => Number(id)).filter((id) => Number.isFinite(id)),
        );
      } else {
        setSavedIds([]);
      }
    } catch (_error) {
      setSavedIds([]);
    }
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
        let kategori: string | undefined;
        let jumlahKemunculan: string | undefined;
        const rawFilters = localStorage.getItem("lastSearchFilters");
        if (rawFilters) {
          const parsed = JSON.parse(rawFilters) as StoredFilters;
          if (parsed?.yearStart) yearStart = Number(parsed.yearStart);
          if (parsed?.yearEnd) yearEnd = Number(parsed.yearEnd);
          if (parsed?.jenisArtikel) jenisArtikel = parsed.jenisArtikel;
          if (parsed?.kategori) kategori = parsed.kategori;
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
          kategori,
          jumlahKemunculan,
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

        // Simpan konteks terbaru agar sidebar / page lain sinkron
        localStorage.setItem("lastSearchPublicationIds", JSON.stringify(ids));
        window.dispatchEvent(new Event("search-context-updated"));
      } catch (_error) {
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
  const [listPage, setListPage] = useState(1);
  const [favoriteIds, setFavoriteIds] = useState<Set<number>>(new Set());
  const [tooltip, setTooltip] = useState<GraphTooltip>({
    visible: false,
    x: 0,
    y: 0,
    title: "",
    authors: "-",
    year: "-",
    citations: 0,
    references: 0,
  });
  const [nodes, setNodes] = useState<CitationGraphNode[]>([]);
  const [edges, setEdges] = useState<CitationGraphEdge[]>([]);
  const [selectedNodeId, setSelectedNodeId] = useState<number | null>(null);

  useEffect(() => {
    const favorites = readFavorites();
    setFavoriteIds(new Set(favorites.map((item) => Number(item.id))));
  }, []);

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

      const res = await getCitationGraphData(activeArticleIds);
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
  }, [activeArticleIds]);

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

  useEffect(() => {
    if (!svgRef.current || !graphModel.gNodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);

    const root = svg.append("g");

    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.35, 3])
      .on("zoom", (event) => root.attr("transform", event.transform));

    svg.call(zoomBehavior);

    const link = root
      .append("g")
      .attr("stroke", "#64748b")
      .attr("stroke-opacity", 0.45)
      .selectAll("line")
      .data(graphModel.gLinks)
      .join("line")
      .attr("stroke-width", (d) => Math.min(3, 0.8 + d.weight * 0.35));

    root
      .append("g")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1.2)
      .selectAll("circle")
      .data(graphModel.gNodes)
      .join("circle")
      .attr("r", (d) => getNodeRadius(d.degree))
      .attr("fill", "#1d4ed8")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1.2)
      .append("title")
      .text((d) => d.title || `Publication ${d.id}`);

    const circles = root.selectAll<SVGCircleElement, GraphNode>("circle");

    circles
      .on("mousemove", (event, d) => {
        if (!graphWrapRef.current) return;
        const rect = graphWrapRef.current.getBoundingClientRect();
        const inCount = graphModel.inDegreeById.get(d.id) || 0;
        setTooltip({
          visible: true,
          x: event.clientX - rect.left + 10,
          y: event.clientY - rect.top + 10,
          title: d.title || `Publication ${d.id}`,
          authors: formatAuthors(d.authors),
          year: d.year ? String(d.year) : "-",
          citations: inCount,
          references: Number(d.referenceCount || 0),
        });
      })
      .on("mouseleave", () => {
        setTooltip((prev) => ({ ...prev, visible: false }));
      });

    const simulation = d3
      .forceSimulation<GraphNode>(graphModel.gNodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>(graphModel.gLinks)
          .id((d) => d.id)
          .distance((d) => Math.max(70, 130 - d.weight * 10))
          .strength(0.6),
      )
      .force("charge", d3.forceManyBody().strength(-260))
      .force("center", d3.forceCenter(WIDTH / 2, HEIGHT / 2))
      .force(
        "collision",
        d3.forceCollide<GraphNode>((d) => getNodeRadius(d.degree) + 2),
      )
      .on("tick", () => {
        link
          .attr("x1", (d) => (d.source as GraphNode).x || 0)
          .attr("y1", (d) => (d.source as GraphNode).y || 0)
          .attr("x2", (d) => (d.target as GraphNode).x || 0)
          .attr("y2", (d) => (d.target as GraphNode).y || 0);

        circles.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);
      });

    const drag = d3
      .drag<SVGCircleElement, GraphNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    circles.call(drag);

    if (selectedNodeId !== null) {
      const selectedNode = graphModel.gNodes.find((n) => n.id === selectedNodeId);
      if (selectedNode) {
        const focusNode = () => {
          const x = selectedNode.x ?? WIDTH / 2;
          const y = selectedNode.y ?? HEIGHT / 2;
          const scale = 1.6;
          const transform = d3.zoomIdentity
            .translate(WIDTH / 2 - x * scale, HEIGHT / 2 - y * scale)
            .scale(scale);

          svg
            .transition()
            .duration(650)
            .call(
              zoomBehavior.transform,
              transform,
            );
        };

        window.setTimeout(focusNode, 350);
      }
    }

    return () => {
      simulation.stop();
      setTooltip((prev) => ({ ...prev, visible: false }));
    };
  }, [graphModel, selectedNodeId]);

  const rankedNodes = useMemo(
    () =>
      [...graphModel.gNodes].sort((a, b) => {
        const aIn = graphModel.inDegreeById.get(a.id) || 0;
        const bIn = graphModel.inDegreeById.get(b.id) || 0;
        if (bIn !== aIn) return bIn - aIn;
        return b.degree - a.degree;
      }),
    [graphModel],
  );

  const totalListPages = Math.max(
    1,
    Math.ceil(rankedNodes.length / LIST_PAGE_SIZE),
  );

  useEffect(() => {
    if (listPage > totalListPages) {
      setListPage(totalListPages);
    }
  }, [listPage, totalListPages]);

  const pagedNodes = useMemo(() => {
    const start = (listPage - 1) * LIST_PAGE_SIZE;
    return rankedNodes.slice(start, start + LIST_PAGE_SIZE);
  }, [rankedNodes, listPage]);

  const pageItems = useMemo(
    () => buildPageItems(listPage, totalListPages),
    [listPage, totalListPages],
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

    const inCount = graphModel.inDegreeById.get(node.id) || 0;
    const outCount = graphModel.outDegreeById.get(node.id) || 0;
    const score = inCount + outCount;

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
        <h1 className="text-xl font-semibold">Jaringan Sitasi</h1>
        <p className="text-sm text-muted-foreground">
          Visualisasi relasi sitasi antar publikasi.
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
          <p className="text-sm text-muted-foreground">Total Relasi Sitasi</p>
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

      <Card className="p-3">
        {loading ? (
          <div className="flex h-[620px] items-center justify-center text-sm text-muted-foreground">
            Memuat graph data...
          </div>
        ) : error ? (
          <div className="flex h-[620px] items-center justify-center text-sm text-red-500">
            {error}
          </div>
        ) : !displayNodes.length ? (
          <div className="flex h-[620px] items-center justify-center text-sm text-muted-foreground">
            {filterIds.size
              ? "Belum ada relasi sitasi pada hasil query ini."
              : "Belum ada hasil query. Silakan lakukan pencarian dulu."}
          </div>
        ) : (
          <div ref={graphWrapRef} className="relative w-full overflow-auto">
            <svg
              ref={svgRef}
              className="h-[620px] w-full min-w-[980px] cursor-grab active:cursor-grabbing"
            />
            {tooltip.visible && (
              <div
                className="pointer-events-none absolute z-20 w-[280px] rounded-md border bg-white p-3 text-xs shadow-lg"
                style={{ left: tooltip.x, top: tooltip.y }}
              >
                <p className="line-clamp-2 text-sm font-semibold">
                  {tooltip.title}
                </p>
                <p className="mt-1 text-muted-foreground">
                  Authors: {tooltip.authors}
                </p>
                <p className="text-muted-foreground">Year: {tooltip.year}</p>
              </div>
            )}
          </div>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="mb-4 text-2xl font-semibold">Artikel Teratas</h2>
        {!pagedNodes.length ? (
          <p className="text-sm text-muted-foreground">Belum ada data.</p>
        ) : (
          <div className="space-y-3">
            {pagedNodes.map((n) => {
              const inCount = graphModel.inDegreeById.get(n.id) || 0;
              const referenceCount = Number(n.referenceCount || 0);
              return (
                <div
                  key={n.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => focusNodeFromList(n)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      focusNodeFromList(n);
                    }
                  }}
                  className="rounded-lg border bg-white px-4 py-3 text-left transition hover:border-blue-300 hover:bg-blue-50/40"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <p className="line-clamp-2 text-base font-semibold">
                        {n.title || `Publication ${n.id}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Authors: {formatAuthors(n.authors)} | Year:{" "}
                        {n.year ?? "-"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        DOI: {n.doi || "-"}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        toggleFavorite(n);
                      }}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-md border text-slate-500 hover:bg-slate-50"
                    >
                      <Star
                        className={`h-3.5 w-3.5 ${
                          favoriteIds.has(n.id)
                            ? "fill-yellow-400 text-yellow-400"
                            : ""
                        }`}
                      />
                    </button>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-indigo-600">
                    <span className="inline-flex items-center gap-1">
                      <Quote className="h-3 w-3" />
                      {inCount} Sitasi
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Quote className="h-3 w-3" />
                      {referenceCount} Referensi
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {totalListPages > 1 && (
          <div className="mt-5 flex items-center justify-center gap-2">
            <button
              type="button"
              onClick={() => setListPage((p) => Math.max(1, p - 1))}
              disabled={listPage <= 1}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            {pageItems.map((item, idx) =>
              item === "..." ? (
                <span
                  key={`ellipsis-${idx}`}
                  className="px-1 text-sm text-muted-foreground"
                >
                  ...
                </span>
              ) : (
                <button
                  key={`page-${item}`}
                  type="button"
                  onClick={() => setListPage(Number(item))}
                  className={`inline-flex h-8 min-w-8 items-center justify-center rounded-md border px-2 text-sm ${
                    listPage === item
                      ? "bg-blue-500 text-white border-blue-500"
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
                setListPage((p) => Math.min(totalListPages, p + 1))
              }
              disabled={listPage >= totalListPages}
              className="inline-flex h-8 w-8 items-center justify-center rounded-md border disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
