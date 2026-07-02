import { getUser } from "@/api/api";

export interface StoredFavoriteItem {
  id: number | string;
}

const FAVORITES_KEY_PREFIX = "favorites";

export function getFavoritesStorageKey() {
  const user = getUser();
  const userId = user?.id ?? user?.user_id ?? user?.email;

  if (!userId) {
    return `${FAVORITES_KEY_PREFIX}:guest`;
  }

  return `${FAVORITES_KEY_PREFIX}:${String(userId)}`;
}

export function readFavorites<T extends StoredFavoriteItem = StoredFavoriteItem>(): T[] {
  try {
    const raw = localStorage.getItem(getFavoritesStorageKey());
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeFavorites<T extends StoredFavoriteItem>(items: T[]) {
  localStorage.setItem(getFavoritesStorageKey(), JSON.stringify(items));
  window.dispatchEvent(new Event("favorites-updated"));
}

export function isFavoriteArticle(id: number | string) {
  const articleId = Number(id);
  if (!Number.isFinite(articleId)) return false;

  return readFavorites().some((item) => Number(item.id) === articleId);
}

export function toggleFavoriteItem<T extends StoredFavoriteItem>(item: T): T[] {
  const articleId = Number(item.id);
  const current = readFavorites<T>();
  const exists = current.some((favorite) => Number(favorite.id) === articleId);
  const next = exists
    ? current.filter((favorite) => Number(favorite.id) !== articleId)
    : [...current, item];

  writeFavorites(next);
  return next;
}
