"use client";
import { useEffect, useState } from "react";
import { calendarApi, CalendarResource, ResourceType, ResourceStatus, RESOURCE_ICON } from "@/lib/calendar";

const TYPES: ResourceType[] = ["employee", "room", "vehicle", "machine", "external"];
const STATUSES: ResourceStatus[] = ["active", "inactive", "maintenance"];

export default function ResourcesPage() {
  const [resources, setResources] = useState<CalendarResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<CalendarResource | null>(null);
  const [form, setForm] = useState({
    resource_type: "room" as ResourceType,
    name: "", capacity: 1, location: "", description: "",
    status: "active" as ResourceStatus,
  });

  const load = () => calendarApi.listResources().then(setResources).finally(() => setLoading(false));
  useEffect(() => { load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ resource_type: "room", name: "", capacity: 1, location: "", description: "", status: "active" });
    setShowForm(true);
  };

  const openEdit = (r: CalendarResource) => {
    setEditing(r);
    setForm({
      resource_type: r.resource_type, name: r.name, capacity: r.capacity,
      location: r.location ?? "", description: r.description ?? "", status: r.status,
    });
    setShowForm(true);
  };

  const save = async () => {
    if (editing) {
      await calendarApi.updateResource(editing.resource_id, form);
    } else {
      await calendarApi.createResource(form);
    }
    setShowForm(false);
    load();
  };

  const setStatus = async (id: string, status: ResourceStatus) => {
    await calendarApi.updateResource(id, { status });
    load();
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Resources</h1>
        <button onClick={openCreate}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          + Add Resource
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-lg p-5 shadow-sm space-y-4">
          <h2 className="font-semibold text-gray-800">{editing ? "Edit Resource" : "New Resource"}</h2>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="text-xs text-gray-500">Type</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.resource_type}
                onChange={e => setForm({ ...form, resource_type: e.target.value as ResourceType })}>
                {TYPES.map(t => <option key={t} value={t}>{RESOURCE_ICON[t]} {t}</option>)}
              </select></div>
            <div><label className="text-xs text-gray-500">Status</label>
              <select className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.status}
                onChange={e => setForm({ ...form, status: e.target.value as ResourceStatus })}>
                {STATUSES.map(s => <option key={s} value={s} className="capitalize">{s}</option>)}
              </select></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Name *</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.name}
                onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            <div><label className="text-xs text-gray-500">Capacity</label>
              <input type="number" min={1} className="w-full border rounded px-2 py-1.5 text-sm mt-1" value={form.capacity}
                onChange={e => setForm({ ...form, capacity: Number(e.target.value) })} /></div>
            <div><label className="text-xs text-gray-500">Location</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1" placeholder="Room 3A, Floor 2…"
                value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-gray-500">Description</label>
              <input className="w-full border rounded px-2 py-1.5 text-sm mt-1"
                value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={save} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700">
              {editing ? "Update" : "Create"}
            </button>
            <button onClick={() => setShowForm(false)} className="rounded border px-4 py-1.5 text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      {loading ? <p className="text-sm text-gray-500">Loading…</p> : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {resources.map(r => (
            <div key={r.resource_id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{RESOURCE_ICON[r.resource_type]}</span>
                    <h3 className="font-semibold text-gray-800">{r.name}</h3>
                  </div>
                  <p className="text-xs text-gray-500 capitalize">{r.resource_type} · Capacity: {r.capacity}</p>
                  {r.location && <p className="text-xs text-gray-400 mt-0.5">{r.location}</p>}
                  {r.description && <p className="text-xs text-gray-500 mt-1">{r.description}</p>}
                </div>
                <span className={`text-xs rounded-full px-2 py-0.5 ${
                  r.status === "active" ? "bg-green-100 text-green-700" :
                  r.status === "maintenance" ? "bg-orange-100 text-orange-700" :
                  "bg-gray-100 text-gray-500"}`}>
                  {r.status}
                </span>
              </div>
              <div className="flex gap-2 mt-3">
                <button onClick={() => openEdit(r)} className="text-xs text-blue-600 hover:underline">Edit</button>
                {r.status === "active" && (
                  <button onClick={() => setStatus(r.resource_id, "inactive")} className="text-xs text-gray-500 hover:underline">Deactivate</button>
                )}
                {r.status !== "active" && (
                  <button onClick={() => setStatus(r.resource_id, "active")} className="text-xs text-green-600 hover:underline">Activate</button>
                )}
                <button onClick={() => setStatus(r.resource_id, "maintenance")} className="text-xs text-orange-500 hover:underline">Set Maintenance</button>
              </div>
            </div>
          ))}
          {resources.length === 0 && (
            <p className="col-span-3 text-center text-gray-400 py-12 text-sm">No resources yet. Add your first resource.</p>
          )}
        </div>
      )}
    </div>
  );
}
