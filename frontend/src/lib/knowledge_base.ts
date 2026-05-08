import { apiClient } from "@/lib/api";

const BASE = "/api/v1/kb";

export interface KBCategory {
  id: string;
  slug: string;
  name: string;
  description?: string;
  parent_id?: string;
  display_order: number;
  icon?: string;
  article_count: number;
}

export interface KBArticle {
  id: string;
  slug: string;
  title: string;
  summary?: string;
  category_id?: string;
  category_name?: string;
  tags: string[];
  status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
  version: number;
  author_name?: string;
  view_count: number;
  is_featured: boolean;
  published_at?: string;
  updated_at?: string;
}

export interface KBArticleDetail extends KBArticle {
  content_md: string;
  access_level: string;
}

export interface KBRevision {
  id: string;
  version_no: number;
  title: string;
  change_summary?: string;
  changed_by_name?: string;
  created_at: string;
}

export interface KBStats {
  total_articles: number;
  published: number;
  drafts: number;
  categories: number;
  top_articles: { id: string; title: string; view_count: number }[];
}

export const kbApi = {
  listCategories: (parent_id?: string) => {
    const q = parent_id ? `?parent_id=${parent_id}` : "";
    return apiClient.get<KBCategory[]>(`${BASE}/categories${q}`).then(r => r.data);
  },
  createCategory: (data: object) =>
    apiClient.post<{ id: string; slug: string }>(`${BASE}/categories`, data).then(r => r.data),
  updateCategory: (id: string, data: object) =>
    apiClient.patch<{ id: string }>(`${BASE}/categories/${id}`, data).then(r => r.data),

  listArticles: (params?: { category_id?: string; status?: string; search?: string; tag?: string; limit?: number; offset?: number }) =>
    apiClient.get<KBArticle[]>(`${BASE}/articles`, { params }).then(r => r.data),
  getArticle: (id: string) =>
    apiClient.get<KBArticleDetail>(`${BASE}/articles/${id}`).then(r => r.data),
  createArticle: (data: object) =>
    apiClient.post<{ id: string; slug: string; status: string }>(`${BASE}/articles`, data).then(r => r.data),
  updateArticle: (id: string, data: object) =>
    apiClient.patch<{ id: string; version: number; status: string }>(`${BASE}/articles/${id}`, data).then(r => r.data),
  deleteArticle: (id: string) =>
    apiClient.delete<{ ok: boolean }>(`${BASE}/articles/${id}`).then(r => r.data),
  listRevisions: (articleId: string) =>
    apiClient.get<KBRevision[]>(`${BASE}/articles/${articleId}/revisions`).then(r => r.data),

  search: (q: string, limit = 20) =>
    apiClient.get<KBArticle[]>(`${BASE}/search`, { params: { q, limit } }).then(r => r.data),
  getStats: () =>
    apiClient.get<KBStats>(`${BASE}/stats`).then(r => r.data),
};
