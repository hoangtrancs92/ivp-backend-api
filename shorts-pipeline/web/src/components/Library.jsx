import { useState } from "react";
import { api } from "../api.js";
import { Avatar, Empty } from "./common.jsx";
import { ask } from "./Confirm.jsx";
import Icon from "./Icon.jsx";

const FILTERS = { all: "Tất cả", done: "Hoàn thành", running: "Đang chạy", todo: "Chưa xong / lỗi" };
const NO_OWNER = "(chưa rõ)";

export const videoStatus = (v) => v.fix ? ["✨ Đang sửa cảnh", "accent"]
  : v.fix_review && v.run?.status !== "running" ? ["✨ Chờ xem ảnh sửa", "accent"]
  : v.run?.status === "running" ? ["Đang chạy", "warn"]
  : v.review ? ["Chờ duyệt ảnh", "warn"]
  : v.output ? ["Hoàn thành", "ok"]
    : v.progress?.error || v.run?.status === "failed" ? ["Lỗi", "bad"] : ["Chưa xong", "muted"];

export const canManage = (video, me, admin) => admin || video.owner === me;

export const downloadUrl = (v) => `/videos/${encodeURIComponent(v.name)}/output.mp4?download=1`;

// Xóa cả thư mục video (ảnh, âm thanh, output.mp4) để nhẹ máy. Trả về true nếu đã xóa.
export async function deleteVideo(video, notify, refresh) {
  const running = video.run?.status === "running";
  const ok = await ask({
    tone: "danger", title: "Xóa video này?", confirmText: "Xóa vĩnh viễn",
    subject: <><b>{video.title || video.name}</b><span>{video.name}</span></>,
    details: [
      "Xóa cả thư mục video: ảnh, giọng đọc và output.mp4",
      "Giải phóng dung lượng trên máy chủ",
      ...(running ? ["Video đang chạy sẽ được dừng trước khi xóa"] : []),
      "Không khôi phục được",
    ],
  });
  if (!ok) return false;
  try {
    await api("/api/video/delete", { video: video.name });
    notify(`Đã xóa ${video.name}`);
    refresh();
    return true;
  } catch (e) {
    notify(e.message, "bad");
    return false;
  }
}

export default function Library({ state, me, admin, openVideo, notify, refresh }) {
  const comments = (name) => state.feedback.filter((f) => f.video === name && !f.parent).length;
  const [owner, setOwner] = useState(me);           // mặc định xem video của mình
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

  const ownerOf = (v) => v.owner || NO_OWNER;
  const owners = [...new Set([me, ...state.users.map((u) => u.name), ...state.videos.map(ownerOf)])];
  const count = (name) => state.videos.filter((v) => ownerOf(v) === name).length;

  const list = state.videos.filter((v) => {
    const s = videoStatus(v)[0];
    if (owner !== "*" && ownerOf(v) !== owner) return false;
    if (filter === "done" && s !== "Hoàn thành") return false;
    if (filter === "running" && s !== "Đang chạy") return false;
    if (filter === "todo" && (s === "Hoàn thành" || s === "Đang chạy")) return false;
    const q = query.trim().toLowerCase();
    return !q || `${v.name} ${v.title} ${v.prompt}`.toLowerCase().includes(q);
  });
  // "Mọi người": chia nhóm theo người tạo
  const groups = owner === "*"
    ? owners.map((name) => [name, list.filter((v) => ownerOf(v) === name)]).filter(([, vs]) => vs.length)
    : [[owner, list]];

  return (
    <>
      <div className="owner-tabs">
        {owners.filter((name) => name !== NO_OWNER || count(name)).map((name) => (
          <button key={name} className={owner === name ? "active" : ""} onClick={() => setOwner(name)}>
            <Avatar name={name} size={24} />
            <span>{name === me ? `${name} (tôi)` : name}</span>
            <em>{count(name)}</em>
          </button>
        ))}
        <button className={owner === "*" ? "active" : ""} onClick={() => setOwner("*")}>
          <span className="all-icon"><Icon name="users" size={14} /></span><span>Mọi người</span><em>{state.videos.length}</em>
        </button>
      </div>

      <div className="toolbar">
        <div className="segmented">
          {Object.entries(FILTERS).map(([k, label]) => (
            <button key={k} className={filter === k ? "active" : ""} onClick={() => setFilter(k)}>{label}</button>
          ))}
        </div>
        <input className="search" placeholder="Tìm theo tên, tiêu đề, đề tài..." value={query} onChange={(e) => setQuery(e.target.value)} />
      </div>

      {list.length === 0 && (
        <Empty icon="▦" title="Không có video nào">
          {owner === me ? "Bạn chưa có video nào. Tạo video mới ở trang Tạo video." : "Thử bỏ bộ lọc hoặc chọn người khác."}
        </Empty>
      )}
      {groups.map(([name, videos]) => (
        <section key={name} className="owner-group">
          {owner === "*" && (
            <h2 className="section-title"><Avatar name={name} size={26} /> {name} <span className="muted">({videos.length})</span></h2>
          )}
          <div className="grid">
            {videos.map((v) => (
              <Tile key={v.name} v={v} comments={comments(v.name)} manage={canManage(v, me, admin)} onOpen={() => openVideo(v.name)}
                onDelete={() => deleteVideo(v, notify, refresh)} />
            ))}
          </div>
        </section>
      ))}
    </>
  );
}

function Tile({ v, comments, manage, onOpen, onDelete }) {
  const [text, cls] = videoStatus(v);
  return (
    <article className="tile" onClick={onOpen}>
      <div className="thumb">
        {v.thumb ? <img src={`/videos/${encodeURIComponent(v.name)}/${v.thumb}`} alt="" loading="lazy" /> : <span>▶</span>}
        <span className={`badge ${cls}`}>{text}</span>
        {v.output && <span className="play">▶</span>}
      </div>
      <div className="tile-body">
        <h3>{v.title || v.name}</h3>
        <p className="prompt-line">{v.prompt || v.name}</p>
        <div className="tile-foot" onClick={(e) => e.stopPropagation()}>
          <span className="muted small">
            {v.scenes ? `${v.scenes} cảnh` : "chưa có kịch bản"}
            {comments > 0 && <span className="comment-count" title="Số góp ý"> · 💬 {comments}</span>}
          </span>
          <span className="tile-actions">
            {v.output && (
              <a className="tile-btn" href={downloadUrl(v)} title="Tải về máy bạn" aria-label="Tải về máy bạn"><Icon name="download" /></a>
            )}
            {manage && (
              <button className="tile-btn danger" onClick={onDelete} title="Xóa video và thư mục" aria-label="Xóa video"><Icon name="trash" /></button>
            )}
          </span>
        </div>
      </div>
    </article>
  );
}
