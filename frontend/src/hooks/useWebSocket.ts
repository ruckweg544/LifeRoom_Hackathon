import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../services/api";
export type ConnectionState = "connecting" | "open" | "closed";
export function useWebSocket({ householdId, token, onMessage }: { householdId: string | null; token: string | null; onMessage: (data: unknown) => void }) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("closed");
  const callback = useRef(onMessage); callback.current = onMessage;
  useEffect(() => {
    if (!householdId || !token) { setConnectionState("closed"); return; }
    let stopped=false; let timer: ReturnType<typeof setTimeout> | undefined; let socket: WebSocket; let attempts=0;
    function connect() {
      if (stopped) return;
      setConnectionState("connecting");
      const current = new WebSocket(wsUrl(householdId!)); socket=current;
      current.onopen=()=> { if (!stopped) current.send(JSON.stringify({token})); };
      current.onmessage=(event)=> {
        if (stopped || current!==socket) return;
        try { const data=JSON.parse(event.data); if (data.type === "ready") { attempts=0; setConnectionState("open"); } callback.current(data); } catch { /* Ignore malformed frames. */ }
      };
      current.onclose=(event)=> {
        if (stopped || current!==socket) return;
        setConnectionState("closed");
        if (event.code!==1008) timer=setTimeout(connect,Math.min(1000*2**attempts++,10000));
      };
      current.onerror=()=>current.close();
    }
    connect();
    return ()=> { stopped=true; clearTimeout(timer); if (socket) { socket.onclose=null; socket.onmessage=null; socket.onopen=null; socket.close(); } };
  },[householdId,token]);
  return { connectionState };
}
