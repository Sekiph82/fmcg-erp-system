"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { API_ORIGIN, apiClient } from "@/lib/api";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useI18n } from "@/lib/i18n";

// Kept as a key/status (not text) so the message follows a language switch. A 403 detail is the server's own reason (e.g. account locked).
type LoginError = { key: string; vars?: Record<string, string> } | { status: number } | { text: string };

export default function LoginPage() {
  const { login } = useAuth();
  const { t, err } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<LoginError | null>(null);
  const [loading, setLoading] = useState(false);
  const [sso, setSso] = useState<{ oidc: string; name: string | null; enforced: boolean } | null>(null);
  useEffect(() => {   // M45.S01.T016 staff single sign-on
    apiClient.get("/api/v1/sso/status").then((r) => setSso(r.data)).catch(() => setSso(null));
    const e = new URLSearchParams(window.location.search).get("sso_error");
    if (e) setError({ key: "staff.login.ssoFailed", vars: { reason: e } });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (ex) {
      if (axios.isAxiosError(ex) && ex.response && ex.response.status >= 500) {
        setError({ status: ex.response.status });
      } else if (axios.isAxiosError(ex) && ex.response?.status === 403 && typeof ex.response.data?.detail === "string") {
        setError({ text: ex.response.data.detail });
      } else {
        setError({ key: "staff.login.invalid" });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4 relative">
      <LanguageSwitcher className="absolute top-4 right-4" />
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          {/* POVU logo replacing the purple ERP square */}
          <div className="flex justify-center mb-3">
            <Image
              src="/brand/povu-logo.png"
              alt="POVU"
              width={192}
              height={128}
              priority
            />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">POVU ERP</h1>
          <p className="text-sm text-gray-500 mt-1">{t("staff.login.subtitle")}</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-5" data-testid="login-form">
            <Input
              id="username"
              label={t("staff.login.username")}
              type="text"
              placeholder={t("staff.login.usernamePlaceholder")}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              data-testid="login-username"
            />
            <Input
              id="password"
              label={t("common.password")}
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
                {"text" in error ? error.text : "status" in error ? err(error.status) : t(error.key, error.vars)}
              </div>
            )}

            <Button type="submit" loading={loading} className="w-full" data-testid="login-submit">
              {t("common.signIn")}
            </Button>
          </form>
          {sso?.oidc === "ACTIVE" && <a href={`${API_ORIGIN}/api/v1/sso/start`} className="mt-3 block w-full text-center border rounded-md py-2 text-sm font-medium" data-testid="login-sso">
            {t(sso.enforced ? "staff.login.ssoWithRequired" : "staff.login.ssoWith", { name: sso.name ?? t("staff.login.ssoDefault") })}</a>}
        </div>
      </div>
    </div>
  );
}
