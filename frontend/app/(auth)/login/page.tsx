"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { BrandHeading, BrandIcon } from "@/components/brand";
import { Eye, EyeOff } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  );
}

function LoginContent() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const authError = searchParams.get("error");
  const blockedEmail = searchParams.get("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const googleUrl = `${API_URL}/api/auth/google/login/?process=login`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (e: unknown) {
      const err = e as { message?: string };
      const msg = err?.message || "";
      if (msg.includes("Invalid credentials") || msg.includes("invalid")) {
        setError("Email or password doesn\u2019t match. Please check and try again.");
      } else {
        setError("Something went wrong. Please try again in a moment.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-bg-primary px-4 py-8">
      <div className="mb-8 text-center flex flex-col items-center">
        <BrandIcon size={40} className="mb-4" />
        <BrandHeading className="text-3xl sm:text-4xl" />
        <p className="text-text-secondary mt-2 text-sm">Sign in to your account</p>
      </div>

      {authError === "allowlist" && (
        <div className="w-full max-w-md mb-4 rounded-lg border border-accent-gold/30 bg-accent-gold/5 p-4 text-center">
          <p className="text-sm text-text-primary mb-1">
            <span className="font-medium">{blockedEmail}</span> — you must be invited in order to sign up.
          </p>
          <p className="text-xs text-text-secondary">
            You must be invited in order to sign up.
          </p>
        </div>
      )}

      <Card className="w-full max-w-md bg-bg-surface border-border">
        <CardHeader>
          <h2 className="text-xl font-semibold text-text-heading text-center">Welcome back</h2>
        </CardHeader>
        <CardContent>
          <a
            href={googleUrl}
            className="w-full flex items-center justify-center gap-2 bg-bg-input border border-border text-text-primary hover:bg-bg-surface-hover font-medium mb-4 rounded-lg py-2.5 px-4 cursor-pointer transition-colors"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </a>

          <div className="flex items-center gap-3 my-4">
            <Separator className="flex-1 bg-border" />
            <span className="text-text-secondary text-xs">or</span>
            <Separator className="flex-1 bg-border" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-text-primary">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="bg-bg-input border-border text-text-primary" />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-text-primary">Password</Label>
              <div className="relative">
                <Input id="password" type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} required className="bg-bg-input border-border text-text-primary pr-10" />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text-primary transition-colors" tabIndex={-1}>
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && <p className="text-flag-critical text-sm">{error}</p>}

            <Button type="submit" disabled={loading} className="w-full bg-accent-gold text-bg-primary hover:bg-accent-gold-hover font-medium">
              {loading ? "Loading..." : "Log In"}
            </Button>
          </form>

          <p className="text-center text-text-secondary text-sm mt-6">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-accent-violet hover:text-accent-violet-light">Sign Up</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
