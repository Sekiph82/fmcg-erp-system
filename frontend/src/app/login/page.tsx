"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { API_ORIGIN, apiClient } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sso, setSso] = useState<{ oidc: string; name: string | null; enforced: boolean } | null>(null);
  useEffect(() => {   // M45.S01.T016 staff single sign-on
    apiClient.get("/api/v1/sso/status").then((r) => setSso(r.data)).catch(() => setSso(null));
    const e = new URLSearchParams(window.location.search).get("sso_error");
    if (e) setError(`Single sign-on failed: ${e}`);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response && err.response.status >= 500) {
        setError("Server error — please try again in a moment.");
      } else if (axios.isAxiosError(err) && err.response?.status === 403 && typeof err.response.data?.detail === "string") {
        setError(err.response.data.detail);
      } else {
        setError("Invalid username or password.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          {/* POVU logo replacing the purple ERP square */}
          <div className="flex justify-center mb-3">
            <Image
              src="/povu-logo.jpg"
              alt="POVU"
              width={128}
              height={128}
              priority
            />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">POVU ERP</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to your account</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
            <Input
              id="username"
              label="Username"
              type="text"
              placeholder="your_username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              data-testid="login-username"
            />
            <Input
              id="password"
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              data-testid="login-password"
            />

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700" data-testid="login-error">
                {error}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full" data-testid="login-submit">
              Sign in
            </Button>
          </form>
          {sso?.oidc === "ACTIVE" && <a href={`${API_ORIGIN}/api/v1/sso/start`} className="mt-3 block w-full text-center border rounded-md py-2 text-sm font-medium" data-testid="login-sso">
            Sign in with {sso.name ?? "single sign-on"}{sso.enforced ? " (required)" : ""}</a>}
        </div>
      </div>
    </div>
  );
}
