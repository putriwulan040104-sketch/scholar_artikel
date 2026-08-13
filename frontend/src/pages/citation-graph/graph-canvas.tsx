import { useEffect, useRef, useState, type RefObject } from "react";
import * as d3 from "d3";
import { Link2, MousePointerClick } from "lucide-react";
import { Card } from "@/components/ui/card";
import type {
  GraphLink,
  GraphModel,
  GraphNode,
  GraphTooltip,
  SelectedRelations,
} from "./citation-graph.types";
import {
  formatAuthors,
  getLinkNodeId,
  getNodeRadius,
  shortTitle,
} from "./citation-graph.utils";

const WIDTH = 1100;
const HEIGHT = 620;

interface GraphCanvasProps {
  graphModel: GraphModel;
  selectedNodeId: number | null;
  selectedRelations: SelectedRelations;
  loading: boolean;
  error: string;
  hasFilter: boolean;
  graphWrapRef: RefObject<HTMLDivElement | null>;
  onSelectNode: (nodeId: number | null) => void;
}

export default function GraphCanvas({
  graphModel,
  selectedNodeId,
  selectedRelations,
  loading,
  error,
  hasFilter,
  graphWrapRef,
  onSelectNode,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [tooltip, setTooltip] = useState<GraphTooltip>({
    visible: false,
    x: 0,
    y: 0,
    title: "",
    authors: "-",
    year: "-",
    relations: 0,
    references: 0,
    degreeCentrality: 0,
  });

  useEffect(() => {
    if (!svgRef.current || !graphModel.gNodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    svg.attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);

    const root = svg.append("g");
    const nodeById = new Map(graphModel.gNodes.map((node) => [node.id, node]));
    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.35, 3])
      .on("zoom", (event) => root.attr("transform", event.transform));
    svg.call(zoomBehavior);

    // membuat edge
    const link = root
      .append("g")
      .selectAll("line")
      .data(graphModel.gLinks)
      .join("line")
      .attr("stroke", (edge) => {
        const sourceId = getLinkNodeId(edge.source);
        const targetId = getLinkNodeId(edge.target);
        if (sourceId === selectedNodeId || targetId === selectedNodeId) {
          return "#2563eb";
        }
        return "#64748b";
      })
      .attr("stroke-opacity", (edge) => {
        if (selectedNodeId === null) return 0.55;
        const sourceId = getLinkNodeId(edge.source);
        const targetId = getLinkNodeId(edge.target);
        return sourceId === selectedNodeId || targetId === selectedNodeId
          ? 0.95
          : 0.1;
      })
      // ketebalan edge berdasarkan jumlah referensi bersama (weight)
      .attr("stroke-width", (edge) => {
        const sourceId = getLinkNodeId(edge.source);
        const targetId = getLinkNodeId(edge.target);
        const selected =
          sourceId === selectedNodeId || targetId === selectedNodeId;
        return Math.min(4, (selected ? 1 : 0.6) + edge.weight * 0.4);
      });

    // tooltip
    link.append("title").text((edge) => {
      const source = nodeById.get(getLinkNodeId(edge.source));
      const target = nodeById.get(getLinkNodeId(edge.target));
      return (
        `${source?.title || "Artikel"} dan ` +
        `${target?.title || "artikel"} — ` +
        `${edge.weight} referensi bersama` +
        (edge.edgeBetweenness > 0
          ? `\nEdge betweenness: ${edge.edgeBetweenness.toFixed(4)}`
          : "")
      );
    });

    // node
    const circles = root
      .append("g")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1.2)
      .selectAll<SVGCircleElement, GraphNode>("circle")
      .data(graphModel.gNodes)
      .join("circle")
      .attr("r", (node) => getNodeRadius(node.degreeCentrality))
      .attr("fill", (node) => {
        if (node.id === selectedNodeId) return "#f59e0b";
        if (
          selectedRelations.connected.some(
            (relation) => relation.node.id === node.id,
          )
        ) {
          return "#2563eb";
        }
        return "#64748b";
      })
      .attr("opacity", (node) => {
        if (selectedNodeId === null || node.id === selectedNodeId) return 1;
        const connected = selectedRelations.connected.some(
          (relation) => relation.node.id === node.id,
        );
        return connected ? 1 : 0.25;
      })
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 1.2)
      .style("cursor", "pointer")
      .on("click", (_event, node) => {
        onSelectNode(node.id === selectedNodeId ? null : node.id);
      });

    circles.append("title").text((node) => node.title || `Publication ${node.id}`);

    const labelNodes =
      selectedNodeId === null
        ? []
        : graphModel.gNodes.filter(
            (node) =>
              node.id === selectedNodeId ||
              selectedRelations.connected.some(
                (relation) => relation.node.id === node.id,
              ),
          );

    const labels = root
      .append("g")
      .selectAll("text")
      .data(labelNodes)
      .join("text")
      .attr("font-size", 11)
      .attr("font-weight", (node) => (node.id === selectedNodeId ? 700 : 500))
      .attr("fill", "#0f172a")
      .attr("paint-order", "stroke")
      .attr("stroke", "#ffffff")
      .attr("stroke-width", 4)
      .attr("stroke-linejoin", "round")
      .style("pointer-events", "none")
      .text((node) => shortTitle(node.title));

    circles.on("mousemove", (event, node) => {
        if (!graphWrapRef.current) return;
        const rect = graphWrapRef.current.getBoundingClientRect();
        setTooltip({
          visible: true,
          x: event.clientX - rect.left + 10,
          y: event.clientY - rect.top + 10,
          title: node.title || `Publication ${node.id}`,
          authors: formatAuthors(node.authors),
          year: node.year ? String(node.year) : "-",
          relations: graphModel.degreeById.get(node.id) || 0,
          references: Number(node.referenceCount || 0),
          degreeCentrality: node.degreeCentrality || 0,
        });
      })
      .on("mouseleave", () => {
        setTooltip((current) => ({ ...current, visible: false }));
      });

    const simulation = d3
      .forceSimulation<GraphNode>(graphModel.gNodes)
      .force(
        "link",
        d3
          .forceLink<GraphNode, GraphLink>(graphModel.gLinks)
          .id((node) => node.id)
          .distance((edge) => Math.max(40, 80 - edge.weight * 6))
          .strength(0.6),
      )
      .force("charge", d3.forceManyBody().strength(-50))
      .force("center", d3.forceCenter(WIDTH / 2, HEIGHT / 2))
      .force(
        "collision",
        d3.forceCollide<GraphNode>((node) => getNodeRadius(node.degreeCentrality) + 2),
      )
      .on("tick", () => {
        link
          .attr("x1", (edge) => (edge.source as GraphNode).x || 0)
          .attr("y1", (edge) => (edge.source as GraphNode).y || 0)
          .attr("x2", (edge) => (edge.target as GraphNode).x || 0)
          .attr("y2", (edge) => (edge.target as GraphNode).y || 0);

        // posisi node
        circles
          .attr("cx", (node) => node.x || 0)
          .attr("cy", (node) => node.y || 0);
        labels
          .attr("x", (node) => (node.x || 0) + getNodeRadius(node.degree) + 5)
          .attr("y", (node) => (node.y || 0) + 4);
      });

    const drag = d3
      .drag<SVGCircleElement, GraphNode>()
      .on("start", (event, node) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        node.fx = node.x;
        node.fy = node.y;
      })
      .on("drag", (event, node) => {
        node.fx = event.x;
        node.fy = event.y;
      })
      .on("end", (event, node) => {
        if (!event.active) simulation.alphaTarget(0);
        node.fx = null;
        node.fy = null;
      });

    circles.call(drag);

    if (selectedNodeId !== null) {
      const selectedNode = graphModel.gNodes.find(
        (node) => node.id === selectedNodeId,
      );
      if (selectedNode) {
        window.setTimeout(() => {
          const x = selectedNode.x ?? WIDTH / 2;
          const y = selectedNode.y ?? HEIGHT / 2;
          const scale = 1.6;
          const transform = d3.zoomIdentity
            .translate(WIDTH / 2 - x * scale, HEIGHT / 2 - y * scale)
            .scale(scale);
          svg
            .transition()
            .duration(650)
            .call(zoomBehavior.transform, transform);
        }, 350);
      }
    }

    return () => {
      simulation.stop();
      setTooltip((current) => ({ ...current, visible: false }));
    };
  }, [
    graphModel,
    graphWrapRef,
    onSelectNode,
    selectedNodeId,
    selectedRelations.connected,
  ]);

  return (
    <Card className="min-w-0 p-3">
      <div className="mb-3 flex flex-col gap-3 rounded-lg bg-slate-50 p-3 text-xs sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-muted-foreground">
          <MousePointerClick className="h-4 w-4 shrink-0" />
          Klik titik artikel untuk melihat referensi yang sama.
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            Artikel dipilih
          </span>
          <span className="inline-flex items-center gap-1.5 text-blue-700">
            <Link2 className="h-3.5 w-3.5" />
            Memiliki referensi yang sama
          </span>
        </div>
      </div>

      {loading ? (
        <div className="flex h-[620px] items-center justify-center text-sm text-muted-foreground">
          Memuat graph data...
        </div>
      ) : error ? (
        <div className="flex h-[620px] items-center justify-center text-sm text-red-500">
          {error}
        </div>
      ) : !graphModel.gNodes.length ? (
        <div className="flex h-[620px] items-center justify-center text-sm text-muted-foreground">
          {hasFilter
            ? "Belum ada kesamaan referensi pada hasil query ini."
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
              <p className="text-muted-foreground">
                Centrality: {(tooltip.degreeCentrality * 100).toFixed(1)}%
              </p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
