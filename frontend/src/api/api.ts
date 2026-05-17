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