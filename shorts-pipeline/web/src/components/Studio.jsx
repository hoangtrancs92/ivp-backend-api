import { useState } from "react";
import { api, duration, hours, REVIEW_MODES, store } from "../api.js";
import { Avatar, Empty, FixProgress, KaggleProgress, Stepper } from "./common.jsx";
import { canManage, deleteVideo } from "./Library.jsx";
import Icon from "./Icon.jsx";

const IDEAS = [
  "Bố lén ướp lạnh hai cốc bia mỗi tối, chờ con trai đi làm về",
  "Mẹ làm cơm hộp mỗi sáng suốt 6 năm, đến ngày tốt nghiệp con mới biết lý do",
  "Chiếc ví cũ của bố và tấm ảnh bên trong",
];

export default function Studio({ state, me, user, admin, refresh, notify, openVideo, editUser }) {
  const [prompt, setPrompt] = useState(store.get("draft"));
  const [busy, setBusy] = useState(false);
  const conf = state.settings;
  const pick = (key) => (conf.models.includes(store.get(key)) ? store.get(key) : conf[key]);   // nhớ lựa chọn lần trước
  const [models, setModels] = useState({ script_model: pick("script_model"), review_model: pick("review_model") });
  const choose = (key) => (e) => { store.set(key, e.target.value); setModels({ ...models, [key]: e.target.value }); };
  const [reviewMode, setReviewMode] = useState(REVIEW_MODES[store.get("review_mode")] ? store.get("review_mode") : "manual");
  const pickMode = (m) => { store.set("review_mode", m); setReviewMode(m); };

  const change = (v) => { setPrompt(v); store.set("draft", v); };     // nháp giữ lại khi tải lại trang
  const missing = user && [!user.kaggle_key && "Kaggle token", !user.ai_api_key && "AI API key"].filter(Boolean);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api("/api/generate", { prompt, ...models, review_mode: reviewMode });
      change("");
      notify(`Đã bắt đầu tạo ${r.video}`);
      refresh();
    } catch (e) {
      notify(e.message, "bad");
    } finally {
      setBusy(false);
    }
  };

  const active = state.videos.filter((v) => v.run?.status === "running");
  const waiting = state.videos.filter((v) => v.review && canManage(v, me, admin));
  const stuck = state.videos.filter((v) => v.progress && !v.output && !v.review && v.run && v.run.status !== "running"
    && canManage(v, me, admin)).slice(0, 6);

  return (
    <>
      <section className="composer">
        <div className="composer-head">
          <h2>Hôm nay kể chuyện gì?</h2>
          {user && <span className="chip"><Avatar name={user.name} size={20} /> {user.name}{user.quota?.remaining != null && ` · GPU còn ${hours(user.quota.remaining)}`}</span>}
        </div>
        <textarea value={prompt} onChange={(e) => change(e.target.value)} rows={5}
          placeholder="Nhập đề tài ngắn, hoặc dán cả câu chuyện. AI viết kịch bản tiếng Nhật, Kaggle vẽ ảnh, bạn duyệt ảnh, máy chủ dựng video."
          onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && prompt.trim()) submit(); }} />
        <div className="model-row">
          <label>Model viết kịch bản
            <select value={models.script_model} onChange={choose("script_model")}>
              {conf.models.map((m) => <option key={m}>{m}</option>)}
            </select>
          </label>
          <label title="Phải là model đọc được ảnh (vision)">Model duyệt ảnh (vision)
            <select value={models.review_model} onChange={choose("review_model")}>
              {conf.models.map((m) => <option key={m}>{m}</option>)}
            </select>
          </label>
        </div>
        <div className="mode-row">
          <span className="mode-label">Duyệt ảnh</span>
          <div className="mode-options" role="radiogroup" aria-label="Chế độ duyệt ảnh">
            {Object.entries(REVIEW_MODES).map(([k, m]) => (
              <button key={k} type="button" role="radio" aria-checked={reviewMode === k}
                className={`mode-option ${reviewMode === k ? "on" : ""}`} onClick={() => pickMode(k)}>
                <span className="mode-icon">{m.icon}</span>{m.label}
              </button>
            ))}
          </div>
          <p className="mode-hint">{REVIEW_MODES[reviewMode].hint}</p>
        </div>
        <div className="composer-foot">
          <div className="ideas">
            {IDEAS.map((idea) => <button key={idea} className="idea" onClick={() => change(idea)}>{idea}</button>)}
          </div>
          <button className="primary big" disabled={busy || !prompt.trim() || !user || missing?.length > 0} onClick={submit}>
            {busy ? "Đang gửi..." : "✦ Tạo video"}
          </button>
        </div>
        {!user && <p className="note">Tạo hồ sơ của bạn trước (góc trái dưới).</p>}
        {missing?.length > 0 && (
          <p className="note warn">Hồ sơ còn thiếu {missing.join(", ")}.{" "}
            <button className="link" onClick={() => editUser(me)}>Bổ sung ngay</button></p>
        )}
      </section>

      {waiting.length > 0 && (
        <>
          <h2 className="section-title">Chờ bạn duyệt ảnh <span className="muted">({waiting.length})</span></h2>
          <div className="job-list">
            {waiting.map((v) => (
              <article key={v.name} className="job waiting-card" onClick={() => openVideo(v.name)}>
                <div className="waiting-thumbs">
                  {v.review.slice(0, 6).map((it) => <img key={it.key} src={it.url} alt="" loading="lazy" />)}
                </div>
                <div className="waiting-text">
                  <h3>{v.title || v.name}</h3>
                  <p className="muted small">Kaggle đã vẽ xong {v.review.length} ảnh. Xem và duyệt để dựng video.</p>
                </div>
                <button className="primary" onClick={(e) => { e.stopPropagation(); openVideo(v.name); }}>👀 Duyệt ảnh</button>
              </article>
            ))}
          </div>
        </>
      )}

      <h2 className="section-title">Đang chạy <span className="muted">({active.length})</span></h2>
      {active.length === 0
        ? <Empty icon="☕" title="Chưa có video nào đang chạy">Video mới sẽ hiện ở đây cùng tiến trình từng bước.</Empty>
        : <div className="job-list">{active.map((v) => <JobCard key={v.name} video={v} onOpen={() => openVideo(v.name)} />)}</div>}

      {stuck.length > 0 && (
        <>
          <h2 className="section-title">Chưa xong / lỗi <span className="muted">· bấm để chạy tiếp, hoặc xóa cho nhẹ máy</span></h2>
          <div className="job-list">
            {stuck.map((v) => (
              <JobCard key={v.name} video={v} onOpen={() => openVideo(v.name)}
                onDelete={canManage(v, me, admin) ? () => deleteVideo(v, notify, refresh) : null} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

export function JobCard({ video, onOpen, onDelete }) {
  const run = video.run;
  const now = Date.now() / 1000;
  const elapsed = run ? (run.ended || now) - run.started : 0;
  return (
    <article className="job" onClick={onOpen}>
      <div className="job-head">
        <div>
          <h3>{video.title || video.name}</h3>
          <p className="prompt-line">{video.fix ? "Sửa cảnh lỗi bằng AI rồi dựng lại video" : video.prompt || "(không có đề tài)"}</p>
        </div>
        <div className="job-meta">
          {run && <span className="chip"><Avatar name={run.user} size={18} /> {run.user}</span>}
          <span className="muted small">{duration(elapsed)}</span>
          {video.progress?.gpu_hours > 0 && <span className="muted small">GPU {hours(video.progress.gpu_hours)}</span>}
          {onDelete && (
            <button className="danger ghost small-btn" onClick={(e) => { e.stopPropagation(); onDelete(); }}><Icon name="trash" size={14} /> Xóa</button>
          )}
        </div>
      </div>
      {video.fix ? <FixProgress fix={video.fix} /> : <>
        <Stepper progress={video.progress} />
        <KaggleProgress progress={video.progress} />
      </>}
      {video.progress?.error && <p className="note bad">{video.progress.error}</p>}
    </article>
  );
}
