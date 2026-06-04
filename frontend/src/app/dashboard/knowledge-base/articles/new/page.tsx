"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { kbApi, KBCategory } from "@/lib/knowledge_base";
import { RequirePermission } from "@/components/PermissionGuard";

function NewArticlePageInner() {
  const router = useRouter();
  const [categories, setCategories] = useState<KBCategory[]>([]);
  const [form, setForm] = useState({
    title: "", slug: "", summary: "", content_md: "",
    category_id: "", tags: "", status: "DRAFT",
    is_featured: false, access_level: "all",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { kbApi.listCategories().then(setCategories); }, []);

  const autoSlug = (title: string) =>
    title.toLowerCase().replace(/[^a-z0-9\s-]/g, "").replace(/\s+/g, "-").slice(0, 100);

  const save = async (publish = false) => {
    if (!form.title.trim()) { setError("Title required"); return; }
    const slug = form.slug || autoSlug(form.title);
    setSaving(true); setError("");
    try {
      const tags = form.tags.split(",").map(t => t.trim()).filter(Boolean);
      const result = await kbApi.createArticle({
        title: form.title,
        slug,
        summary: form.summary || null,
        content_md: form.content_md,
        category_id: form.category_id || null,
        tags,
        status: publish ? "PUBLISHED" : form.status,
        is_featured: form.is_featured,
        access_level: form.access_level,
      });
      router.push(`/dashboard/knowledge-base/${result.id}`);
    } catch {
      setError("Failed to save article");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">New Article</h1>
          <p className="text-xs text-gray-500 mt-0.5">Write in Markdown. Preview in the article view.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => save(false)} disabled={saving}
            className="rounded border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50">
            Save Draft
          </button>
          <button onClick={() => save(true)} disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving ? "Saving…" : "Publish"}
          </button>
        </div>
      </div>

      {error && <p className="text-xs text-red-500 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>}

      <div className="grid grid-cols-3 gap-5">
        <div className="col-span-2 space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Title *</label>
            <input type="text" value={form.title}
              onChange={e => setForm(f => ({ ...f, title: e.target.value, slug: f.slug || autoSlug(e.target.value) }))}
              placeholder="e.g. How to create a Purchase Order"
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Summary</label>
            <textarea value={form.summary}
              onChange={e => setForm(f => ({ ...f, summary: e.target.value }))}
              rows={2} placeholder="Brief description shown in article list…"
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none resize-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Content (Markdown)</label>
            <textarea value={form.content_md}
              onChange={e => setForm(f => ({ ...f, content_md: e.target.value }))}
              rows={24}
              placeholder={"# Article Title\n\nWrite your content here in **Markdown**.\n\n## Section 1\n\nStep 1...\n\n## Section 2\n\nStep 2..."}
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:ring-1 focus:ring-blue-500 outline-none resize-y"
            />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">URL Slug</label>
            <input type="text" value={form.slug}
              onChange={e => setForm(f => ({ ...f, slug: e.target.value }))}
              placeholder="auto-generated-from-title"
              className="w-full border rounded px-3 py-2 text-sm font-mono focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Category</label>
            <select value={form.category_id}
              onChange={e => setForm(f => ({ ...f, category_id: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
              <option value="">Uncategorized</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tags (comma-separated)</label>
            <input type="text" value={form.tags}
              onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
              placeholder="sop, procurement, guide"
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Access Level</label>
            <select value={form.access_level}
              onChange={e => setForm(f => ({ ...f, access_level: e.target.value }))}
              className="w-full border rounded px-3 py-2 text-sm focus:ring-1 focus:ring-blue-500 outline-none">
              <option value="all">All Users</option>
              <option value="management">Management Only</option>
              <option value="hr">HR Only</option>
              <option value="finance">Finance Only</option>
              <option value="production">Production Only</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer pt-1">
            <input type="checkbox" checked={form.is_featured}
              onChange={e => setForm(f => ({ ...f, is_featured: e.target.checked }))}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            Featured article
          </label>
          <div className="bg-gray-50 border rounded-lg p-3 text-xs text-gray-500 space-y-1">
            <p className="font-semibold text-gray-600">Markdown tips</p>
            <p><code className="bg-white px-1 rounded"># H1</code> <code className="bg-white px-1 rounded">## H2</code></p>
            <p><code className="bg-white px-1 rounded">**bold**</code> <code className="bg-white px-1 rounded">*italic*</code></p>
            <p><code className="bg-white px-1 rounded">- item</code> for lists</p>
            <p><code className="bg-white px-1 rounded">```code block```</code></p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function NewArticlePage() {
  return (
    <RequirePermission permission="knowledge_base.create">
      <NewArticlePageInner />
    </RequirePermission>
  );
}
