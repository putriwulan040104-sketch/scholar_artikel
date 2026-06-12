import type { FavoriteItem, GraphLink } from "./citation-graph.types";

const NODE_RADIUS_MIN = 5;
const NODE_RADIUS_MAX = 18;

export function readFavorites(): FavoriteItem[] {
  try {
    const raw = localStorage.getItem("favorites");
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeFavorites(items: FavoriteItem[]) {
  localStorage.setItem("favorites", JSON.stringify(items));
}

export function formatAuthors(raw: unknown): string {
  if (Array.isArray(raw)) {
    const names = raw
      .map((v) => (typeof v === "string" ? v.trim() : ""))
      .filter((v) => v);
    return names.length ? names.join(", ") : "-";
  }

  if (typeof raw === "string") {
    const s = raw.trim();
    if (!s) return "-";
    try {
      const parsed = JSON.parse(s);
      if (Array.isArray(parsed)) {
        const names = parsed
          .map((v) => (typeof v === "string" ? v.trim() : ""))
          .filter((v) => v);
        return names.length ? names.join(", ") : s;
      }
    } catch {
      return s;
    }
    return s;
  }

  return "-";
}

export function buildPageItems(
  current: number,
  total: number,
): Array<number | string> {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const items: Array<number | string> = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);

  if (start > 2) items.push("...");
  for (let p = start; p <= end; p += 1) items.push(p);
  if (end < total - 1) items.push("...");

  items.push(total);
  return items;
}

export function getNodeRadius(degree: number): number {
  const safeDegree = Number.isFinite(degree) ? Math.max(0, degree) : 0;
  const r = NODE_RADIUS_MIN + Math.sqrt(safeDegree) * 2.8;
  return Math.max(NODE_RADIUS_MIN, Math.min(NODE_RADIUS_MAX, r));
}

export function getLinkNodeId(
  value: GraphLink["source"] | GraphLink["target"],
) {
  return typeof value === "object" ? Number(value.id) : Number(value);
}

export function shortTitle(title?: string | null, maxLength = 34) {
  const value = title || "Artikel tanpa judul";
  return value.length > maxLength
    ? `${value.slice(0, maxLength - 1)}…`
    : value;
}
