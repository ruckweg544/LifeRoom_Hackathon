import { api } from "./api";
import type { Message } from "../types";

export const messageService = {
  create(content: string) { return api.post<Message>("/api/messages", { content }); },
  list(limit = 50) {
    return api.get<Message[]>("/api/messages", { limit });
  },
};
