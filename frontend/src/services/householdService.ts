import { api } from "./api";
import type { SessionResponse } from "../types";

export const householdService = {
  create(payload: { display_name: string; household_name: string; password?: string | null }) {
    return api.post<SessionResponse>("/api/households", payload, { auth: false });
  },
  join(payload: { display_name: string; room_code: string; password?: string | null }) {
    return api.post<SessionResponse>("/api/households/join", { ...payload, room_code: payload.room_code.toUpperCase() }, { auth: false });
  },
  me() {
    return api.get<SessionResponse>("/api/households/me");
  },
};
