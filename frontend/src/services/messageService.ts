import { api } from "./api";
import type { Message } from "../types";

export interface MessageAnalysis {
  message_id: string;
  is_task: boolean;
  suggestion: { title: string; assigned_to_id: string | null; due_date: string | null; due_at?: string | null } | null;
}

export const messageService = {
  analyze(id: string) { return api.post<MessageAnalysis>(`/api/messages/${encodeURIComponent(id)}/analyze`); },
  create(content: string) { return api.post<Message>("/api/messages", { content }); },
  list(limit = 50) {
    return api.get<Message[]>("/api/messages", { limit });
  },
};
