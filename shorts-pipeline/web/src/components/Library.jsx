import { useState } from "react";
import { api, store } from "../api.js";
import { Avatar, Empty, PostedToggle } from "./common.jsx";
import { ask } from "./Confirm.jsx";
import Icon from "./Icon.jsx";
import { deleteSkit, SkitModal, skitThumb } from "./Skits.jsx";

const FILTERS = { all: "Tất cả", done: "Hoàn thành", running: "Đang chạy", todo: "Chưa xong / lỗi", unposted: "Chưa đăng",
  posted: "Đã đăng" };
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

const KINDS = { all: ["Tất cả", null], story: ["Truyện kể", "🎬"], skit: ["Tiểu phẩm", "🎭"] };
const skitStatus = (s) => s.run?.status === "running" ? ["Đang chạy", "accent"] : s.output ? ["Hoàn thành", "ok"]
  : s.progress?.error ? ["Lỗi", "bad"] : ["Chưa xong", "warn"];

export default function Library({ state, me, admin, openVideo, notify, refresh }) {
  const comments = (name) => state.feedback.filter((f) => f.video === name && !f.parent).length;
  const [owner, setOwner] = useState(me);           // mặc định xem video của mình
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [kind, setKindState] = useState(KINDS[store.get("lib_kind")] ? store.get("lib_kind") : "all");
  const setKind = (k) => { setKindState(k); store.set("lib_kind", k); };
  const [openSkit, setOpenSkit] = useState(null);

  // Truyện kể (videos/) và tiểu phẩm (skits/) chung một danh sách, mỗi mục ghi loại
  const items = [
    ...state.videos.map((v) => ({ ...v, kind: "story", status: videoStatus(v) })),
    ...(state.skits || []).map((s) => ({ ...s, kind: "skit", status: skitStatus(s) })),
  ].sort((a, b) => b.updated - a.updated);
  const ofKind = items.filter((v) => kind === "all" || v.kind === kind);
  const ownerOf = (v) => v.owner || NO_OWNER;
  const owners = [...new Set([me, ...state.users.map((u) => u.name), ...ofKind.map(ownerOf)])];
  const count = (name) => ofKind.filter((v) => ownerOf(v) === name).length;
  const kindCount = (k) => items.filter((v) => k === "all" || v.kind === k).length;

  const list = ofKind.filter((v) => {
    const s = v.status[0];
    if (owner !== "*" && ownerOf(v) !== owner) return false;
    if (filter === "done" && s !== "Hoàn thành") return false;
    if (filter === "running" && s !== "Đang chạy") return false;
    if (filter === "todo" && (s === "Hoàn thành" || s === "Đang chạy")) return false;
    if (filter === "unposted" && (!v.output || v.posted)) return false;      // video xong mà chưa đăng TikTok
    if (filter === "posted" && !v.posted) return false;
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
          <span className="all-icon"><Icon name="users" size={14} /></span><span>Mọi người</span><em>{ofKind.length}</em>
        </button>
      </div>

      <div className="kind-tabs" role="tablist" aria-label="Loại video">
        {Object.entries(KINDS).map(([k, [label, icon]]) => (
          <button key={k} role="tab" aria-selected={kind === k} className={kind === k ? "on" : ""} onClick={() => setKind(k)}>
            {icon && <span>{icon}</span>}{label}<em>{kindCount(k)}</em>
          </button>
        ))}
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
        <Empty icon="▦" title={kind === "skit" ? "Không có tiểu phẩm nào" : "Không có video nào"}>
          {owner === me ? (kind === "skit" ? "Bạn chưa có tiểu phẩm nào. Tạo ở trang Tiểu phẩm."
            : "Bạn chưa có video nào. Tạo video mới ở trang Tạo video hoặc Tiểu phẩm.") : "Thử bỏ bộ lọc hoặc chọn người khác."}
        </Empty>
      )}
      {groups.map(([name, videos]) => (
        <section key={name} className="owner-group">
          {owner === "*" && (
            <h2 className="section-title"><Avatar name={name} size={26} /> {name} <span className="muted">({videos.length})</span></h2>
          )}
          <div className="grid">
            {videos.map((v) => v.kind === "skit"
              ? <SkitTile key={v.name} s={v} showKind={kind === "all"} manage={admin || v.owner === me} onOpen={() => setOpenSkit(v.name)}
                onDelete={() => deleteSkit(v, notify, refresh)} notify={notify} refresh={refresh} />
              : <Tile key={v.name} v={v} showKind={kind === "all"} comments={comments(v.name)} manage={canManage(v, me, admin)}
                onOpen={() => openVideo(v.name)} onDelete={() => deleteVideo(v, notify, refresh)} notify={notify} refresh={refresh} />)}
          </div>
        </section>
      ))}
      {openSkit && (state.skits || []).some((s) => s.name === openSkit) && (
        <SkitModal skit={state.skits.find((s) => s.name === openSkit)} manage={admin || state.skits.find((s) => s.name === openSkit).owner === me}
          notify={notify} refresh={refresh} onClose={() => setOpenSkit(null)} />
      )}
    </>
  );
}

function SkitTile({ s, showKind, manage, onOpen, onDelete, notify, refresh }) {
  const [text, cls] = s.status;
  const thumb = skitThumb(s);
  return (
    <article className="tile" onClick={onOpen}>
      <div className={`thumb ${s.poster ? "" : "thumb-faces"}`}>
        {thumb ? <img src={thumb} alt="" loading="lazy" /> : <span>🎭</span>}
        <span className={`badge ${cls}`}>{text}</span>
        {showKind && <span className="kind-chip skit">🎭 Tiểu phẩm</span>}
        {s.output && <span className="play">▶</span>}
      </div>
      <div className="tile-body">
        <h3>{s.title || "(đang viết...)"}</h3>
        <p className="prompt-line">{s.prompt || s.name}</p>
        <div className="tile-foot" onClick={(e) => e.stopPropagation()}>
          <span className="muted small">{s.lines ? `${s.lines} câu${s.seconds ? ` · ${Math.round(s.seconds)} giây` : ""}` : "chưa có kịch bản"}</span>
          <span className="tile-actions">
            {s.output && <PostedToggle kind="skit" name={s.name} posted={s.posted} manage={manage} notify={notify} refresh={refresh} />}
            {s.output && (
              <a className="tile-btn" href={`/skits/${s.name}/output.mp4?download=1`} title="Tải về máy bạn" aria-label="Tải về máy bạn"><Icon name="download" /></a>
            )}
            {manage && (
              <button className="tile-btn danger" onClick={onDelete} title="Xóa tiểu phẩm" aria-label="Xóa tiểu phẩm"><Icon name="trash" /></button>
            )}
          </span>
        </div>
      </div>
    </article>
  );
}

function Tile({ v, showKind, comments, manage, onOpen, onDelete, notify, refresh }) {
  const [text, cls] = videoStatus(v);
  return (
    <article className="tile" onClick={onOpen}>
      <div className="thumb">
        {v.thumb ? <img src={`/videos/${encodeURIComponent(v.name)}/${v.thumb}`} alt="" loading="lazy" /> : <span>▶</span>}
        <span className={`badge ${cls}`}>{text}</span>
        {showKind && <span className="kind-chip">🎬 Truyện kể</span>}
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
            {v.output && <PostedToggle kind="video" name={v.name} posted={v.posted} manage={manage} notify={notify} refresh={refresh} />}
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
