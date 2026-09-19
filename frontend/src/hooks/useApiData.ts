import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../services/api";
import { useHousehold } from "../context/HouseholdContext";

export function useApiData<T>(fetcher: () => Promise<T>): { data:T|null; isLoading:boolean; error:string|null; reload:()=>void } {
  const { realtimeVersion }=useHousehold();
  const [data,setData]=useState<T|null>(null), [isLoading,setIsLoading]=useState(true), [error,setError]=useState<string|null>(null);
  const [revision,setRevision]=useState(0);
  const fetcherRef=useRef(fetcher); fetcherRef.current=fetcher;
  const reload=useCallback(()=>setRevision(x=>x+1),[]);
  useEffect(()=> {
    let active=true;
    setError(null);
    fetcherRef.current().then(result=> { if(active) setData(result); }).catch(err=> {
      if(active) setError(err instanceof ApiError ? err.message : "Could not load this page.");
    }).finally(()=> { if(active) setIsLoading(false); });
    return ()=> { active=false; };
  },[revision,realtimeVersion]);
  return {data,isLoading,error,reload};
}
