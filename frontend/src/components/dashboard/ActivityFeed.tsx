import type { Activity } from "../../types";
export function ActivityFeed({activities}:{activities:Activity[]}) { return activities.length ? <ul>{activities.map(a=><li key={a.id}>{a.message}</li>)}</ul> : <p>No activity yet.</p>; }
