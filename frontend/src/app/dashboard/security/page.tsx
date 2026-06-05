"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/context/AuthContext";
import {
  getSettings, setup2FA, verify2FA, disable2FA, regenerateRecoveryCodes,
  get2FAReport, getSecurityRiskReport, getAccessAnomalyReport, resendOTP,
  TwoFAMethod, TwoFASettingsRead, TwoFASetupResponse, TwoFAStatusReport,
} from "@/lib/twoFactor";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { PageHelpTooltip } from "@/components/help/PageHelpTooltip";

type Step = "idle" | "qr" | "otp_input" | "done" | "disable";

export default function SecurityPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<TwoFASettingsRead | null>(null);
  const [step, setStep] = useState<Step>("idle");
  const [method, setMethod] = useState<TwoFAMethod>("totp");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [setupData, setSetupData] = useState<TwoFASetupResponse | null>(null);
  const [setupSessionToken, setSetupSessionToken] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<TwoFAStatusReport | null>(null);
  const [riskReport, setRiskReport] = useState<unknown>(null);
  const [anomalyReport, setAnomalyReport] = useState<unknown>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const cooldownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    loadSettings();
    return () => { if (cooldownRef.current) clearInterval(cooldownRef.current); };
  }, []);

  function startCooldown(seconds: number) {
    setResendCooldown(seconds);
    if (cooldownRef.current) clearInterval(cooldownRef.current);
    cooldownRef.current = setInterval(() => {
      setResendCooldown((s) => {
        if (s <= 1) { clearInterval(cooldownRef.current!); return 0; }
        return s - 1;
      });
    }, 1000);
  }

  async function loadSettings() {
    try {
      const s = await getSettings();
      setSettings(s);
    } catch {}
  }

  async function handleSetup() {
    setError("");
    setLoading(true);
    try {
      const phone = method === "sms" ? phoneNumber : undefined;
      const data = await setup2FA(method, phone);
      setSetupData(data);
      if (method === "totp") {
        setStep("qr");
      } else {
        setSetupSessionToken(data.session_token ?? null);
        setStep("otp_input");
        startCooldown(60);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Setup failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    setError("");
    setLoading(true);
    try {
      const res = await verify2FA(code, setupSessionToken ?? undefined);
      setRecoveryCodes(res.recovery_codes);
      setStep("done");
      await loadSettings();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Invalid code");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!setupSessionToken || resendCooldown > 0) return;
    setError("");
    setLoading(true);
    try {
      const res = await resendOTP(setupSessionToken);
      setSetupSessionToken(res.session_token);
      startCooldown(res.cooldown_seconds);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Failed to resend code");
    } finally {
      setLoading(false);
    }
  }

  async function handleDisable() {
    setError("");
    setLoading(true);
    try {
      await disable2FA(password);
      setStep("idle");
      setPassword("");
      await loadSettings();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Failed to disable 2FA");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegenerate() {
    setError("");
    setLoading(true);
    try {
      const res = await regenerateRecoveryCodes();
      setRecoveryCodes(res.codes);
      setStep("done");
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail || "Failed to regenerate");
    } finally {
      setLoading(false);
    }
  }

  async function loadReport() {
    try {
      const [r, risk, anomaly] = await Promise.all([
        get2FAReport(),
        getSecurityRiskReport(),
        getAccessAnomalyReport(),
      ]);
      setReport(r);
      setRiskReport(risk);
      setAnomalyReport(anomaly);
    } catch {}
  }

  const methodLabels: Record<TwoFAMethod, string> = {
    totp: "Authenticator App (TOTP)",
    sms: "SMS OTP",
    email: "Email OTP",
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">Security Settings</h1>
          <PageHelpTooltip topic="admin-security" />
        </div>
        <p className="text-sm text-gray-500 mt-1">Manage two-factor authentication for your account.</p>
      </div>

      {/* Current status */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Two-Factor Authentication</h2>
            <p className="text-sm text-gray-500">
              {settings?.is_enabled
                ? `Enabled · Method: ${methodLabels[settings.method!] || settings.method}`
                : "Not enabled"}
            </p>
          </div>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
            settings?.is_enabled
              ? "bg-green-100 text-green-800"
              : "bg-gray-100 text-gray-600"
          }`}>
            {settings?.is_enabled ? "Active" : "Disabled"}
          </span>
        </div>

        {!settings?.is_enabled && step === "idle" && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Choose method</label>
              <div className="grid grid-cols-3 gap-3">
                {(["totp", "sms", "email"] as TwoFAMethod[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMethod(m)}
                    className={`p-3 border rounded-xl text-sm font-medium transition-colors ${
                      method === m
                        ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                        : "border-gray-200 text-gray-700 hover:border-gray-300"
                    }`}
                  >
                    {methodLabels[m]}
                  </button>
                ))}
              </div>
            </div>

            {method === "sms" && (
              <Input
                id="phone-number"
                label="Phone Number"
                type="tel"
                placeholder="+254700000000"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
              />
            )}

            <Button onClick={handleSetup} loading={loading} disabled={method === "sms" && !phoneNumber.trim()}>
              Enable 2FA
            </Button>
          </div>
        )}

        {settings?.is_enabled && step === "idle" && (
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep("disable")}>
              Disable 2FA
            </Button>
            <Button variant="secondary" onClick={handleRegenerate} loading={loading}>
              Regenerate Recovery Codes
            </Button>
          </div>
        )}
      </div>

      {/* QR Code display (TOTP) */}
      {step === "qr" && setupData && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Scan QR Code</h2>
          {setupData.qr_code_image && (
            <div className="flex justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element -- 2FA QR data URI is generated by the backend for direct scanning. */}
              <img
                src={`data:image/png;base64,${setupData.qr_code_image}`}
                alt="2FA QR Code"
                className="w-48 h-48 border border-gray-200 rounded-lg"
              />
            </div>
          )}
          {setupData.secret_key && (
            <div className="bg-gray-50 rounded-lg p-3 text-center">
              <p className="text-xs text-gray-500 mb-1">Manual entry key</p>
              <code className="text-sm font-mono font-bold tracking-widest text-gray-900">
                {setupData.secret_key}
              </code>
            </div>
          )}
          <p className="text-sm text-gray-600">
            Open your authenticator app, scan the QR code, then enter the 6-digit code below.
          </p>
          <div className="space-y-3">
            <Input
              id="verify-code"
              label="Verification Code"
              type="text"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              autoFocus
            />
            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <Button onClick={handleVerify} loading={loading} className="w-full">
              Verify & Enable
            </Button>
          </div>
        </div>
      )}

      {/* OTP input (SMS/Email) */}
      {step === "otp_input" && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">
            {method === "email" ? "Check your email" : "Check your phone"}
          </h2>
          <p className="text-sm text-gray-600">
            {method === "email"
              ? `We sent a 6-digit code to ${user?.email}. Enter it below to enable Email OTP.`
              : `We sent a 6-digit code to ${phoneNumber}. Enter it below to enable SMS OTP.`}
          </p>
          <div className="space-y-3">
            <Input
              id="otp-code"
              label="Verification Code"
              type="text"
              inputMode="numeric"
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
              maxLength={6}
              autoFocus
            />
            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <Button onClick={handleVerify} loading={loading} className="w-full" disabled={code.length !== 6}>
              Verify & Enable
            </Button>
            <button
              type="button"
              onClick={handleResend}
              disabled={resendCooldown > 0 || loading}
              className="w-full text-sm text-indigo-600 hover:text-indigo-800 disabled:text-gray-400 disabled:cursor-not-allowed"
            >
              {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Resend code"}
            </button>
          </div>
        </div>
      )}

      {/* Recovery codes */}
      {step === "done" && recoveryCodes.length > 0 && (
        <div className="bg-white rounded-2xl border border-amber-300 p-6 space-y-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-8 h-8 bg-amber-100 rounded-full flex items-center justify-center">
              <span className="text-amber-600 font-bold text-sm">!</span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Save your recovery codes</h2>
              <p className="text-sm text-gray-500 mt-1">
                Store these codes securely. Each can only be used once. They will not be shown again.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {recoveryCodes.map((c, i) => (
              <code key={i} className="bg-gray-900 text-green-400 text-sm font-mono px-3 py-2 rounded-lg text-center">
                {c}
              </code>
            ))}
          </div>
          <Button onClick={() => { setStep("idle"); setRecoveryCodes([]); }} className="w-full">
            I have saved my codes
          </Button>
        </div>
      )}

      {/* Disable confirm */}
      {step === "disable" && (
        <div className="bg-white rounded-2xl border border-red-200 p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Disable 2FA</h2>
          <p className="text-sm text-gray-500">Enter your password to confirm disabling two-factor authentication.</p>
          <Input
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoFocus
          />
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <div className="flex gap-3">
            <Button variant="danger" onClick={handleDisable} loading={loading}>
              Disable 2FA
            </Button>
            <Button variant="secondary" onClick={() => { setStep("idle"); setError(""); }}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Admin reports */}
      {user?.is_superuser && (
        <div className="bg-white rounded-2xl border border-gray-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Security Reports</h2>
            <Button variant="secondary" onClick={loadReport} loading={loading}>
              Load Reports
            </Button>
          </div>

          {report && (
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-2xl font-bold text-gray-900">{report.users_with_2fa_enabled}</div>
                <div className="text-sm text-gray-500">Users with 2FA</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-2xl font-bold text-red-600">{report.users_without_2fa}</div>
                <div className="text-sm text-gray-500">Without 2FA</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-2xl font-bold text-amber-600">{report.failed_attempts_last_24h}</div>
                <div className="text-sm text-gray-500">Failed attempts (24h)</div>
              </div>
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="text-sm font-medium text-gray-700 mb-1">Methods</div>
                {Object.entries(report.method_breakdown).map(([k, v]) => (
                  <div key={k} className="text-sm text-gray-500">{k}: {v}</div>
                ))}
              </div>
            </div>
          )}

          {!!riskReport && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">AI Security Risk Monitor</h3>
              <pre className="bg-gray-900 text-green-300 text-xs rounded-lg p-3 overflow-auto max-h-40">
                {JSON.stringify(riskReport, null, 2)}
              </pre>
            </div>
          )}

          {!!anomalyReport && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">AI Access Anomaly Detector</h3>
              <pre className="bg-gray-900 text-blue-300 text-xs rounded-lg p-3 overflow-auto max-h-40">
                {JSON.stringify(anomalyReport, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
