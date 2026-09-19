export type Priority = "low" | "medium" | "high";

export interface Member {
  id: string;
  display_name: string;
  initials: string;
  is_owner: boolean;
  created_at: string;
  online?: boolean;
}

export interface Household {
  id: string;
  name: string;
  room_code: string;
  has_password: boolean;
  created_at: string;
}

export interface SessionResponse {
  household: Household;
  member: Member;
  session_token: string;
  members: Member[];
}

export interface Message {
  id: string;
  household_id: string;
  member_id: string;
  sender_name: string;
  content: string;
  created_at: string;
}

export interface Chore {
  id: string;
  household_id: string;
  title: string;
  description: string | null;
  assigned_to_id: string | null;
  assigned_to_name: string | null;
  created_by_id: string;
  created_by_name: string | null;
  due_date: string | null;
  priority: Priority;
  completed: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface BillParticipant {
  id: string;
  member_id: string;
  member_name: string | null;
  share_cents: number;
  settled: boolean;
}

export interface Bill {
  id: string;
  household_id: string;
  title: string;
  amount_cents: number;
  paid_by_id: string;
  paid_by_name: string | null;
  created_by_id: string;
  created_at: string;
  participants: BillParticipant[];
}

export interface GroceryItem {
  id: string;
  household_id: string;
  name: string;
  quantity: number;
  added_by_id: string;
  added_by_name: string | null;
  purchased: boolean;
  created_at: string;
}

export type ActivityType =
  | "CHORE_CREATED"
  | "CHORE_COMPLETED"
  | "CHORE_REOPENED"
  | "BILL_CREATED"
  | "BILL_SETTLED"
  | "GROCERY_ADDED"
  | "GROCERY_PURCHASED"
  | "MEMBER_JOINED"
  | "HOUSEHOLD_CREATED";

export interface Activity {
  id: string;
  household_id: string;
  type: ActivityType;
  actor_name: string;
  message: string;
  created_at: string;
}

export interface DashboardSummary {
  chores_due: number;
  you_owe_cents: number;
  you_are_owed_cents: number;
  groceries_needed: number;
  members_online: number;
  members_total: number;
}

export interface DashboardData {
  summary: DashboardSummary;
  todays_chores: Chore[];
  recent_messages: Message[];
  upcoming_bills: Bill[];
  grocery_preview: GroceryItem[];
  recent_activity: Activity[];
}

export interface ApiErrorShape {
  detail?: string;
  errors?: { field: string; message: string }[];
}
