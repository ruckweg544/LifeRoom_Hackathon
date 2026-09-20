import { api } from "./api";
import type { Chore, Priority } from "../types";

export interface CreateChorePayload {
  source_message_id?: string;
  title: string;
  description?: string | null;
  assigned_to_id?: string | null;
  due_date?: string | null;
  priority?: Priority;
}

export interface UpdateChorePayload {
  title?: string;
  description?: string | null;
  assigned_to_id?: string | null;
  due_date?: string | null;
  priority?: Priority;
  completed?: boolean;
}

export const choreService = {
  list() {
    return api.get<Chore[]>("/api/chores");
  },
  create(payload: CreateChorePayload) {
    return api.post<Chore>("/api/chores", payload);
  },
  update(id: string, payload: UpdateChorePayload) {
    return api.patch<Chore>(`/api/chores/${id}`, payload);
  },
  remove(id: string) {
    return api.delete<void>(`/api/chores/${id}`);
  },
};
