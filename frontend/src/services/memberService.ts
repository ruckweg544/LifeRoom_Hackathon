import { api } from "./api";
import type { Member } from "../types";

export const memberService = {
  list() {
    return api.get<(Member & { online: boolean })[]>("/api/members");
  },
  updateMyProfile(displayName: string) {
    return api.patch<Member>("/api/members/me", { display_name: displayName });
  },
};
