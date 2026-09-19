import type { Priority } from "../../types";
export function PriorityBadge({ priority }: { priority: Priority }) { return <span className="badge">{priority}</span>; }
