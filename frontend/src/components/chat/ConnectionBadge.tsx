import type { ConnectionState } from "../../hooks/useWebSocket";
export function ConnectionBadge({state}:{state:ConnectionState}) { return <span className="badge" role="status">{state=== "open" ? "Connected" : state === "connecting" ? "Connecting…" : "Offline"}</span>; }
