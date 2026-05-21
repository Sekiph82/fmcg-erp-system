"use client";

import { useEffect, useState } from "react";
import { listEventDefinitions, EventDefinition } from "@/lib/webhooks";

export default function EventDefinitionsPage() {
  const [defs, setDefs] = useState<EventDefinition[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);
  async function load() {
    try { setDefs(await listEventDefinitions()); } catch {}
    setLoading(false);
  }

  const modules = Array.from(new Set(defs.map((d) => d.module))).sort();
  const [moduleFilter, setModuleFilter] = useState("all");

  const filtered = defs.filter((d) => {
    const matchSearch = !search || d.event_code.includes(search) || d.event_name.toLowerCase().includes(search.toLowerCase());
    const matchModule = moduleFilter === "all" || d.module === moduleFilter;
    return matchSearch && matchModule;
  });

  if (loading) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Event Definitions</h1>
        <p className="text-sm text-gray-500 mt-1">All event types registered in the system ({defs.length} total)</p>
      </div>

      <div className="flex gap-3">
        <input
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          placeholder="Search event code or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          value={moduleFilter}
          onChange={(e) => setModuleFilter(e.target.value)}
        >
          <option value="all">All modules</option>
          {modules.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-700">Event Code</th>
              <th className="text-left px-4 py-3 font-medium text-gray-700">Name</th>
              <th className="text-left px-4 py-3 font-medium text-gray-700">Module</th>
              <th className="text-left px-4 py-3 font-medium text-gray-700">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filtered.map((d) => (
              <tr key={d.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <code className="text-indigo-700 font-mono text-xs">{d.event_code}</code>
                </td>
                <td className="px-4 py-3 text-gray-900">{d.event_name}</td>
                <td className="px-4 py-3">
                  <span className="bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded">{d.module}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${d.active_flag ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {d.active_flag ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">No definitions found</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
