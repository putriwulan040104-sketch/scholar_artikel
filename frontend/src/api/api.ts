const BASE_URL = "http://127.0.0.1:5000/api";

// Auth
export async function login(email: string, password: string) {
  try {
    const res = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) return { status: "error", message: data.message || "Login gagal" };
    if (data.token) {
      localStorage.setItem("token", data.token);
      localStorage.setItem("user", JSON.stringify(data.data));
    }
    return data;
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export async function register(name: string, email: string, password: string) {
  try {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (!res.ok) return { status: "error", message: data.message || "Register gagal" };
    return data;
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export function logout() {
  const token = getToken();
  if (token) {
    void fetch(`${BASE_URL}/auth/logout`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      keepalive: true,
    }).catch(() => undefined);
  }

  localStorage.removeItem("token");
  localStorage.removeItem("user");
  localStorage.removeItem("lastSearchPublicationIds");
  localStorage.removeItem("lastSearchQuery");
  localStorage.removeItem("lastSearchFilters");
  window.dispatchEvent(new Event("search-context-updated"));
}

export function getToken() {
  return localStorage.getItem("token");
}

export function getUser() {
  const user = localStorage.getItem("user");
  return user ? JSON.parse(user) : null;
}

export function isSuperAdmin() {
  const user = getUser();
  const role = String(user?.role || "")
    .trim()
    .toLowerCase()
    .replaceAll("-", "_")
    .replaceAll(" ", "_");

  return role === "super_admin";
}

export interface ManagedUser {
  id: string | number;
  name?: string | null;
  email?: string | null;
  avatarUrl?: string | null;
  role?: string | null;
  createdAt?: string | null;
}

export interface UserMutationPayload {
  name: string;
  email: string;
  role: string;
  password?: string;
}

async function requestWithToken(url: string, options: RequestInit = {}) {
  const token = getToken();
  if (!token) {
    return {
      ok: false,
      data: {
        status: "error",
        message: "Token tidak ditemukan",
      },
    };
  }

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  };

  const res = await fetch(url, {
    ...options,
    headers,
  });
  const data = await res.json();

  return {
    ok: res.ok,
    data,
  };
}

export async function getUsers(): Promise<{
  status: string;
  data?: ManagedUser[];
  total?: number;
  message?: string;
}> {
  const token = getToken();
  if (!token) {
    return {
      status: "error",
      message: "Token tidak ditemukan",
    };
  }

  try {
    const res = await fetch(`${BASE_URL}/users`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await res.json();
    if (!res.ok) {
      return {
        status: "error",
        message: data.message || "Gagal mengambil data pengguna",
      };
    }

    return {
      status: "success",
      data: Array.isArray(data?.data) ? data.data : [],
      total: Number(data?.total ?? 0),
    };
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function createUser(payload: UserMutationPayload): Promise<{
  status: string;
  data?: ManagedUser;
  message?: string;
}> {
  try {
    const { ok, data } = await requestWithToken(`${BASE_URL}/users`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (!ok) {
      return {
        status: "error",
        message: data.message || "Gagal menambahkan user",
      };
    }

    return data;
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function updateUser(
  userId: string | number,
  payload: UserMutationPayload,
): Promise<{
  status: string;
  data?: ManagedUser;
  message?: string;
}> {
  try {
    const { ok, data } = await requestWithToken(`${BASE_URL}/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });

    if (!ok) {
      return {
        status: "error",
        message: data.message || "Gagal memperbarui user",
      };
    }

    return data;
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function deleteUser(userId: string | number): Promise<{
  status: string;
  data?: ManagedUser;
  message?: string;
}> {
  try {
    const { ok, data } = await requestWithToken(`${BASE_URL}/users/${userId}`, {
      method: "DELETE",
    });

    if (!ok) {
      return {
        status: "error",
        message: data.message || "Gagal menghapus user",
      };
    }

    return data;
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export type ArticleRequestStatus = "pending" | "processing" | "done" | "rejected";

export interface ArticleRequest {
  id: string | number;
  nama?: string | null;
  email?: string | null;
  kataKunci?: string | null;
  judulArtikel?: string | null;
  keterangan?: string | null;
  status?: ArticleRequestStatus | string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export async function getArticleRequests(): Promise<{
  status: string;
  data?: ArticleRequest[];
  total?: number;
  message?: string;
}> {
  try {
    const { ok, data } = await requestWithToken(`${BASE_URL}/article-requests`);

    if (!ok) {
      return {
        status: "error",
        message: data.message || "Gagal mengambil data request artikel",
      };
    }

    return {
      status: "success",
      data: Array.isArray(data?.data) ? data.data : [],
      total: Number(data?.total ?? 0),
    };
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function updateArticleRequestStatus(
  requestId: string | number,
  status: ArticleRequestStatus,
): Promise<{
  status: string;
  data?: ArticleRequest;
  message?: string;
}> {
  try {
    const { ok, data } = await requestWithToken(
      `${BASE_URL}/article-requests/${requestId}/status`,
      {
        method: "PUT",
        body: JSON.stringify({ status }),
      },
    );

    if (!ok) {
      return {
        status: "error",
        message: data.message || "Gagal memperbarui status request",
      };
    }

    return data;
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export type PublicationExtractionStatus = "complete" | "partial" | "empty";

export interface ManagedPublication {
  id: number;
  articleId?: number | null;
  articleUrl?: string | null;
  pdfUrl?: string | null;
  title?: string | null;
  authors?: string[];
  keywords?: string[];
  referenceList?: string[];
  referenceCount?: number;
  doi?: string | null;
    journal?: string | null;
    year?: number | null;
    category?: string | null;
    hasRawText?: boolean;
  extractionStatus?: PublicationExtractionStatus;
  createdAt?: string | null;
}

export interface PublicationMutationPayload {
  title: string;
  authors: string[];
  keywords: string[];
  doi?: string;
  journal?: string;
  year?: number | null;
  articleUrl?: string;
  pdfUrl?: string;
}

export type ActivityLogStatus = "success" | "failed";

export interface ActivityLog {
  id: number;
  userId?: string | number | null;
  userName?: string | null;
  action?: string | null;
  entityType?: string | null;
  entityId?: string | null;
  description?: string | null;
  oldData?: Record<string, unknown> | null;
  newData?: Record<string, unknown> | null;
  ipAddress?: string | null;
  status?: ActivityLogStatus | string | null;
  createdAt?: string | null;
}

export interface ActivityLogParams {
  page?: number;
  pageSize?: number;
  search?: string;
  action?: string;
  entityType?: string;
  status?: string;
  dateFrom?: string;
  dateTo?: string;
}

export async function getActivityLogs(
  filters: ActivityLogParams = {},
): Promise<{
  status: string;
  data?: ActivityLog[];
  total?: number;
  page?: number;
  pageSize?: number;
  totalPages?: number;
  message?: string;
}> {
  const params = new URLSearchParams();
  params.set("page", String(filters.page || 1));
  params.set("page_size", String(filters.pageSize || 10));

  if (filters.search) params.set("search", filters.search);
  if (filters.action && filters.action !== "all") {
    params.set("action", filters.action);
  }
  if (filters.entityType && filters.entityType !== "all") {
    params.set("entity_type", filters.entityType);
  }
  if (filters.status && filters.status !== "all") {
    params.set("status", filters.status);
  }
  if (filters.dateFrom) params.set("date_from", filters.dateFrom);
  if (filters.dateTo) params.set("date_to", filters.dateTo);

  try {
    const result = await requestWithToken(
      `${BASE_URL}/admin/activity-logs?${params.toString()}`,
    );
    if (!result.ok) {
      return {
        status: "error",
        message: result.data?.message || "Gagal mengambil log aktivitas",
      };
    }

    return {
      status: "success",
      data: Array.isArray(result.data?.data) ? result.data.data : [],
      total: Number(result.data?.total || 0),
      page: Number(result.data?.page || 1),
      pageSize: Number(result.data?.pageSize || 10),
      totalPages: Number(result.data?.totalPages || 1),
    };
  } catch {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function getManagedPublications(): Promise<{
  status: string;
  data?: ManagedPublication[];
  total?: number;
  message?: string;
}> {
  try {
    const result = await requestWithToken(`${BASE_URL}/admin/publications`);
    if (!result.ok) {
      return {
        status: "error",
        message: result.data?.message || "Gagal mengambil data publikasi",
      };
    }

    return {
      status: "success",
      data: Array.isArray(result.data?.data) ? result.data.data : [],
      total: Number(result.data?.total ?? 0),
    };
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export async function updateManagedPublication(
  publicationId: number,
  payload: PublicationMutationPayload,
): Promise<{
  status: string;
  data?: ManagedPublication;
  message?: string;
}> {
  try {
    const result = await requestWithToken(
      `${BASE_URL}/admin/publications/${publicationId}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
    );
    return result.ok
      ? result.data
      : {
          status: "error",
          message: result.data?.message || "Gagal memperbarui publikasi",
        };
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export async function deleteManagedPublication(
  publicationId: number,
): Promise<{
  status: string;
  data?: ManagedPublication;
  message?: string;
}> {
  try {
    const result = await requestWithToken(
      `${BASE_URL}/admin/publications/${publicationId}`,
      { method: "DELETE" },
    );
    return result.ok
      ? result.data
      : {
          status: "error",
          message: result.data?.message || "Gagal menghapus publikasi",
        };
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export async function updateProfile(payload: {
  name?: string;
  email?: string;
  avatarUrl?: string;
}) {
  const token = getToken();
  if (!token) {
    return {
      status: "error",
      message: "Token tidak ditemukan",
    };
  }

  try {
    const res = await fetch(`${BASE_URL}/auth/profile`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      return {
        status: "error",
        message: data.message || "Gagal memperbarui profile",
      };
    }

    if (data?.data) {
      localStorage.setItem("user", JSON.stringify(data.data));
      window.dispatchEvent(new Event("user-updated"));
    }

    return data;
  } catch (_error) {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export function updateUserLocal(payload: {
  name?: string;
  email?: string;
  avatarUrl?: string;
}) {
  const user = getUser();
  if (!user) {
    return null;
  }

  const nextUser = {
    ...user,
    ...payload,
  };

  localStorage.setItem("user", JSON.stringify(nextUser));
  window.dispatchEvent(new Event("user-updated"));
  return nextUser;
}


// Search
export interface SearchResult {
  status            : string;
  query?            : string;
  total?            : number;
  total_matched?    : number;
  displayed_count?  : number;
  total_occurrences?: number;  
  paper_count?      : number;  
  data?             : any[];
  message?          : string;
}

export async function searchArticles(
  query            : string,
  topK             : number  = 10,
  yearStart?       : number,
  yearEnd?         : number,
  jenisArtikel?    : string,
  kategori?        : string,
  jumlahKemunculan?: number | string, 
  jumlahPublikasi? : string,
  jenisAnalisis?   : string,
): Promise<SearchResult> {
  try {
    const params = new URLSearchParams({ query, top_k: topK.toString() });

    if (yearStart)        params.append("year_start",        yearStart.toString());
    if (yearEnd)          params.append("year_end",          yearEnd.toString());
    if (jenisArtikel)     params.append("jenis_artikel",     jenisArtikel);
    if (kategori)         params.append("kategori",          kategori);
    if (jenisAnalisis)    params.append("jenis_analisis",    jenisAnalisis);
    if (jumlahKemunculan !== undefined && jumlahKemunculan !== null && String(jumlahKemunculan).trim() !== "") {
      params.append("jumlah_kemunculan", String(jumlahKemunculan));
    }

    if (jumlahPublikasi)  params.append("jumlah_publikasi",  jumlahPublikasi);

    const res  = await fetch(`${BASE_URL}/search?${params}`);
    const data = await res.json();

    if (!res.ok) return { status: "error", message: data.message || "Pencarian gagal" };
    const list = Array.isArray(data?.data) ? data.data : [];
    const normalizedTotalMatched = Number(
      data?.total_matched ?? data?.total ?? data?.paper_count ?? list.length
    );

    return {
      ...data,
      total_matched: Number.isFinite(normalizedTotalMatched)
        ? normalizedTotalMatched
        : list.length,
    }; // sudah include total_occurrences & paper_count
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

// Stats
export async function getStats() {
  try {
    const res  = await fetch(`${BASE_URL}/stats`);
    const data = await res.json();
    if (!res.ok) return { status: "error", message: "Gagal mengambil statistik" };
    return data;
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export interface CategoryOption {
  value: string;
  label: string;
  count: number;
}

export interface AnalysisTypeOption {
  value: ArticleRelationType | string;
  label: string;
  count: number;
}

export async function getCategoryOptions(): Promise<{
  status: string;
  data?: CategoryOption[];
  message?: string;
}> {
  const candidates = [
    `${BASE_URL}/categories`,
    `${BASE_URL}/search/categories`,
    `${BASE_URL}/publications/categories`,
  ];

  try {
    let lastMessage = "Gagal mengambil kategori";
    for (const url of candidates) {
      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 404) {
          lastMessage = `Endpoint tidak ditemukan: ${url}`;
          continue;
        }
        return {
          status: "error",
          message: data?.message || `HTTP ${res.status} saat ambil kategori`,
        };
      }

      return {
        status: "success",
        data: Array.isArray(data?.data) ? data.data : [],
      };
    }

    return { status: "error", message: lastMessage };
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export interface CitationGraphNode {
  id: number;
  article_id?: number | null;
  title?: string | null;
  year?: number | null;
  doi?: string | null;
  authors?: string[] | string | null;
  reference_count?: number;
}

export async function getAnalysisTypeOptions(): Promise<{
  status: string;
  data?: AnalysisTypeOption[];
  message?: string;
}> {
  const candidates = [
    `${BASE_URL}/relation-types`,
    `${BASE_URL}/search/relation-types`,
    `${BASE_URL}/publications/relation-types`,
  ];

  try {
    let lastMessage = "Gagal mengambil jenis analisis";
    for (const url of candidates) {
      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok) {
        if (res.status === 404) {
          lastMessage = `Endpoint tidak ditemukan: ${url}`;
          continue;
        }
        return {
          status: "error",
          message: data?.message || `HTTP ${res.status} saat ambil jenis analisis`,
        };
      }

      return {
        status: "success",
        data: Array.isArray(data?.data) ? data.data : [],
      };
    }

    return { status: "error", message: lastMessage };
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

export type ArticleRelationType =
  | "bibliographic_coupling"
  | "keyword_cooccurrence"
  | "co_authorship";

export interface CitationGraphEdge {
  source: number;
  target: number;
  weight?: number;
  relation_type?: ArticleRelationType;
  details?: {
    shared_references?: string[];
    shared_keywords?: string[];
    shared_authors?: string[];
  };
}

export async function getCitationGraphData(
  articleIds?: number[],
  relationType: ArticleRelationType = "bibliographic_coupling",
) {
  const params = new URLSearchParams({
    relation_type: relationType,
  });
  if (articleIds?.length) {
    params.set("article_ids", articleIds.join(","));
  }
  const query = `?${params.toString()}`;
  const candidates = [
    `${BASE_URL}/graph-data${query}`,
    `${BASE_URL}/publications/graph-data${query}`,
  ];

  try {
    let lastMessage = "Gagal mengambil data graph";
    for (const url of candidates) {
      const res = await fetch(url);
      const raw = await res.text();
      let data: any = null;
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch (_e) {
        data = null;
      }

      if (!res.ok) {
        if (res.status === 404) {
          lastMessage = `Endpoint tidak ditemukan: ${url}`;
          continue;
        }
        return {
          status: "error",
          message: data?.message || `HTTP ${res.status} saat ambil graph data`,
        };
      }

      const result = data?.result || {};
      return {
        status: "success",
        data: {
          nodes: (result.nodes || []) as CitationGraphNode[],
          edges: (result.edges || []) as CitationGraphEdge[],
        },
      };
    }

    return {
      status: "error",
      message: lastMessage,
    };
  } catch (_error) {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}
