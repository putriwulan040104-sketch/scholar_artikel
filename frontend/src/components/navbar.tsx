import { useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Camera, ChevronDown, User } from "lucide-react";
import { getUser, logout, updateProfile, updateUserLocal } from "@/api/api";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SidebarTrigger } from "@/components/ui/sidebar";

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useMemo(() => getUser(), []);

  const [profileOpen, setProfileOpen] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [avatarUrl, setAvatarUrl] = useState(user?.avatarUrl || "");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const avatarInputRef = useRef<HTMLInputElement | null>(null);

  const userInitial = (name || "U").charAt(0).toUpperCase();

  const pageTitle = useMemo(() => {
    const pathname = location.pathname;

    if (pathname.startsWith("/dashboard")) return "Dashboard";
    if (pathname.startsWith("/search")) return "Eksplorasi";
    if (pathname.startsWith("/citation-graph")) return "Jaringan Relasi Artikel";
    if (pathname.startsWith("/favorite")) return "Artikel Tersimpan";
    if (pathname.startsWith("/super-admin/dashboard")) return "Dashboard";
    if (pathname.startsWith("/super-admin/publications")) return "Kelola Publikasi";
    if (pathname.startsWith("/super-admin/users")) return "Kelola Pengguna";
    if (pathname.startsWith("/super-admin/requests")) return "Kelola Request";
    if (pathname.startsWith("/super-admin/activity-logs")) return "Log Aktivitas";
    if (pathname.startsWith("/detail")) return "Detail Publikasi";

    return "Dashboard";
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleOpenProfile = () => {
    const freshUser = getUser();
    setName(freshUser?.name || "");
    setEmail(freshUser?.email || "");
    setAvatarUrl(freshUser?.avatarUrl || "");
    setSaving(false);
    setMessage("");
    setProfileOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage("");

    const result = await updateProfile({ name, email, avatarUrl });
    if (result.status === "error") {
      setSaving(false);
      setMessage(result.message || "Gagal memperbarui profile.");
      return;
    }

    updateUserLocal({
      name: result?.data?.name ?? name,
      email: result?.data?.email ?? email,
      avatarUrl: result?.data?.avatarUrl ?? avatarUrl,
    });

    setSaving(false);
    setMessage("Profile berhasil diperbarui.");
    setTimeout(() => {
      setProfileOpen(false);
      setMessage("");
    }, 800);
  };

  const handleAvatarFile = (file: File | null) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      setAvatarUrl(result);
    };
    reader.readAsDataURL(file);
  };

  return (
    <>
      <header className="sticky top-0 z-40 flex h-18 shrink-0 items-center border-b border-white/10 bg-primary px-4 shadow-sm">
        <div className="flex items-center gap-2 px-4">
          <SidebarTrigger className="-ml-1 rounded-md p-1 transition hover:bg-white/20 [&_svg]:h-5 [&_svg]:w-5 [&_svg]:text-white " />
          <h1 className="text-white font-medium">{pageTitle}</h1>
        </div>
        <div className="ml-auto">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex items-center gap-2 rounded-full hover:bg-white/10 p-1 transition">
                <Avatar className="h-8 w-8">
                  {avatarUrl ? <AvatarImage src={avatarUrl} alt={name || "User"} /> : null}
                  <AvatarFallback>{userInitial ? userInitial : <User />}</AvatarFallback>
                </Avatar>
                <ChevronDown className="h-4 w-4 text-white/80" />
              </button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem
                onSelect={(e) => {
                  e.preventDefault();
                  handleOpenProfile();
                }}
              >
                Profile
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-500">
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="max-w-lg rounded-xl p-0 overflow-hidden">
          <div className="border-b px-6 py-4 text-center">
            <h2 className="text-lg font-semibold">Profile</h2>
            <p className="text-sm text-muted-foreground">Kelola informasi akun Anda</p>
          </div>

          <div className="space-y-4 px-6 py-5">
            <div className="flex flex-col items-center gap-3 text-center">
              <div className="relative">
                <Avatar className="h-24 w-24">
                  {avatarUrl ? <AvatarImage src={avatarUrl} alt={name || "User"} /> : null}
                  <AvatarFallback className="text-2xl font-semibold">{userInitial}</AvatarFallback>
                </Avatar>
                <button
                  type="button"
                  aria-label="Ubah foto profile"
                  className="absolute -bottom-1 -right-1 rounded-full border bg-white p-1.5 text-muted-foreground shadow-sm transition hover:text-foreground"
                  onClick={() => avatarInputRef.current?.click()}
                >
                  <Camera className="h-4 w-4" />
                </button>
                <Input
                  ref={avatarInputRef}
                  id="profile-avatar"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleAvatarFile(e.target.files?.[0] || null)}
                />
              </div>
              <div>
              </div>
            </div>

            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="profile-name">Nama</Label>
                <Input
                  id="profile-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nama lengkap"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="profile-email">Email</Label>
                <Input
                  id="profile-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email"
                />
              </div>
            </div>

            {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}

            <div className="flex items-center justify-end gap-2 border-t pt-4">
              <Button variant="outline" onClick={() => setProfileOpen(false)}>
                Batal
              </Button>
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Menyimpan..." : "Simpan"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
