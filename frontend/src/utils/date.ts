export function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.round(diffMs / 1000);

  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.round(diffHour / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatTime(isoDate: string): string {
  return new Date(isoDate).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatDueDate(isoDate: string | null): string {
  if (!isoDate) return "No due date";
  const date = new Date(isoDate);
  const now = new Date();

  const isSameDay = date.toDateString() === now.toDateString();
  if (isSameDay) return `Today, ${date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;

  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  if (date.toDateString() === tomorrow.toDateString()) return "Tomorrow";

  if (date.getTime() < now.setHours(0, 0, 0, 0)) {
    return `Overdue - ${date.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
  }

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function isOverdue(isoDate: string | null): boolean {
  if (!isoDate) return false;
  return new Date(isoDate).getTime() < Date.now();
}

/** <input type="datetime-local"> needs local time with no timezone suffix. */
export function toDatetimeLocalValue(isoDate: string | null): string {
  if (!isoDate) return "";
  const date = new Date(isoDate);
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}
