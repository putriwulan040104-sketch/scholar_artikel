import { getUser } from "@/api/api";

const SEARCH_HISTORY_KEY_PREFIX = "search_history";
const SEARCH_HISTORY_LIMIT = 6;

export function getSearchHistoryStorageKey() {
  const user = getUser();
  const userId = user?.id ?? user?.user_id ?? user?.email;

  if (!userId) {
    return `${SEARCH_HISTORY_KEY_PREFIX}:guest`;
  }

  return `${SEARCH_HISTORY_KEY_PREFIX}:${String(userId)}`;
}

export function readSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(getSearchHistoryStorageKey());
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed)
      ? parsed.map((item) => String(item).trim()).filter(Boolean)
      : [];
  } catch {
    return [];
  }
}

export function writeSearchHistory(items: string[]) {
  const cleaned = items
    .map((item) => String(item).trim())
    .filter(Boolean)
    .slice(0, SEARCH_HISTORY_LIMIT);

  localStorage.setItem(getSearchHistoryStorageKey(), JSON.stringify(cleaned));
  window.dispatchEvent(new Event("search-history-updated"));
}

export function addSearchHistory(keyword: string) {
  const clean = keyword.trim();
  if (!clean) return readSearchHistory();

  const current = readSearchHistory();
  const updated = [
    clean,
    ...current.filter((item) => item.toLowerCase() !== clean.toLowerCase()),
  ].slice(0, SEARCH_HISTORY_LIMIT);

  writeSearchHistory(updated);
  return updated;
}
