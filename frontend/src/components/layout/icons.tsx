import type { SVGProps } from "react";
const paths = {
  BillIcon: "M6 2h12v20l-3-2-3 2-3-2-3 2V2m3 5h6m-6 4h6m-6 4h6",
  ChatIcon: "M3 3h18v14H9l-6 4V3",
  ChoreIcon: "m4 12 5 5L20 6",
  GroceryIcon: "M2 3h3l3 13h11l3-10H6m4 14h.01M18 20h.01",
  MembersIcon: "M16 21v-3a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v3m18 0v-3a4 4 0 0 0-3-4M9 2a4 4 0 1 0 0 8 4 4 0 0 0 0-8",
  PlusIcon: "M12 4v16M4 12h16",
  SendIcon: "m2 2 20 10-20 10 4-10-4-10m4 10h16",
  CopyIcon: "M9 9h12v12H9zM4 15H2V2h13v2",
};
function icon(name: keyof typeof paths) { return (props: SVGProps<SVGSVGElement>) => <svg {...props} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d={paths[name]} /></svg>; }
export const BillIcon=icon("BillIcon"), ChatIcon=icon("ChatIcon"), ChoreIcon=icon("ChoreIcon"), GroceryIcon=icon("GroceryIcon"), MembersIcon=icon("MembersIcon"), PlusIcon=icon("PlusIcon"), SendIcon=icon("SendIcon"), CopyIcon=icon("CopyIcon");
