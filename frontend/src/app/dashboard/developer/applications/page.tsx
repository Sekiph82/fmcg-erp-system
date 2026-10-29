"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  ApiClientApplication,
  ApiClientEnvironment,
  devPortalApi,
} from "@/lib/api_portal_api";

const ENVIRONMENTS: ApiClientEnvironment[] = ["development", "sandbox", "production"];

export default function ApiApplicationsPage() {
  const [applications, setApplications] = useState<ApiClientApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [environment, setEnvironment] = useState<ApiClientEnvironment>("development");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setApplications(await devPortalApi.listApplications(true));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "API applications could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await devPortalApi.createApplication({
        name: name.trim(),
        description: description.trim() || undefined,
        environment,
      });
      setName("");
      setDescription("");
      setEnvironment("development");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "API application could not be registered.");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (application: ApiClientApplication) => {
    setUpdatingId(application.client_id);
    setError(null);
    try {
      await devPortalApi.updateApplication(application.client_id, { is_active: !application.is_active });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "API application could not be updated.");
    } finally {
      setUpdatingId(null);
    }
  };

  const formatDate = (value: string) => new Date(value).toLocaleString();

  return (
    <main className="w-full min-w-0 space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/dashboard/developer" className="text-sm text-blue-700 hover:underline">Developer Portal</Link>
          <h1 className="mt-2 text-2xl font-bold text-gray-900">API Applications</h1>
          <p className="mt-1 text-sm text-gray-600">Register application metadata before managing its credentials.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading} className="rounded border px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50">
          Refresh
        </button>
      </div>

      <p className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
        This registry stores application details only. It does not create credentials or connect to an external partner.
      </p>

      {error && <div role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}

      <form onSubmit={create} className="space-y-4 rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold">Register an application</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-1 text-sm font-medium text-gray-700">
            Application name
            <input required maxLength={160} value={name} onChange={(event) => setName(event.target.value)} className="w-full rounded border px-3 py-2 font-normal" />
          </label>
          <label className="space-y-1 text-sm font-medium text-gray-700">
            Environment
            <select value={environment} onChange={(event) => setEnvironment(event.target.value as ApiClientEnvironment)} className="w-full rounded border px-3 py-2 font-normal">
              {ENVIRONMENTS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
        <label className="block space-y-1 text-sm font-medium text-gray-700">
          Description <span className="font-normal text-gray-500">(optional)</span>
          <textarea maxLength={2000} rows={3} value={description} onChange={(event) => setDescription(event.target.value)} className="w-full rounded border px-3 py-2 font-normal" />
        </label>
        <button type="submit" disabled={saving || !name.trim()} className="rounded bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50">
          {saving ? "Registering…" : "Register application"}
        </button>
      </form>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Registered applications</h2>
        {loading ? <p className="text-sm text-gray-500">Loading applications…</p> : applications.length === 0 ? (
          <p className="rounded border bg-white p-5 text-sm text-gray-600">No applications are registered yet.</p>
        ) : (
          <div className="space-y-3">
            {applications.map((application) => (
              <article key={application.client_id} className="flex flex-wrap items-start justify-between gap-4 rounded-lg border bg-white p-4 shadow-sm">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{application.name}</h3>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-700">{application.environment}</span>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${application.is_active ? "bg-green-100 text-green-800" : "bg-gray-200 text-gray-600"}`}>
                      {application.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                  {application.description && <p className="text-sm text-gray-600">{application.description}</p>}
                  <p className="text-xs text-gray-500">Registered {formatDate(application.created_at)}</p>
                </div>
                <button type="button" onClick={() => void toggleActive(application)} disabled={updatingId === application.client_id} className="rounded border px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50">
                  {updatingId === application.client_id ? "Saving…" : application.is_active ? "Deactivate" : "Reactivate"}
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
