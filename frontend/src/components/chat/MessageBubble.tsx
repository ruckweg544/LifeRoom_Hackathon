import type { Message } from "../../types";
import { formatTime } from "../../utils/date";
export function MessageBubble({message,isOwn,showSender}:{message:Message;isOwn:boolean;showSender:boolean}) { return <article className={`message-bubble ${isOwn ? "message-bubble--own" : ""}`}>{showSender && <strong>{message.sender_name}</strong>}<p style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{message.content}</p><small>{formatTime(message.created_at)}</small></article>; }
