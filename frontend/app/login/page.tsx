"use client";

import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("admin@mock-hrms.dev");
  const [password, setPassword] = useState("password123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await login(email, password);
      if (!result.success) {
        setError(result.error?.message || "Login failed");
        return;
      }

      localStorage.setItem("hrms_access_token", result.data.access_token);
      try {
        const payload = JSON.parse(atob(result.data.access_token.split(".")[1]));
        if (typeof payload.role === "string") {
          document.cookie = `hrms_role=${payload.role}; path=/; max-age=86400; samesite=lax`;
        }
      } catch {
        // Ignore token parsing errors; backend auth remains source of truth.
      }
      document.cookie = "hrms_auth=1; path=/; max-age=86400; samesite=lax";
      router.push("/dashboard");
    } catch {
      setError("Unable to reach API. Confirm backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#040b22] px-4">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(95,92,255,0.35),transparent_40%),radial-gradient(circle_at_80%_5%,rgba(59,130,246,0.22),transparent_35%),linear-gradient(180deg,#0a1230_0%,#050a1f_55%,#040818_100%)]" />
      <Card className="relative w-full max-w-md border border-indigo-300/20 bg-slate-950/70 text-slate-100 shadow-2xl backdrop-blur">
        <CardHeader className="space-y-3">
          <div className="mx-auto h-20 w-56 overflow-hidden">
            <Image
              src="/logo.png"
              alt="HRMS Logo"
              width={320}
              height={120}
              className="h-full w-full object-cover object-center"
              priority
            />
          </div>
          <CardTitle className="text-2xl font-bold text-white">Welcome</CardTitle>
          <CardDescription className="text-slate-300">
            Login with seeded credentials to access the workspace.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label className="text-slate-200" htmlFor="email">Email</Label>
              <Input
                className="border-indigo-300/20 bg-white/10 text-white placeholder:text-slate-300"
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label className="text-slate-200" htmlFor="password">Password</Label>
              <Input
                className="border-indigo-300/20 bg-white/10 text-white placeholder:text-slate-300"
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error ? <p className="text-sm text-rose-300">{error}</p> : null}
            <Button className="w-full bg-indigo-500 text-white hover:bg-indigo-400" disabled={loading} type="submit">
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
