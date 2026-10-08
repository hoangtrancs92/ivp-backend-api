import { useState } from "react";
import { ago, api } from "../api.js";
import { Avatar } from "./common.jsx";
import { ask } from "./Confirm.jsx";
import { ReactButton, ReactionSummary } from "./Reactions.jsx";

export const clock = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export function Stars({ value, onChange, size = 16 }) {
  return (
    <span className={`stars ${onChange ? "editable" : ""}`} style={{ fontSize: size }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" className={n <= (value || 0) ? "on" : ""} disabled={!onChange}
          onClick={() => onChange?.(value === n ? null : n)} aria-label={`${n} sao`}>★</button>
      ))}
    </span>
  );
}

// Góp ý dưới một video, kiểu bình luận Facebook: hạng mục, chấm sao, gắn thời điểm, thích, trả lời
export default function Comments({ video, state, me, admin, refresh, notify, player }) {
  const items = state.feedback.filter((f) => f.video === video.name);
  const roots = items.filter((f) => !f.parent).sort((a, b) => b.created - a.created);
  const replies = (id) => items.filter((f) => f.parent === id).sort((a, b) => a.created - b.created);
  const rated = roots.filter((f) => f.rating);

  return (
    <section className="comments">
      <div className="comments-head">
        <h3>Góp ý <span className="muted">({roots.length})</span></h3>
        {rated.length > 0 && (
          <span className="muted small">
            <Stars value={Math.round(rated.reduce((s, f) => s + f.rating, 0) / rated.length)} size={13} />{" "}
            {(rated.reduce((s, f) => s + f.rating, 0) / rated.length).toFixed(1)}/5 · {rated.length} lượt chấm
          </span>
        )}
      </div>
      <Composer video={video} me={me} categories={state.categories} player={player} refresh={refresh} notify={notify} />
      {roots.length === 0 && <p className="muted small empty-comments">Chưa có góp ý nào. Hãy là người đầu tiên nhận xét video này.</p>}
      <ul className="comment-list">
        {roots.map((f) => (
          <Comment key={f.id} f={f} replies={replies(f.id)} me={me} admin={admin} categories={state.categories}
            player={player} refresh={refresh} notify={notify} />
        ))}
      </ul>
    </section>
  );
}

function Composer({ video, me, categories, player, refresh, notify, parent, onDone, autoFocus }) {
  const [text, setText] = useState("");
  const [category, setCategory] = useState(null);
  const [rating, setRating] = useState(null);
  const [at, setAt] = useState(null);
  const [busy, setBusy] = useState(false);

  const send = async () => {
    setBusy(true);
    try {
      await api("/api/feedback", { video: video?.name, parent, text, category, rating, at });
      setText(""); setCategory(null); setRating(null); setAt(null);
      refresh();
      onDone?.();
    } catch (e) {
      notify(e.message, "bad");
    } finally {
      setBusy(false);
    }
  };
  const mark = () => {
    const t = player?.current?.currentTime;
    if (t != null) setAt(at === null ? t : null);
  };

  return (
    <div className={`composer-comment ${parent ? "reply" : ""}`}>
      <Avatar name={me} size={parent ? 28 : 36} />
      <div className="comment-box">
        <textarea rows={parent ? 1 : 2} value={text} autoFocus={autoFocus} onChange={(e) => setText(e.target.value)}
          placeholder={parent ? "Viết phản hồi..." : "Góp ý cho video này: điểm tốt, chỗ cần sửa, gợi ý cải thiện..."}
          onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && text.trim()) send(); }} />
        {!parent && (
          <div className="comment-tools">
            <div className="cat-chips">
              {Object.entries(categories).map(([k, label]) => (
                <button key={k} type="button" className={category === k ? "on" : ""} onClick={() => setCategory(category === k ? null : k)}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="comment-actions">
          {!parent && <Stars value={rating} onChange={setRating} />}
          {!parent && player?.current && (
            <button type="button" className={`chip-btn ${at !== null ? "on" : ""}`} onClick={mark}
              title="Gắn thời điểm đang phát của video vào góp ý">
              ⏱ {at !== null ? `tại ${clock(at)}` : "Gắn thời điểm"}
            </button>
          )}
          <span className="grow" />
          {parent && <button type="button" className="ghost small-btn" onClick={onDone}>Hủy</button>}
          <button type="button" className="primary small-btn" disabled={busy || text.trim().length < 2} onClick={send}>
            {parent ? "Trả lời" : "Gửi góp ý"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Comment({ f, replies = [], me, admin, categories, player, refresh, notify, isReply }) {
  const [replying, setReplying] = useState(false);
  const act = (action, extra = {}) => api(`/api/feedback/${action}`, { id: f.id, ...extra }).then(refresh)
    .catch((e) => notify(e.message, "bad"));
  const remove = async () => {
    if (await ask({ tone: "danger", title: "Xóa góp ý này?", confirmText: "Xóa", message: replies.length ? "Các phản hồi bên dưới cũng bị xóa." : undefined })) act("delete");
  };
  const seek = () => {
    if (player?.current && f.at != null) { player.current.currentTime = f.at; player.current.play?.(); }
  };

  return (
    <li className={`comment ${f.resolved ? "resolved" : ""}`}>
      <Avatar name={f.user} size={isReply ? 28 : 36} />
      <div className="comment-main">
        <div className="bubble">
          <div className="bubble-head">
            <b>{f.user}</b>
            {f.category && <span className="cat-badge">{categories[f.category]}</span>}
            {f.rating && <Stars value={f.rating} size={12} />}
            {f.resolved && <span className="badge inline ok">✓ Đã xử lý{f.resolved_by ? ` · ${f.resolved_by}` : ""}</span>}
          </div>
          <p>
            {f.at != null && <button className="time-link" onClick={seek} title="Tua tới đoạn này">{clock(f.at)}</button>}
            {f.text}
          </p>
          {f.note && <p className="resolve-note">Cách xử lý: {f.note}</p>}
          <ReactionSummary reactions={f.reactions} />
        </div>
        <div className="comment-meta">
          <span className="muted">{ago(f.created)}</span>
          <ReactButton item={f} me={me} refresh={refresh} notify={notify} />
          {!isReply && <button className="link-btn" onClick={() => setReplying(!replying)}>Trả lời</button>}
          {admin && !isReply && (
            <button className="link-btn" onClick={() => act("resolve")}>{f.resolved ? "Bỏ đánh dấu" : "Đánh dấu đã xử lý"}</button>
          )}
          {(admin || f.user === me) && <button className="link-btn danger-text" onClick={remove}>Xóa</button>}
        </div>
        {(replies.length > 0 || replying) && (
          <ul className="comment-list replies">
            {replies.map((r) => (
              <Comment key={r.id} f={r} me={me} admin={admin} categories={categories} refresh={refresh} notify={notify} isReply />
            ))}
            {replying && (
              <li><Composer parent={f.id} me={me} categories={categories} refresh={refresh} notify={notify}
                autoFocus onDone={() => setReplying(false)} /></li>
            )}
          </ul>
        )}
      </div>
    </li>
  );
}
