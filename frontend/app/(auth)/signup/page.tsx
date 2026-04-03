"use client";

import { useState, Suspense } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { BrandHeading } from "@/components/brand";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SignupPage() {
  return (
    <Suspense>
      <SignupContent />
    </Suspense>
  );
}

function SignupContent() {
  const { signup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);

  const googleUrl = `${API_URL}/api/auth/google/login/?process=login`;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signup(email, password, termsAccepted);
      router.push("/dashboard");
    } catch (e: unknown) {
      const err = e as { message?: string };
      const msg = err?.message || "";
      if (msg.includes("allow list") || msg.includes("allowlist")) {
        setError("You must be invited in order to sign up.");
      } else if (msg.includes("already registered")) {
        setError("This email is already registered.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-bg-primary px-4">
      <div className="mb-8 text-center">
        <BrandHeading className="text-4xl" />
      </div>

      <Card className="w-full max-w-md bg-bg-surface border-border">
        <CardHeader>
          <h2 className="text-xl font-semibold text-text-heading text-center">Create your account</h2>
        </CardHeader>
        <CardContent>
          <button
            onClick={() => { if (termsAccepted) window.location.href = googleUrl; }}
            disabled={!termsAccepted}
            className="w-full flex items-center justify-center gap-2 bg-bg-input border border-border text-text-primary hover:bg-bg-surface-hover font-medium mb-4 rounded-lg py-2.5 px-4 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
            Continue with Google
          </button>
          {!termsAccepted && (
            <p className="text-text-secondary/50 text-[10px] text-center -mt-2 mb-2">
              Accept the terms below to continue
            </p>
          )}

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
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} className="bg-bg-input border-border text-text-primary" />
            </div>

            <Separator className="bg-border" />

            <label className="flex items-start gap-2 cursor-pointer">
              <input type="checkbox" checked={termsAccepted} onChange={(e) => setTermsAccepted(e.target.checked)} className="mt-0.5 rounded border-border accent-accent-gold" />
              <span className="text-xs text-text-secondary leading-relaxed">
                I agree to the <Link href="/terms" className="text-accent-gold hover:text-accent-gold-hover underline">Terms of Service</Link> and <Link href="/privacy" className="text-accent-gold hover:text-accent-gold-hover underline">Privacy Policy</Link>
              </span>
            </label>

            {error && <p className="text-flag-critical text-sm">{error}</p>}

            <Button type="submit" disabled={loading || !termsAccepted} className="w-full bg-accent-gold text-bg-primary hover:bg-accent-gold-hover font-medium">
              {loading ? "Loading..." : "Sign Up"}
            </Button>
          </form>

          <p className="text-center text-text-secondary text-sm mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-accent-gold hover:text-accent-gold-hover">Log In</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
