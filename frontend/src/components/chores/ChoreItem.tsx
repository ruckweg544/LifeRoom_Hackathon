import type { Chore } from "../../types";
import { formatDueDate } from "../../utils/date";
export function ChoreItem({ chore, onToggleComplete, onDelete }: { chore: Chore; onToggleComplete: (c: Chore) => void; onDelete: (c: Chore) => void }) {
  return <article className="card item-row"><label><input type="checkbox" checked={chore.completed} onChange={() => onToggleComplete(chore)} /> {chore.title}</label><p>{chore.assigned_to_name || "Unassigned"} · {formatDueDate(chore.due_date)}</p><button onClick={() => onDelete(chore)} aria-label={`Delete ${chore.title}`}>Delete</button></article>;
}
