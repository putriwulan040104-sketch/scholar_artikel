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
