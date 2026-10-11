import { useMemo, useState } from "react";
import { api, duration, RUN_STATUS, store } from "../api.js";
import { Avatar, Empty, LogView } from "./common.jsx";
import { ask } from "./Confirm.jsx";

// nhóm trạng thái cho bộ lọc
const GROUPS = {
  all: { label: "Tất cả", test: () => true },
  running: { label: "Đang chạy", test: (r) => r.status === "running" },
  waiting: { label: "Chờ duyệt", test: (r) => r.status === "waiting" },
  failed: { label: "Lỗi", test: (r) => r.status === "failed" },
  done: { label: "Hoàn thành", test: (r) => r.status === "done" },
  stopped: { label: "Dừng / ngắt", test: (r) => r.status === "stopped" || r.status === "interrupted" },
};
const ACTION_ICON = { auto: "🎬", fix: "✨", fix_apply: "🛠", upload_lora: "☁️" };

const dayKey = (t) => new Date(t * 1000).toDateString();
const dayLabel = (t) => {
  const d = new Date(t * 1000), today = new Date(), yesterday = new Date(Date.now() - 86400000);
  if (d.toDateString() === today.toDateString()) return "Hôm nay";
  if (d.toDateString() === yesterday.toDateString()) return "Hôm qua";
  return d.toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit" });
};
const clock = (t) => new Date(t * 1000).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

