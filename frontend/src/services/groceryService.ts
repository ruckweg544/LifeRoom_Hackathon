import { api } from "./api";
import type { GroceryItem } from "../types";

export interface CreateGroceryPayload {
  name: string;
  quantity?: number;
}

export interface UpdateGroceryPayload {
  name?: string;
  quantity?: number;
  purchased?: boolean;
}

export const groceryService = {
  list() {
    return api.get<GroceryItem[]>("/api/groceries");
  },
  create(payload: CreateGroceryPayload) {
    return api.post<GroceryItem>("/api/groceries", payload);
  },
  update(id: string, payload: UpdateGroceryPayload) {
    return api.patch<GroceryItem>(`/api/groceries/${id}`, payload);
  },
  remove(id: string) {
    return api.delete<void>(`/api/groceries/${id}`);
  },
};
