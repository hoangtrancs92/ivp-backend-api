import { useRef, useState } from "react";
import { api } from "../api.js";

// Cảm xúc kiểu Facebook cho góp ý
export const REACTIONS = {
  like: { emoji: "👍", label: "Thích", colour: "#2563eb" },
  love: { emoji: "❤️", label: "Yêu thích", colour: "#e0384b" },
  haha: { emoji: "😆", label: "Haha", colour: "#d99a06" },
  wow: { emoji: "😮", label: "Wow", colour: "#d99a06" },
  sad: { emoji: "😢", label: "Buồn", colour: "#d99a06" },
  angry: { emoji: "😡", label: "Phẫn nộ", colour: "#e8590c" },
};

export const reactionCounts = (reactions = {}) => {
  const counts = {};
  Object.values(reactions).forEach((r) => { counts[r] = (counts[r] || 0) + 1; });
  return Object.entries(counts).sort((a, b) => b[1] - a[1]);
};

// Nút "Thích": bấm là thả 👍 (hoặc bỏ cảm xúc đang chọn); rê chuột / nhấn giữ hiện thanh 6 cảm xúc
export function ReactButton({ item, me, refresh, notify }) {
  const mine = item.reactions?.[me];
  const [open, setOpen] = useState(false);
  const timer = useRef(null);
  const held = useRef(false);

  const react = (reaction) => {
    setOpen(false);
    api("/api/feedback/react", { id: item.id, reaction }).then(refresh).catch((e) => notify(e.message, "bad"));
  };
  const show = () => { clearTimeout(timer.current); timer.current = setTimeout(() => setOpen(true), 350); };
  const hide = () => { clearTimeout(timer.current); timer.current = setTimeout(() => setOpen(false), 300); };
  const touchStart = () => { held.current = false; timer.current = setTimeout(() => { held.current = true; setOpen(true); }, 400); };
  const touchEnd = (e) => { clearTimeout(timer.current); if (held.current) e.preventDefault(); };

  return (
    <span className="react-wrap" onMouseEnter={show} onMouseLeave={hide}>
      {open && (
        <span className="react-bar" role="menu" onMouseEnter={() => clearTimeout(timer.current)}>
          {Object.entries(REACTIONS).map(([key, r], i) => (
            <button key={key} className={`react-pick ${mine === key ? "on" : ""}`} style={{ animationDelay: `${i * 25}ms` }}
              onClick={() => react(key)} title={r.label} aria-label={r.label}>
              <span>{r.emoji}</span><em>{r.label}</em>
            </button>
          ))}
        </span>
      )}
      <button className="link-btn react-btn" style={mine ? { color: REACTIONS[mine].colour } : undefined}
        onClick={() => react(mine || "like")} onTouchStart={touchStart} onTouchEnd={touchEnd}
        onContextMenu={(e) => e.preventDefault()}>
        {mine ? <><span className="react-mini">{REACTIONS[mine].emoji}</span>{REACTIONS[mine].label}</> : "Thích"}
      </button>
    </span>
  );
}

// Top 3 cảm xúc + tổng số, rê chuột xem ai đã thả gì
export function ReactionSummary({ reactions, compact }) {
  const counts = reactionCounts(reactions);
  const total = Object.keys(reactions || {}).length;
  if (!total) return null;
  const who = Object.entries(reactions).map(([u, r]) => `${REACTIONS[r]?.emoji} ${u}`).join("\n");
  return (
    <span className={`react-summary ${compact ? "compact" : ""}`} title={who}>
      <span className="react-stack">
        {counts.slice(0, 3).map(([r]) => <span key={r} className="react-dot">{REACTIONS[r]?.emoji}</span>)}
      </span>
      <span className="react-total">{total}</span>
    </span>
  );
}
