import { api } from "./api";
import type { DashboardData } from "../types";

export const dashboardService = {
  get() {
    return api.get<DashboardData>("/api/dashboard");
  },
};
