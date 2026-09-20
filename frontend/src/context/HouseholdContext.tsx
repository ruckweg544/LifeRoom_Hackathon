import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError, clearToken, getStoredToken, storeToken } from "../services/api";
import { householdService } from "../services/householdService";
import { useWebSocket, type ConnectionState } from "../hooks/useWebSocket";
import type { Household, Member, SessionResponse } from "../types";

interface HouseholdContextValue {
  realtimeVersion: number;
  connectionState: ConnectionState;
  household: Household | null;
  currentMember: Member | null;
  members: Member[];
  sessionToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  applySession: (session: SessionResponse) => void;
  updateCurrentMember: (member: Member) => void;
  leaveHousehold: () => void;
}

const HouseholdContext = createContext<HouseholdContextValue | undefined>(undefined);

export function HouseholdProvider({ children }: { children: ReactNode }) {
  const [realtimeVersion, setRealtimeVersion] = useState(0);
  const [household, setHousehold] = useState<Household | null>(null);
  const [currentMember, setCurrentMember] = useState<Member | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [restoreError, setRestoreError] = useState<string | null>(null);

  const applySession = useCallback((session: SessionResponse) => {
    setHousehold(session.household);
    setCurrentMember(session.member);
    setMembers(session.members);
    setSessionToken(session.session_token);
    storeToken(session.session_token);
  }, []);

  const updateCurrentMember = useCallback((member: Member) => {
    setCurrentMember(member);
    setMembers((prev) => prev.map((m) => (m.id === member.id ? member : m)));
  }, []);

  const leaveHousehold = useCallback(() => {
    clearToken();
    setHousehold(null);
    setCurrentMember(null);
    setMembers([]);
    setSessionToken(null);
  }, []);

  useEffect(() => {
    window.addEventListener("liferoom:session-invalid", leaveHousehold);
    return () => window.removeEventListener("liferoom:session-invalid", leaveHousehold);
  }, [leaveHousehold]);

  // On first load, try to restore a session from a stored token.
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    setSessionToken(token);
    householdService
      .me()
      .then((session) => {
        setHousehold(session.household);
        setCurrentMember(session.member);
        setMembers(session.members);
      })
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401) {
          clearToken();
          setSessionToken(null);
        } else {
          setRestoreError("Could not restore your session. Your saved session has been kept.");
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const { connectionState } = useWebSocket({
    householdId: household?.id || null, token: sessionToken,
    onMessage: () => setRealtimeVersion(value => value + 1),
  });
  useEffect(() => {
    if (!household || !sessionToken) return;
    let active = true;
    householdService.me().then(session => { if (active) setMembers(session.members); }).catch(() => {});
    return () => { active = false; };
  }, [household, sessionToken, realtimeVersion]);

  const value = useMemo(
    () => ({
      realtimeVersion, connectionState, household,
      currentMember,
      members,
      sessionToken,
      isLoading,
      isAuthenticated: Boolean(household && currentMember && sessionToken),
      applySession,
      updateCurrentMember,
      leaveHousehold,
    }),
    [realtimeVersion, connectionState, household, currentMember, members, sessionToken, isLoading, applySession, updateCurrentMember, leaveHousehold]
  );

  return <HouseholdContext.Provider value={value}>{restoreError ? <div role="alert">{restoreError} <button onClick={() => window.location.reload()}>Retry</button></div> : children}</HouseholdContext.Provider>;
}

export function useHousehold(): HouseholdContextValue {
  const ctx = useContext(HouseholdContext);
  if (!ctx) throw new Error("useHousehold must be used within a HouseholdProvider");
  return ctx;
}
