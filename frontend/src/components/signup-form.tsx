import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { register } from "@/api/api";
import { useState } from "react";
import { PasswordInput } from "@/components/password-input";
import { z } from "zod";

const passwordMismatchMessage = "Konfirmasi password tidak sama";

const signupSchema = z
  .object({
    password: z
      .string()
      .min(1, "Password wajib diisi")
      .min(8, "Password minimal 8 karakter")
      .regex(/[A-Za-z]/, "Password harus berisi huruf")
      .regex(/[0-9]/, "Password harus berisi angka"),
    confirmPassword: z.string().min(1, "Konfirmasi password wajib diisi"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: passwordMismatchMessage,
    path: ["confirmPassword"],
  });

type SignupFormValues = z.infer<typeof signupSchema>;
type SignupFormErrors = Partial<Record<keyof SignupFormValues, string>>;

function getSignupErrors(error: z.ZodError<SignupFormValues>) {
  return error.issues.reduce<SignupFormErrors>((errors, issue) => {
    const field = issue.path[0] as keyof SignupFormErrors | undefined;
    if (field && !errors[field]) {
      errors[field] = issue.message;
    }

    return errors;
  }, {});
}

export function SignupForm({
  className,
  ...props
}: React.ComponentProps<"div">) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<SignupFormErrors>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    const parsed = signupSchema.safeParse({
      password,
      confirmPassword,
    });

    if (!parsed.success) {
      setFieldErrors(getSignupErrors(parsed.error));
      return;
    }

    setFieldErrors({});
    setLoading(true);

    const res = await register(name, email, parsed.data.password);
    setLoading(false);

    if (res.status === "error") {
      setError(res.message);
      return;
    }

    navigate("/login");
  };

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Buat Akun Baru</CardTitle>
          <CardDescription>
            Masukkan email Anda untuk membuat akun
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="name">Nama Lengkap</FieldLabel>
                <Input
                  id="name"
                  type="text"
                  placeholder="Nama lengkap"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setError("");
                  }}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="email">Email</FieldLabel>
                <Input
                  id="email"
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError("");
                  }}
                  required
                />
              </Field>
              <Field>
                <Field className="grid grid-cols-2 gap-4">
                  <Field data-invalid={!!fieldErrors.password}>
                    <FieldLabel htmlFor="password">Password</FieldLabel>
                    <PasswordInput
                      id="password"
                      value={password}
                      aria-invalid={!!fieldErrors.password}
                      aria-describedby={
                        fieldErrors.password
                          ? "signup-password-error"
                          : undefined
                      }
                      onChange={(e) => {
                        const nextPassword = e.target.value;

                        setPassword(nextPassword);
                        setError("");
                        setFieldErrors((current) => ({
                          ...current,
                          password: undefined,
                          confirmPassword:
                            confirmPassword && nextPassword !== confirmPassword
                              ? passwordMismatchMessage
                              : current.confirmPassword ===
                                  passwordMismatchMessage
                                ? undefined
                                : current.confirmPassword,
                        }));
                      }}
                    />
                    <FieldError id="signup-password-error">
                      {fieldErrors.password}
                    </FieldError>
                  </Field>
                  <Field data-invalid={!!fieldErrors.confirmPassword}>
                    <FieldLabel htmlFor="confirm-password">
                      Konfirmasi Password
                    </FieldLabel>
                    <PasswordInput
                      id="confirm-password"
                      value={confirmPassword}
                      aria-invalid={!!fieldErrors.confirmPassword}
                      aria-describedby={
                        fieldErrors.confirmPassword
                          ? "signup-confirm-password-error"
                          : undefined
                      }
                      onChange={(e) => {
                        const nextConfirmPassword = e.target.value;

                        setConfirmPassword(nextConfirmPassword);
                        setError("");
                        setFieldErrors((current) => ({
                          ...current,
                          confirmPassword:
                            nextConfirmPassword &&
                            password !== nextConfirmPassword
                              ? passwordMismatchMessage
                              : undefined,
                        }));
                      }}
                    />
                    <FieldError id="signup-confirm-password-error">
                      {fieldErrors.confirmPassword}
                    </FieldError>
                  </Field>
                </Field>
              </Field>
              {error && (
                <p className="text-sm text-red-500 text-center -mt-2">
                  {error}
                </p>
              )}
              <Field>
                <Button type="submit" disabled={loading}>
                  {loading ? "Loading..." : "Daftar"}
                </Button>
                <FieldDescription className="text-center">
                  Sudah punya akun? <Link to="/login">Masuk</Link>
                </FieldDescription>
              </Field>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
