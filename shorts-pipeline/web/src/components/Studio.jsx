import { useState } from "react";
import { api, BUILD_MODES, CONTRAST_KINDS, COUNTRIES, duration, hours, REVIEW_MODES, store, VOICE_MODES } from "../api.js";
import { Avatar, Empty, FixProgress, KaggleProgress, Stepper } from "./common.jsx";
import { canManage, deleteVideo } from "./Library.jsx";
import Icon from "./Icon.jsx";

export default function Studio({ state, me, user, admin, refresh, notify, openVideo, editUser }) {
  const [prompt, setPrompt] = useState(store.get("draft"));
  const [busy, setBusy] = useState(false);
  const conf = state.settings;
  const pick = (key) => (conf.models.includes(store.get(key)) ? store.get(key) : conf[key]);   // nhớ lựa chọn lần trước
  const [models, setModels] = useState({ script_model: pick("script_model"), review_model: pick("review_model") });
  const choose = (key) => (e) => { store.set(key, e.target.value); setModels({ ...models, [key]: e.target.value }); };
  // mặc định "Không duyệt" (khóa nhớ mới: bỏ lựa chọn cũ "Tôi tự duyệt" đã lưu trong trình duyệt)
  const [reviewMode, setReviewMode] = useState(REVIEW_MODES[store.get("review_mode_v2")] ? store.get("review_mode_v2") : "none");
  const pickMode = (m) => { store.set("review_mode_v2", m); setReviewMode(m); };
  const [voiceMode, setVoiceMode] = useState(VOICE_MODES[store.get("voice_mode")] ? store.get("voice_mode") : "narration");
  const pickVoice = (m) => { store.set("voice_mode", m); setVoiceMode(m); };
  // 3 ô cách dựng; "Tương phản" có thêm: ngẫu nhiên / Nhật Bản vs một nước (lấy số liệu thật để tân bốc Nhật)
  const remembered = (key, list, fallback) => (list[store.get(key)] ? store.get(key) : fallback);
  const [build, setBuild] = useState(remembered("build_mode", BUILD_MODES, "classic"));
  const [contrast, setContrast] = useState(remembered("contrast_kind", CONTRAST_KINDS, "random"));
  const [country, setCountry] = useState(remembered("country", COUNTRIES, "CHN"));
  const keep = (key, set) => (v) => { store.set(key, v); set(v); };
  const japanVs = build === "contrast" && contrast === "japan";
  // Nhật vs nước khác: phân tích khoảng 2 phút, ưu tiên dẫn chứng; các ô khác theo BUILD_MODES
  const style = japanVs ? "classic" : BUILD_MODES[build].style;
  const storyMode = build === "contrast" ? (japanVs ? "kaigai" : "contrast") : BUILD_MODES[build].story;

  const change = (v) => { setPrompt(v); store.set("draft", v); };     // nháp giữ lại khi tải lại trang
  const missing = user && [!user.kaggle_key && "Kaggle token", !user.ai_api_key && "AI API key"].filter(Boolean);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api("/api/generate", { prompt, ...models, review_mode: reviewMode, voice_mode: voiceMode, style, story_mode: storyMode, country, contrast_mode: build === "contrast" });
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
        <div className="choice-grid story-grid">
          <div className="choice-group">
            <Choices title="Cách dựng" modes={BUILD_MODES} value={build} onPick={keep("build_mode", setBuild)} />
            {build === "contrast" && (
              <div className="story-picker" role="radiogroup" aria-label="Kiểu tương phản">
                <span className="story-label">Tương phản</span>
                <div className="story-chips">
                  {Object.entries(CONTRAST_KINDS).map(([k, m]) => (
                    <button key={k} type="button" role="radio" aria-checked={contrast === k} title={m.hint}
                      className={`chip-btn ${contrast === k ? "on" : ""}`} onClick={() => keep("contrast_kind", setContrast)(k)}>
                      <span aria-hidden="true">{m.icon}</span> {m.label}
                    </button>
                  ))}
                  {contrast === "japan" && (
                    <label className="country-pick">so với
                      <select value={country} onChange={(e) => keep("country", setCountry)(e.target.value)}>
                        {Object.entries(COUNTRIES).map(([k, name]) => <option key={k} value={k}>{name}</option>)}
                      </select>
                    </label>
                  )}
                </div>
                <p className="story-hint">{contrast === "japan"
                  ? `日本くん đấu ${COUNTRIES[country]} từng hiệp theo chủ đề bạn nhập, Nhật thắng áp đảo. Linh vật ghép lớp nhảy, đấm; thẻ tỉ số và ảnh thật; nhạc vui cố định, nhịp nhanh, nhiều tiếng hiệu ứng; số liệu thật (World Bank) nếu liên quan.`
                  : CONTRAST_KINDS[contrast].hint}</p>
              </div>
            )}
          </div>
        </div>
        <div className="choice-grid">
          <Choices title="Kiểu kể" note="AI tự chọn giọng VOICEVOX cho từng nhân vật" modes={VOICE_MODES} value={voiceMode} onPick={pickVoice} />
          <Choices title="Duyệt ảnh" modes={REVIEW_MODES} value={reviewMode} onPick={pickMode} />
        </div>
        <details className="model-box">
          <summary>⚙ Tùy chọn model <span className="muted">· {models.script_model}{reviewMode === "ai" && ` · duyệt: ${models.review_model}`}</span></summary>
          <div className="model-row">
            <label>Viết kịch bản
              <select value={models.script_model} onChange={choose("script_model")}>
                {conf.models.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label title="Phải là model đọc được ảnh (vision); dùng khi AI duyệt hoặc nhờ AI chấm ảnh">Duyệt ảnh (vision)
              <select value={models.review_model} onChange={choose("review_model")}>
                {conf.models.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
          </div>
        </details>
        <div className="composer-foot">
          <span className="muted small summary-line">
            {BUILD_MODES[build].icon} {BUILD_MODES[build].label}{build === "contrast" && ` (${contrast === "japan" ? `Nhật vs ${COUNTRIES[country]}` : "ngẫu nhiên"})`} · {VOICE_MODES[voiceMode].icon} {VOICE_MODES[voiceMode].label} · {REVIEW_MODES[reviewMode].icon} {REVIEW_MODES[reviewMode].label}
            {" "}· video {japanVs ? "~2 phút · phân tích, ít hiệu ứng" : "~70-80 giây"} · <kbd>Ctrl</kbd>+<kbd>Enter</kbd> để tạo
          </span>
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


// Nhóm thẻ lựa chọn (chọn một): biểu tượng, tên, mô tả ngắn ngay trong thẻ
function Choices({ title, note, modes, value, onPick }) {
  return (
    <div className="choice-group" role="radiogroup" aria-label={title}>
      <div className="choice-title">{title}{note && <span className="muted small"> · {note}</span>}</div>
      <div className="choice-cards">
        {Object.entries(modes).map(([k, m]) => (
          <button key={k} type="button" role="radio" aria-checked={value === k} title={m.hint}
            className={`choice-card ${value === k ? "on" : ""}`} onClick={() => onPick(k)}>
            <span className="choice-icon">{m.icon}</span>
            <span className="choice-text"><b>{m.label}</b><small>{m.short}</small></span>
            <span className="choice-dot" />
          </button>
        ))}
      </div>
    </div>
  );
}
