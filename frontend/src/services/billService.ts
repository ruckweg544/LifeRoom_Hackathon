import { api } from "./api";
import type { Bill } from "../types";

export interface CreateBillPayload {
  title: string;
  amount: number;
  paid_by_id: string;
  participant_ids: string[];
}

export const billService = {
  list() {
    return api.get<Bill[]>("/api/bills");
  },
  create(payload: CreateBillPayload) {
    return api.post<Bill>("/api/bills", payload);
  },
  setSettled(billId: string, participantId: string, settled: boolean) {
    return api.patch<Bill>(`/api/bills/${billId}/participants/${participantId}`, undefined, {
      query: { settled },
    });
  },
  remove(id: string) {
    return api.delete<void>(`/api/bills/${id}`);
  },
};
