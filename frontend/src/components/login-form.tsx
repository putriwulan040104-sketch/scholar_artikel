"use client";

import { Link, useNavigate } from "react-router-dom";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
  // FieldSeparator,
} from "./ui/field";
import { Input } from "./ui/input";
import { useState } from "react";
import { login } from "@/api/api";
import { PasswordInput } from "@/components/password-input";
import { z } from "zod";

const loginSchema = z.object({
  password: z
    .string()
    .min(1, "Password wajib diisi")
    .min(8, "Password minimal 8 karakter")
    .regex(/[A-Za-z]/, "Password harus berisi huruf")
    .regex(/[0-9]/, "Password harus berisi angka"),
});

type LoginFormErrors = Partial<
  Record<keyof z.infer<typeof loginSchema>, string>
>;

function getLoginErrors(error: z.ZodError<z.infer<typeof loginSchema>>) {
  return error.issues.reduce<LoginFormErrors>((errors, issue) => {
    const field = issue.path[0] as keyof LoginFormErrors | undefined;
    if (field && !errors[field]) {
      errors[field] = issue.message;
    }

    return errors;
  }, {});
}

export function LoginForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<LoginFormErrors>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const parsed = loginSchema.safeParse({ password });
    if (!parsed.success) {
      setFieldErrors(getLoginErrors(parsed.error));
      return;
    }

    setFieldErrors({});
    setLoading(true);

    const res = await login(email, parsed.data.password);
    setLoading(false);

    if (res.status === "error") {
      setError(res.message);
      return;
    }

    navigate("/search");
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Selamat Datang</CardTitle>
          <CardDescription>Masukkan akun anda</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError("");
                  }}
                  required
                />
              </Field>
              <Field data-invalid={!!fieldErrors.password}>
                <FieldLabel htmlFor="password">Password</FieldLabel>
                <PasswordInput
                  id="password"
                  placeholder="password"
                  value={password}
                  aria-invalid={!!fieldErrors.password}
                  aria-describedby={
                    fieldErrors.password ? "login-password-error" : undefined
                  }
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError("");
                    setFieldErrors((current) => ({
                      ...current,
                      password: undefined,
                    }));
                  }}
                />
                <FieldError id="login-password-error">
                  {fieldErrors.password}
                </FieldError>
                <div className="flex items-center">
                  <a
                    href="#"
                    className="ml-auto text-sm underline-offset-4 hover:underline"
                  >
                    Lupa password?
                  </a>
                </div>
              </Field>
              {error && (
                <p className="text-sm text-red-500 text-center -mt-2">
                  {error}
                </p>
              )}
              <Field>
                <Button type="submit" disabled={loading}>
                  {loading ? "Loading..." : "Login"}
                </Button>
              </Field>
              {/* <FieldSeparator className="*:data-[slot=field-separator-content]:bg-card">
                atau
              </FieldSeparator> */}
              {/* <Field>
                <Button variant="outline" type="button">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path
                      d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .307 5.387.307 12s5.56 12 12.173 12c3.573 0 6.267-1.173 8.373-3.36 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.053H12.48z"
                      fill="currentColor"
                    />
                  </svg>
                  Masuk dengan Google
                </Button>
              </Field> */}
              <FieldDescription className="text-center">
                Tidak punya akun? <Link to="/register">Daftar</Link>
              </FieldDescription>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
