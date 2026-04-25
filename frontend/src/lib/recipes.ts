import { apiClient } from "@/lib/api";

export type RecipeStatus = "DRAFT" | "APPROVED" | "OBSOLETE";

export interface Recipe {
  id: string;
  product_id: string;
  product_name?: string;
  product_sku?: string;
  version: string;
  name: string;
  description?: string;
  status: RecipeStatus;
  is_active: boolean;
  valid_from?: string;
  valid_to?: string;
  created_by?: string;
  approved_by?: string;
}

export interface RecipeItem {
  id: string;
  recipe_id: string;
  material_id: string;
  material_name?: string;
  material_code?: string;
  line_no: number;
  quantity: number;
  unit: string;
  loss_percentage: number;
  is_optional: boolean;
  alternative_group?: string;
  notes?: string;
}

export interface ProcessParameter {
  id: string;
  recipe_id: string;
  step_no: number;
  step_name: string;
  target_temperature?: number;
  target_ph?: number;
  target_viscosity?: number;
  mixing_time_minutes?: number;
  rpm?: number;
  notes?: string;
}

export interface RecipeDetail extends Recipe {
  items: RecipeItem[];
  process_parameters: ProcessParameter[];
}

export interface RecipeCreate {
  product_id: string;
  version: string;
  name: string;
  description?: string;
  is_active?: boolean;
  valid_from?: string;
  valid_to?: string;
}

export interface RecipeItemCreate {
  material_id: string;
  line_no: number;
  quantity: number;
  unit: string;
  loss_percentage?: number;
  is_optional?: boolean;
  alternative_group?: string;
  notes?: string;
}

export interface ProcessParameterCreate {
  step_no: number;
  step_name: string;
  target_temperature?: number;
  target_ph?: number;
  target_viscosity?: number;
  mixing_time_minutes?: number;
  rpm?: number;
  notes?: string;
}

export const recipesApi = {
  async list(params?: { product_id?: string; status?: RecipeStatus; skip?: number; limit?: number }): Promise<Recipe[]> {
    const res = await apiClient.get<Recipe[]>("/api/v1/recipes/", { params }).then((r) => r.data);
    return res.data;
  },

  async get(id: string): Promise<RecipeDetail> {
    const res = await apiClient.get<RecipeDetail>(`/api/v1/recipes/${id}`).then((r) => r.data);
    return res.data;
  },

  async create(data: RecipeCreate): Promise<Recipe> {
    const res = await apiClient.post<Recipe>("/api/v1/recipes/", data).then((r) => r.data);
    return res.data;
  },

  async update(id: string, data: Partial<RecipeCreate>): Promise<Recipe> {
    const res = await apiClient.patch<Recipe>(`/api/v1/recipes/${id}`, data).then((r) => r.data);
    return res.data;
  },

  async approve(id: string): Promise<Recipe> {
    const res = await apiClient.post<Recipe>(`/api/v1/recipes/${id}/approve`).then((r) => r.data);
    return res.data;
  },

  async obsolete(id: string): Promise<Recipe> {
    const res = await apiClient.post<Recipe>(`/api/v1/recipes/${id}/obsolete`).then((r) => r.data);
    return res.data;
  },

  async duplicate(id: string, new_version: string, new_name?: string): Promise<Recipe> {
    const res = await apiClient.post<Recipe>(`/api/v1/recipes/${id}/duplicate`, { new_version, new_name }).then((r) => r.data);
    return res.data;
  },

  async addItem(recipeId: string, data: RecipeItemCreate): Promise<RecipeItem> {
    const res = await apiClient.post<RecipeItem>(`/api/v1/recipes/${recipeId}/items`, data).then((r) => r.data);
    return res.data;
  },

  async updateItem(recipeId: string, itemId: string, data: Partial<RecipeItemCreate>): Promise<RecipeItem> {
    const res = await apiClient.patch<RecipeItem>(`/api/v1/recipes/${recipeId}/items/${itemId}`, data).then((r) => r.data);
    return res.data;
  },

  async deleteItem(recipeId: string, itemId: string): Promise<void> {
    await apiClient.delete(`/api/v1/recipes/${recipeId}/items/${itemId}`).then((r) => r.data);
  },

  async addProcessParam(recipeId: string, data: ProcessParameterCreate): Promise<ProcessParameter> {
    const res = await apiClient.post<ProcessParameter>(`/api/v1/recipes/${recipeId}/process-parameters`, data).then((r) => r.data);
    return res.data;
  },

  async updateProcessParam(recipeId: string, paramId: string, data: Partial<ProcessParameterCreate>): Promise<ProcessParameter> {
    const res = await apiClient.patch<ProcessParameter>(`/api/v1/recipes/${recipeId}/process-parameters/${paramId}`, data).then((r) => r.data);
    return res.data;
  },

  async deleteProcessParam(recipeId: string, paramId: string): Promise<void> {
    await apiClient.delete(`/api/v1/recipes/${recipeId}/process-parameters/${paramId}`).then((r) => r.data);
  },

  async deleteRecipe(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/recipes/${id}`).then((r) => r.data);
  },
};
