const BASE_URL = "http://127.0.0.1:5000/api";

export async function login(email: string, password: string) {
  try {
    const res =  await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email, password,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      return {
        status: "error",
        message: data.message || "Login gagal",
      };
    }

    if (data.token) {
      localStorage.setItem("token", data.token);
      localStorage.setItem("user", JSON.stringify(data.data));
    }

    return data;
  } catch (error) {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function register(name: string, email: string, password: string) {
  try {
    const res = await fetch(`${BASE_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({name, email, password}),
    });

    const data = await res.json();

    if (!res.ok) {
      return {
        status: "error",
        message: data.message || "Register gagal",
      };
    }

    return data;
  } catch (error) {
    return {
      status: "error",
      message: "Gagal koneksi ke server",
    };
  }  
}

export function logout() {
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

export async function searchArticles(
  query: string,
  topK: number = 10,
  yearStart?: number,
  yearEnd?: number
) {
  try {
    const params = new URLSearchParams({ query, top_k: topK.toString() });
    if (yearStart) params.append("year_start", yearStart.toString());
    if (yearEnd)   params.append("year_end",   yearEnd.toString());

    const res  = await fetch(`${BASE_URL}/search?${params}`);
    const data = await res.json();

    if (!res.ok) {
      return {
        status : "error",
        message: data.message || "Pencarian gagal",
      };
    }
    return data;
  } catch (error) {
    return {
      status : "error",
      message: "Gagal koneksi ke server",
    };
  }
}

export async function getStats() {
  try {
    const res  = await fetch(`${BASE_URL}/stats`);
    const data = await res.json();

    if (!res.ok) {
      return {
        status : "error",
        message: "Gagal mengambil statistik",
      };
    }
    return data;
  } catch (error) {
    return {
      status : "error",
      message: "Gagal koneksi ke server",
    };
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

export interface CitationGraphEdge {
  source: number;
  target: number;
  weight?: number;
}

export async function getCitationGraphData() {
  const candidates = [
    `${BASE_URL}/graph-data`,
    `${BASE_URL}/publications/graph-data`,
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
        // Coba candidate berikutnya jika 404.
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
