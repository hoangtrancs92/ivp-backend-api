import { useState } from "react";
import { ago, api } from "../api.js";
import { Avatar, Empty } from "./common.jsx";
import { clock, Stars } from "./Comments.jsx";
import Icon from "./Icon.jsx";
import { ReactButton, ReactionSummary } from "./Reactions.jsx";

// Trang tổng hợp góp ý của mọi video: thống kê theo hạng mục, lọc, đánh dấu đã xử lý, xuất Markdown
export default function FeedbackPage({ state, me, admin, openVideo, refresh, notify }) {
  const [status, setStatus] = useState("open");
  const [category, setCategory] = useState("all");
  const [video, setVideo] = useState("all");
  const cats = state.categories;
  const roots = state.feedback.filter((f) => !f.parent);
  const replies = (id) => state.feedback.filter((f) => f.parent === id).length;
  const exists = new Set(state.videos.map((v) => v.name));
  const thumb = (name) => state.videos.find((v) => v.name === name)?.thumb;

  const list = roots
    .filter((f) => status === "all" || (status === "open" ? !f.resolved : f.resolved))
    .filter((f) => category === "all" || (f.category || "other") === category)
    .filter((f) => video === "all" || f.video === video)
    .sort((a, b) => Object.keys(b.reactions).length - Object.keys(a.reactions).length || b.created - a.created);

  const open = roots.filter((f) => !f.resolved);
  const rated = roots.filter((f) => f.rating);
  const avg = rated.length ? rated.reduce((s, f) => s + f.rating, 0) / rated.length : null;
  const byCat = Object.keys(cats).map((k) => [k, open.filter((f) => (f.category || "other") === k).length]);
  const maxCat = Math.max(1, ...byCat.map(([, n]) => n));
  const videos = [...new Set(roots.map((f) => f.video))];

  const resolve = async (f) => {
    try { await api("/api/feedback/resolve", { id: f.id }); refresh(); } catch (e) { notify(e.message, "bad"); }
  };

  if (roots.length === 0) {
    return <Empty icon="💬" title="Chưa có góp ý nào">Mở một video đã hoàn thành ở Thư viện và viết góp ý ngay dưới video.</Empty>;
  }

  return (
    <>
      <div className="stats">
        <div className="stat"><b>{roots.length}</b><span>góp ý</span></div>
        <div className="stat"><b className={open.length ? "warn" : "ok"}>{open.length}</b><span>chưa xử lý</span></div>
        <div className="stat"><b>{avg ? avg.toFixed(1) : "-"}<small className="muted">/5</small></b><span>điểm trung bình ({rated.length} lượt)</span></div>
        <div className="stat"><b>{new Set(roots.map((f) => f.user)).size}</b><span>người góp ý</span></div>
      </div>

      <div className="feedback-layout">
        <aside className="panel padded cat-summary">
          <h2>Chưa xử lý theo hạng mục</h2>
          <p className="muted small">Hạng mục nhiều góp ý nhất là chỗ nên sửa trước trong quy trình.</p>
          {byCat.map(([k, n]) => (
            <button key={k} className={`cat-row ${category === k ? "on" : ""}`} onClick={() => setCategory(category === k ? "all" : k)}>
              <span>{cats[k]}</span><b>{n}</b>
              <i style={{ width: `${(n / maxCat) * 100}%` }} />
            </button>
          ))}
          <a className="button full-btn" href={`/api/feedback/export?resolved=${status === "open" ? 0 : 1}`}>
            <Icon name="download" /> Xuất tổng hợp (.md)
          </a>
          <p className="muted small">File Markdown xếp theo hạng mục, có thể dán cho AI để đề xuất sửa quy tắc viết kịch bản, prompt ảnh, thông số dựng.</p>
        </aside>

        <div className="feedback-main">
          <div className="toolbar">
            <div className="segmented">
              {[["open", "Chưa xử lý"], ["done", "Đã xử lý"], ["all", "Tất cả"]].map(([k, label]) => (
                <button key={k} className={status === k ? "active" : ""} onClick={() => setStatus(k)}>{label}</button>
              ))}
            </div>
            <select value={video} onChange={(e) => setVideo(e.target.value)}>
              <option value="all">Mọi video</option>
              {videos.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>

          {list.length === 0 && <Empty icon="✓" title="Không có góp ý nào ở bộ lọc này">Thử đổi bộ lọc.</Empty>}
          <ul className="fb-list">
            {list.map((f) => (
              <li key={f.id} className={`fb-card ${f.resolved ? "resolved" : ""}`}>
                <button className="fb-thumb" onClick={() => exists.has(f.video) && openVideo(f.video)} title={f.video}>
                  {thumb(f.video) ? <img src={`/videos/${encodeURIComponent(f.video)}/${thumb(f.video)}`} alt="" /> : <span>▶</span>}
                </button>
                <div className="fb-body">
                  <div className="bubble-head">
                    <Avatar name={f.user} size={22} /> <b>{f.user}</b>
                    <span className="cat-badge">{cats[f.category || "other"]}</span>
                    {f.rating && <Stars value={f.rating} size={12} />}
                    <span className="muted small">· {ago(f.created)}</span>
                  </div>
                  <p>{f.at != null && <span className="time-link static">{clock(f.at)}</span>}{f.text}</p>
                  {f.note && <p className="resolve-note">Cách xử lý: {f.note}</p>}
                  <div className="comment-meta">
                    <span className="muted">{exists.has(f.video) ? f.video : `${f.video} (đã xóa)`}</span>
                    <ReactionSummary reactions={f.reactions} compact />
                    <ReactButton item={f} me={me} refresh={refresh} notify={notify} />
                    {replies(f.id) > 0 && <span className="muted">💬 {replies(f.id)} phản hồi</span>}
                    {exists.has(f.video) && <button className="link-btn" onClick={() => openVideo(f.video)}>Mở video</button>}
                    {admin && <button className="link-btn" onClick={() => resolve(f)}>{f.resolved ? "Bỏ đánh dấu" : "✓ Đã xử lý"}</button>}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
