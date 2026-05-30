const BASE_URL = "http://127.0.0.1:5000/api";

// ── Auth ──────────────────────────────────────────────────

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
  localStorage.removeItem("token");
  localStorage.removeItem("user");
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


// ── Search ────────────────────────────────────────────────

export interface SearchResult {
  status            : string;
  query?            : string;
  total?            : number;
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
  jenisAnalisis?   : string,
  jumlahKemunculan?: number | string, 
  jumlahPublikasi? : string,
  sumberData?      : string,
): Promise<SearchResult> {
  try {
    const params = new URLSearchParams({ query, top_k: topK.toString() });

    if (yearStart)        params.append("year_start",        yearStart.toString());
    if (yearEnd)          params.append("year_end",          yearEnd.toString());
    if (jenisArtikel)     params.append("jenis_artikel",     jenisArtikel);
    if (jenisAnalisis)    params.append("jenis_analisis",    jenisAnalisis);
    if (jumlahKemunculan !== undefined && jumlahKemunculan !== null && String(jumlahKemunculan).trim() !== "") {
      params.append("jumlah_kemunculan", String(jumlahKemunculan));
    }

    if (jumlahPublikasi)  params.append("jumlah_publikasi",  jumlahPublikasi);
    if (sumberData)       params.append("sumber_data",       sumberData);

    const res  = await fetch(`${BASE_URL}/search?${params}`);
    const data = await res.json();

    if (!res.ok) return { status: "error", message: data.message || "Pencarian gagal" };

    return data; // sudah include total_occurrences & paper_count
  } catch {
    return { status: "error", message: "Gagal koneksi ke server" };
  }
}

// ── Stats ─────────────────────────────────────────────────

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