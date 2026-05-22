"use client";
import { useEffect, useState } from "react";
import { kbApi, KBCategory } from "@/lib/knowledge_base";

interface CategoryForm {
  name: string;
  slug: string;
  description: string;
  icon: string;
  display_order: number;
}

const EMPTY_FORM: CategoryForm = { name: "", slug: "", description: "", icon: "", display_order: 0 };

function slugify(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export default function KBCategoriesPage() {
  const [categories, setCategories] = useState<KBCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CategoryForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const [editId, setEditId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<CategoryForm>(EMPTY_FORM);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const cats = await kbApi.listCategories();
      setCategories(cats);
    } catch {
      setError("Failed to load categories.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) { setSaveError("Name is required."); return; }
    setSaving(true); setSaveError("");
    try {
      await kbApi.createCategory({
        name: form.name.trim(),
        slug: form.slug.trim() || slugify(form.name),
        description: form.description.trim() || undefined,
        icon: form.icon.trim() || undefined,
        display_order: form.display_order,
      });
      setShowCreate(false);
      setForm(EMPTY_FORM);
      await load();
    } catch {
      setSaveError("Failed to create category.");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (c: KBCategory) => {
    setEditId(c.id);
    setEditForm({ name: c.name, slug: c.slug, description: c.description ?? "", icon: c.icon ?? "", display_order: c.display_order });
    setEditError("");
  };

  const handleEdit = async () => {
    if (!editId || !editForm.name.trim()) { setEditError("Name is required."); return; }
    setEditSaving(true); setEditError("");
    try {
      await kbApi.updateCategory(editId, {
        name: editForm.name.trim(),
        slug: editForm.slug.trim() || slugify(editForm.name),
        description: editForm.description.trim() || undefined,
        icon: editForm.icon.trim() || undefined,
        display_order: editForm.display_order,
      });
      setEditId(null);
      await load();
    } catch {
      setEditError("Failed to update category.");
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
            <a href="/dashboard/knowledge-base" className="hover:underline text-blue-600">Knowledge Base</a>
            <span>/</span>
            <span>Categories</span>
          </div>
          <h1 className="text-xl font-bold text-gray-900">Knowledge Base Categories</h1>
          <p className="text-xs text-gray-500 mt-0.5">Organise articles into categories.</p>
        </div>
        <button
          onClick={() => { setShowCreate(true); setSaveError(""); setForm(EMPTY_FORM); }}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          + New Category
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-blue-900">New Category</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Name *</label>
              <input
                type="text"
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value, slug: slugify(e.target.value) }))}
                placeholder="e.g. HR Policies"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Slug</label>
              <input
                type="text"
                value={form.slug}
                onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
                placeholder="auto-generated"
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Icon (emoji)</label>
              <input
                type="text"
                value={form.icon}
                onChange={e => setForm(f => ({ ...f, icon: e.target.value }))}
                placeholder="e.g. 📄"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 block mb-1">Display Order</label>
              <input
                type="number"
                value={form.display_order}
                onChange={e => setForm(f => ({ ...f, display_order: parseInt(e.target.value) || 0 }))}
                min={0}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs font-medium text-gray-600 block mb-1">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                placeholder="Short description (optional)"
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              />
            </div>
          </div>
          {saveError && <p className="text-xs text-red-600">{saveError}</p>}
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={saving}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? "Saving…" : "Create Category"}
            </button>
            <button onClick={() => setShowCreate(false)}
              className="rounded border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      {error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">{error}</div>
      ) : loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : categories.length === 0 ? (
        <div className="bg-white border rounded-xl p-10 text-center text-gray-400 text-sm">
          No categories yet. Create one to get started.
        </div>
      ) : (
        <div className="bg-white border rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Icon</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Slug</th>
                <th className="px-4 py-3 text-left">Description</th>
                <th className="px-4 py-3 text-right">Articles</th>
                <th className="px-4 py-3 text-right">Order</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {categories.map(c => (
                editId === c.id ? (
                  <tr key={c.id} className="bg-blue-50">
                    <td className="px-4 py-2">
                      <input type="text" value={editForm.icon}
                        onChange={e => setEditForm(f => ({ ...f, icon: e.target.value }))}
                        className="w-16 border rounded px-2 py-1 text-sm" />
                    </td>
                    <td className="px-4 py-2">
                      <input type="text" value={editForm.name}
                        onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                        className="w-full border rounded px-2 py-1 text-sm" />
                    </td>
                    <td className="px-4 py-2">
                      <input type="text" value={editForm.slug}
                        onChange={e => setEditForm(f => ({ ...f, slug: e.target.value }))}
                        className="w-full border rounded px-2 py-1 text-sm font-mono" />
                    </td>
                    <td className="px-4 py-2">
                      <input type="text" value={editForm.description}
                        onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                        className="w-full border rounded px-2 py-1 text-sm" />
                    </td>
                    <td className="px-4 py-2 text-right text-gray-500">{c.article_count}</td>
                    <td className="px-4 py-2">
                      <input type="number" value={editForm.display_order}
                        onChange={e => setEditForm(f => ({ ...f, display_order: parseInt(e.target.value) || 0 }))}
                        className="w-16 border rounded px-2 py-1 text-sm text-right" />
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex gap-2 items-center">
                        <button onClick={handleEdit} disabled={editSaving}
                          className="text-xs text-blue-600 hover:underline disabled:opacity-50">
                          {editSaving ? "Saving…" : "Save"}
                        </button>
                        <button onClick={() => setEditId(null)} className="text-xs text-gray-500 hover:underline">Cancel</button>
                        {editError && <span className="text-xs text-red-600">{editError}</span>}
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-lg">{c.icon || "—"}</td>
                    <td className="px-4 py-3 font-medium text-gray-800">
                      <a href={`/dashboard/knowledge-base/articles?category_id=${c.id}`}
                        className="hover:text-blue-600 hover:underline">
                        {c.name}
                      </a>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.slug}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs max-w-xs truncate">{c.description || "—"}</td>
                    <td className="px-4 py-3 text-right font-medium text-blue-700">{c.article_count}</td>
                    <td className="px-4 py-3 text-right text-gray-500">{c.display_order}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => startEdit(c)}
                        className="text-xs text-blue-600 hover:underline">
                        Edit
                      </button>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
