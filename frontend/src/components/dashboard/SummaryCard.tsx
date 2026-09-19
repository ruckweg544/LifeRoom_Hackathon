import type { ReactNode } from "react";
import { Link } from "react-router-dom";
export function SummaryCard({label,value,icon,to}:{label:string;value:string;icon:ReactNode;to:string}) { return <Link className="card" to={to}><p>{icon} {label}</p><strong style={{fontSize:24}}>{value}</strong></Link>; }