export default function Activity({ state, me, admin, openVideo, notify, refresh }) {
  const [group, setGroup] = useState(store.get("act_group", "all"));
  const [who, setWho] = useState("");
  const [action, setAction] = useState("");
  const [query, setQuery] = useState("");
  const [logId, setLogId] = useState(null);
  const now = Date.now() / 1000;
  const titles = useMemo(() => Object.fromEntries(state.videos.map((v) => [v.name, v.title])), [state.videos]);
  const pickGroup = (g) => { store.set("act_group", g); setGroup(g); };

  if (state.runs.length === 0) return <Empty icon="≡" title="Chưa có hoạt động">Mỗi lần ai đó chạy việc sẽ được ghi ở đây.</Empty>;

  const today = dayKey(now);
  const count = (g) => state.runs.filter(GROUPS[g].test).length;
  const todayCount = (status) => state.runs.filter((r) => r.status === status && dayKey(r.started) === today).length;
  const users = [...new Set(state.runs.map((r) => r.user))].sort();
  const actions = [...new Set(state.runs.map((r) => r.action || "auto"))];
  const labels = Object.fromEntries(state.runs.map((r) => [r.action || "auto", r.label]));

  const q = query.trim().toLowerCase();
  const shown = state.runs.filter((r) => GROUPS[group].test(r) && (!who || r.user === who) && (!action || (r.action || "auto") === action)
    && (!q || `${r.video} ${titles[r.video] || ""} ${r.prompt || ""} ${r.user}`.toLowerCase().includes(q)));
  const running = shown.filter((r) => r.status === "running");
  const rest = shown.filter((r) => r.status !== "running");
  const days = [];
  for (const r of rest) {
    const k = dayKey(r.started);
    if (!days.length || days[days.length - 1].key !== k) days.push({ key: k, label: dayLabel(r.started), runs: [] });
    days[days.length - 1].runs.push(r);
  }

  const canAct = (r) => admin || r.user === me;
  const stop = async (r) => {
    if (!await ask({ tone: "warn", title: "Dừng việc đang chạy?", confirmText: "Dừng lại",
      message: "Lô ảnh đã gửi lên Kaggle vẫn chạy nốt trên Kaggle. Bấm Chạy tiếp sau để lấy kết quả và làm tiếp." })) return;
    api("/api/stop", { id: r.id }).then(() => { notify("Đã dừng"); refresh(); }).catch((e) => notify(e.message, "bad"));
  };
  const resume = (r) => api("/api/resume", { video: r.video })
    .then((x) => { notify(`Chạy tiếp ${r.video}`); setLogId(x.id); refresh(); }).catch((e) => notify(e.message, "bad"));

  const row = (r) => {
    const [text, cls] = RUN_STATUS[r.status] || [r.status, ""];
    const key = r.action || "auto";
    const resumable = key === "auto" && r.video && ["failed", "interrupted", "stopped"].includes(r.status) && canAct(r)
      && !state.runs.some((x) => x.video === r.video && x.status === "running");
    return (
      <div key={r.id} className={`act-row ${r.status} ${logId === r.id ? "open" : ""}`}>
        <div className="act-main">
          <span className="act-icon" title={r.label}>{ACTION_ICON[key] || "•"}</span>
          <div className="act-body">
            <div className="act-title">
              {r.video ? <button className="link" onClick={() => openVideo(r.video)}>{titles[r.video] || r.video}</button>
                : <b>{r.label}</b>}
              <span className={`badge inline ${cls}`}>{text}</span>
            </div>
            <div className="act-meta muted small">
              <span className="chip plain"><Avatar name={r.user} size={18} /> {r.user}</span>
              {r.by && r.by !== r.user && <span>bấm bởi {r.by}</span>}
              <span>{r.label}</span>
              <span>{clock(r.started)}</span>
              <span>⏱ {duration((r.ended || now) - r.started)}</span>
              {r.video && titles[r.video] && <span className="clip act-name">{r.video}</span>}
            </div>
          </div>
          <div className="act-actions">
            {r.status === "running" && canAct(r) && <button className="danger ghost small-btn" onClick={() => stop(r)}>■ Dừng</button>}
            {resumable && <button className="ghost small-btn" onClick={() => resume(r)}>↻ Chạy tiếp</button>}
            <button className={`ghost small-btn ${logId === r.id ? "on" : ""}`} onClick={() => setLogId(logId === r.id ? null : r.id)}>
              {logId === r.id ? "Ẩn log" : "Log"}
            </button>
          </div>
        </div>
        {logId === r.id && <LogView runId={r.id} follow={r.status === "running"} />}
      </div>
    );
  };

  return (
    <div className="activity">
      <div className="stats act-stats">
        {[["running", "Đang chạy", count("running"), "warn"], ["waiting", "Chờ duyệt ảnh", count("waiting"), "warn"],
          ["failed", "Lỗi hôm nay", todayCount("failed"), "bad"], ["done", "Xong hôm nay", todayCount("done"), "ok"]].map(([g, label, n, tone]) => (
          <button key={g} className={`stat act-stat ${tone} ${group === g ? "on" : ""}`} onClick={() => pickGroup(group === g ? "all" : g)}>
            <span className="muted small">{label}</span><b>{n}</b>
          </button>
        ))}
      </div>

      <div className="panel padded act-filters">
        <div className="segmented small">
          {Object.entries(GROUPS).map(([g, x]) => (
            <button key={g} className={group === g ? "active" : ""} onClick={() => pickGroup(g)}>
              {x.label} <span className="muted">{count(g)}</span>
            </button>
          ))}
        </div>
        <div className="act-filter-row">
          <select value={who} onChange={(e) => setWho(e.target.value)}>
            <option value="">Mọi người dùng</option>
            {users.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">Mọi loại việc</option>
            {actions.map((a) => <option key={a} value={a}>{ACTION_ICON[a] || "•"} {labels[a]}</option>)}
          </select>
          <input placeholder="Tìm video, đề tài..." value={query} onChange={(e) => setQuery(e.target.value)} />
          {(who || action || query || group !== "all") && (
            <button className="ghost small-btn" onClick={() => { setWho(""); setAction(""); setQuery(""); pickGroup("all"); }}>Xóa lọc</button>
          )}
        </div>
      </div>

      {shown.length === 0 && <p className="muted act-empty">Không có lần chạy nào khớp bộ lọc.</p>}

      {running.length > 0 && (
        <section className="act-day">
          <h3 className="act-day-title live">● Đang chạy <span className="muted">({running.length})</span></h3>
          <div className="panel act-list">{running.map(row)}</div>
        </section>
      )}
      {days.map((d) => (
        <section key={d.key} className="act-day">
          <h3 className="act-day-title">{d.label} <span className="muted">({d.runs.length})</span></h3>
          <div className="panel act-list">{d.runs.map(row)}</div>
        </section>
      ))}
    </div>
  );
}
