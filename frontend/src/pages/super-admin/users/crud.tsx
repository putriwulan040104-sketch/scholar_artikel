import { useEffect, useState } from "react";
import type { ManagedUser } from "@/api/api";
import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/password-input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type UserCrudMode = "create" | "edit" | "delete";

export interface UserCrudPayload {
  name: string;
  email: string;
  role: string;
  password?: string;
}

interface UserCrudDialogProps {
  open: boolean;
  mode: UserCrudMode;
  user?: ManagedUser | null;
  loading?: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: UserCrudPayload) => void;
}

const titleByMode: Record<UserCrudMode, string> = {
  create: "Tambah Pengguna",
  edit: "Edit Pengguna",
  delete: "Hapus Pengguna",
};

export function UserCrudDialog({
  open,
  mode,
  user,
  loading = false,
  onOpenChange,
  onSubmit,
}: UserCrudDialogProps) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("user");
  const [password, setPassword] = useState("");

  useEffect(() => {
    setName(user?.name || "");
    setEmail(user?.email || "");
    setRole(user?.role || "user");
    setPassword("");
  }, [user, open]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    onSubmit({
      name,
      email,
      role,
      password: password || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg rounded-xl">
        <DialogHeader>
          <DialogTitle>{titleByMode[mode]}</DialogTitle>
        </DialogHeader>

        {mode === "delete" ? (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Yakin ingin menghapus user{" "}
              <span className="font-medium text-foreground">
                {user?.email || user?.name || "-"}
              </span>
              ?
            </p>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Batal
              </Button>
              <Button
                type="button"
                variant="destructive"
                disabled={loading}
                onClick={() =>
                  onSubmit({
                    name: user?.name || "",
                    email: user?.email || "",
                    role: user?.role || "user",
                  })
                }
              >
                {loading ? "Menghapus..." : "Hapus"}
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="user-name">Nama</Label>
              <Input
                id="user-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Nama user"
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="user-email">Email</Label>
              <Input
                id="user-email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="Email"
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="user-role">Role</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger id="user-role">
                  <SelectValue placeholder="Pilih role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="super_admin">Super Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="user-password">
                Password {mode === "edit" ? "(opsional)" : ""}
              </Label>
              <PasswordInput
                id="user-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Password user"
                required={mode === "create"}
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Batal
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? "Menyimpan..." : "Simpan"}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
