import type { Bill } from "../../types";
import { formatCents } from "../../utils/money";
export function BillItem({ bill, onToggleSettled, onDelete }: { bill: Bill; onToggleSettled: (b: Bill, id: string, settled: boolean) => void; onDelete: (b: Bill) => void }) {
  return <article className="card"><div className="page-header"><h3>{bill.title} · {formatCents(bill.amount_cents)}</h3><button onClick={()=>onDelete(bill)} aria-label={`Delete ${bill.title}`}>Delete</button></div><p>Paid by {bill.paid_by_name}</p>{bill.participants.map(p=><label className="item-row" key={p.id}><input type="checkbox" checked={p.settled} disabled={p.member_id===bill.paid_by_id} onChange={()=>onToggleSettled(bill,p.id,!p.settled)} />{p.member_name}: {formatCents(p.share_cents)} {p.settled ? "paid" : "unpaid"}</label>)}</article>;
}
