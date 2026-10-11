// Trang "Tiểu phẩm": chức năng riêng (skit/), tách khỏi video truyện kể. Nhập ý tưởng -> AI viết tiểu phẩm -> đạo diễn dựng
// -> VOICEVOX -> tìm tiếng -> Kaggle vẽ nhân vật, biểu cảm, nền, tranh chèn -> dựng video kiểu sân khấu.
import { useState } from "react";
import { ago, api, duration, hours, store } from "../api.js";
import { Avatar, LogView, Modal, PostedToggle, Stepper } from "./common.jsx";
import { ask } from "./Confirm.jsx";
import Icon from "./Icon.jsx";

const IDEAS = [
  ["🏢", "Nhân viên mới thú nhận lỗi ngày càng nặng, 4 tiền bối thi nhau kể lỗi còn tệ hơn"],
  ["🎯", "Sniper tự tin tuyệt đối nhưng lần nào cũng sai một việc cơ bản, chỉ huy qua điện thoại ngày càng hoảng"],
  ["🍺", "Vợ biến buổi đi nhậu của chồng thành một buổi kiểm tra nhiệm vụ nghiêm trọng"],
  ["🍜", "Khách gọi món liên tục rồi đổi món, bồi bàn ngày càng hoảng loạn"],
];
const FORMATS = { loop: "Vòng lặp", list: "Danh sách", incident: "Biến cố", story: "Chuyện có twist",
  misunderstanding: "Hiểu lầm", interview: "Hỏi đáp", reaction: "Phản ứng dây chuyền", free: "Tự do" };
// Khuôn chọn khi tạo: "" = AI tự chọn theo ý tưởng
const FORMAT_CHOICES = [
  ["", "✨", "AI tự chọn", "Chọn khuôn hợp ý tưởng nhất"],
  ["story", "📖", "Chuyện có twist", "Rắc rối lớn dần, lộ sự thật, cú chốt"],
  ["loop", "🔁", "Vòng lặp", "Một việc lặp lại, lần sau lố hơn"],
  ["list", "📋", "Danh sách", "Các mục tăng dần, có nhãn từng mục"],
  ["misunderstanding", "🙃", "Hiểu lầm", "Hai bên nói hai chuyện khác nhau"],
  ["interview", "🎤", "Hỏi đáp", "Hỏi nghiêm túc, trả lời vô lý"],
  ["reaction", "💥", "Phản ứng dây chuyền", "Mỗi người phản ứng một kiểu, quá đà dần"],
  ["incident", "⚡", "Biến cố", "Một sự cố ngắn, nhân vật ra vào, đảo ngược"],
  ["free", "🧪", "Tự do", "Đề tài lạ: AI tự thiết kế cấu trúc riêng"],
];
const GRADES = { noir: "Noir", retro: "Retro", warm: "Ấm", cool: "Lạnh", night: "Đêm" };
const SKIT_MODEL = "claude-sonnet-5-5";
const FLOW = ["Viết", "Đạo diễn", "Giọng", "Tiếng", "Kaggle vẽ", "Dựng"];

export default function Skits({ state, me, user, admin, refresh, notify, editUser }) {
  const [prompt, setPrompt] = useState(store.get("skit_draft"));
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(null);
  const [filter, setFilter] = useState("all");
  const conf = state.settings;
  // model viết tiểu phẩm: nhớ riêng (không chung với Tạo video), mặc định Sonnet cho rẻ
  const [model, setModel] = useState(conf.models.includes(store.get("skit_model")) ? store.get("skit_model")
    : conf.models.includes(SKIT_MODEL) ? SKIT_MODEL : conf.script_model);
  const change = (v) => { setPrompt(v); store.set("skit_draft", v); };
  const [format, setFormat] = useState(store.get("skit_format"));
  const pickFormat = (f) => { setFormat(f); store.set("skit_format", f); };
  const missing = user && [!user.kaggle_key && "Kaggle token", !user.ai_api_key && "AI API key"].filter(Boolean);
  const skits = state.skits || [];
  const mine = (s) => admin || s.owner === me;
  const status = (s) => s.run?.status === "running" ? "running" : s.output ? "done" : s.progress?.error ? "failed" : "idle";
  const counts = { all: skits.length, running: 0, done: 0, failed: 0 };
  skits.forEach((s) => { const k = status(s); if (k in counts) counts[k] += 1; });
  const shown = skits.filter((s) => filter === "all" || status(s) === filter);

  const submit = async () => {
    setBusy(true);
    try {
      const r = await api("/api/skit/generate", { prompt, script_model: model, format });
      change("");
      notify(`Đã bắt đầu tạo ${r.video}`);
      refresh();
    } catch (e) {
      notify(e.message, "bad");
    } finally {
      setBusy(false);
    }
  };
  const resume = (s) => resumeSkit(s, notify, refresh);
  const remove = async (s) => { if (await deleteSkit(s, notify, refresh)) setOpen(null); };
  const current = skits.find((s) => s.name === open);

  return (
    <div className="skits">
      <section className="sk-composer">
        <div className="sk-composer-main">
          <div className="sk-composer-head">
            <span className="sk-badge">🎭 Tiểu phẩm hài</span>
            {user && <span className="sk-user"><Avatar name={user.name} size={20} /> {user.name}
              {user.quota?.remaining != null && <span className="muted"> · GPU còn {hours(user.quota.remaining)}</span>}</span>}
          </div>
          <h2>Kể một tình huống, AI dựng thành tiểu phẩm</h2>
          <textarea value={prompt} onChange={(e) => change(e.target.value)} rows={3}
            placeholder="Ai, ở đâu, có tật hay logic buồn cười gì? AI tự thêm leo thang, cảnh chèn, kỹ xảo, tiếng và cú chốt."
            onKeyDown={(e) => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && prompt.trim()) submit(); }} />
          <div className="sk-ideas">
            {IDEAS.map(([icon, idea]) => (
              <button key={idea} type="button" className={prompt === idea ? "on" : ""} onClick={() => change(idea)}>
                <span>{icon}</span>{idea}
              </button>
            ))}
          </div>
          <div className="sk-formats" role="radiogroup" aria-label="Khuôn tiểu phẩm">
            <span className="sk-label">Khuôn</span>
            {FORMAT_CHOICES.map(([k, icon, label, hint]) => (
              <button key={k || "auto"} type="button" role="radio" aria-checked={format === k} title={hint}
                className={format === k ? "on" : ""} onClick={() => pickFormat(k)}>
                <span>{icon}</span>{label}
              </button>
            ))}
          </div>
          <div className="sk-foot">
            <label className="sk-model">Model viết
              <select value={model} onChange={(e) => { setModel(e.target.value); store.set("skit_model", e.target.value); }}>
                {conf.models.map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <span className="muted small"><kbd>Ctrl</kbd>+<kbd>Enter</kbd></span>
            <span className="grow" />
            <button className="primary big" disabled={busy || !prompt.trim() || !user || missing?.length > 0} onClick={submit}>
              {busy ? "Đang gửi..." : "Tạo tiểu phẩm"}
            </button>
          </div>
          {missing?.length > 0 && (
            <p className="note warn">Hồ sơ còn thiếu {missing.join(", ")}.{" "}
              <button className="link" onClick={() => editUser(me)}>Bổ sung ngay</button></p>
          )}
        </div>
        <ol className="sk-flow">
          {FLOW.map((step, i) => <li key={step}><b>{i + 1}</b>{step}</li>)}
          <li className="sk-flow-note">≥ 60 giây · dọc 9:16 · VOICEVOX</li>
        </ol>
      </section>

      <div className="sk-toolbar">
        <h2>Tiểu phẩm</h2>
        <div className="sk-tabs" role="tablist">
          {[["all", "Tất cả"], ["running", "Đang chạy"], ["done", "Xong"], ["failed", "Lỗi"]].map(([k, label]) => (
            <button key={k} role="tab" aria-selected={filter === k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>
              {label}<span>{counts[k]}</span>
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0
        ? <div className="sk-empty"><div>🎬</div><b>{skits.length ? "Không có tiểu phẩm nào ở mục này" : "Chưa có tiểu phẩm nào"}</b>
          <span className="muted">{skits.length ? "Chọn mục khác ở trên." : "Nhập ý tưởng hoặc bấm một gợi ý ở trên để bắt đầu."}</span></div>
        : <div className="sk-grid">{shown.map((s) => (
          <SkitCard key={s.name} skit={s} state={status(s)} onOpen={() => setOpen(s.name)} manage={mine(s)} notify={notify} refresh={refresh}
            onResume={mine(s) && !s.output && s.run?.status !== "running" ? () => resume(s) : null}
            onDelete={mine(s) ? () => remove(s) : null} />
        ))}</div>}

      {current && <SkitModal skit={current} manage={mine(current)} notify={notify} refresh={refresh} onClose={() => setOpen(null)} />}
    </div>
  );
}

export async function resumeSkit(s, notify, refresh) {
  try {
    await api("/api/skit/resume", { skit: s.name });
    notify(`Chạy tiếp ${s.name}`);
    refresh();
  } catch (e) { notify(e.message, "bad"); }
}

// Xóa cả thư mục tiểu phẩm. Trả về true nếu đã xóa.
export async function deleteSkit(s, notify, refresh) {
  const ok = await ask({
    tone: "danger", title: "Xóa tiểu phẩm này?", confirmText: "Xóa vĩnh viễn",
    subject: <><b>{s.title || s.name}</b><span>{s.name}</span></>,
    details: ["Xóa kịch bản, giọng đọc, ảnh nhân vật và output.mp4", ...(s.run?.status === "running" ? ["Đang chạy sẽ được dừng trước"] : []),
      "Không khôi phục được"],
  });
  if (!ok) return false;
  try {
    await api("/api/skit/delete", { skit: s.name });
    notify(`Đã xóa ${s.name}`);
    refresh();
    return true;
  } catch (e) {
    notify(e.message, "bad");
    return false;
  }
}

// Cửa sổ chi tiết tiểu phẩm (trang Tiểu phẩm và Thư viện)
export function SkitModal({ skit, manage, notify, refresh, onClose }) {
  return (
    <Modal title={skit.title || "Tiểu phẩm mới"} onClose={onClose} wide>
      <SkitDetail skit={skit} manage={manage} notify={notify} refresh={refresh} onResume={manage && !skit.output && skit.run?.status !== "running" ? () => resumeSkit(skit, notify, refresh) : null}
        onDelete={manage ? async () => { if (await deleteSkit(skit, notify, refresh)) onClose(); } : null} />
    </Modal>
  );
}

export function skitThumb(s) {
  return s.poster ? `/skits/${s.name}/${s.poster}?v=${Math.round(s.updated)}` : s.faces?.[0] ? `/skits/${s.name}/${s.faces[0]}` : null;
}

function Poster({ skit }) {
  if (skit.poster) return <img className="sk-poster-img" src={`/skits/${skit.name}/${skit.poster}?v=${Math.round(skit.updated)}`} alt="" loading="lazy" />;
  if (skit.faces?.length) {
    return <div className="sk-cast">{skit.faces.map((f) => <img key={f} src={`/skits/${skit.name}/${f}`} alt="" loading="lazy" />)}</div>;
  }
  if (skit.run?.status === "running") {                 // chưa có ảnh: hiện bước đang làm
    return (
      <div className="sk-poster-live">
        <span className="spin" />
        <b>{skit.step?.label || "Đang khởi động"}</b>
        <small>bước {Math.min(skit.steps_done + 1, skit.steps_total || 1)}/{skit.steps_total || "?"}</small>
      </div>
    );
  }
  return <div className="sk-poster-blank">🎭</div>;
}

function SkitCard({ skit, state, onOpen, onResume, onDelete, manage, notify, refresh }) {
  const run = skit.run;
  const elapsed = run ? (run.ended || Date.now() / 1000) - run.started : 0;
  const pct = skit.steps_total ? Math.round((skit.steps_done / skit.steps_total) * 100) : 0;
  return (
    <article className={`sk-card ${state}`} onClick={onOpen}>
      <div className="sk-poster">
        <Poster skit={skit} />
        <span className={`sk-status ${state}`}>
          {state === "running" ? <><i className="spin" /> Đang chạy</> : state === "done" ? "Xong" : state === "failed" ? "Lỗi" : "Chưa xong"}
        </span>
        {skit.seconds && <span className="sk-duration">{Math.round(skit.seconds)}s</span>}
        {skit.output && <span className="sk-play"><svg viewBox="0 0 24 24" width="26" height="26"><path d="M8 5v14l11-7z" fill="currentColor" /></svg></span>}
        {(onResume || onDelete) && (
          <div className="sk-actions" onClick={(e) => e.stopPropagation()}>
            {onResume && <button title="Chạy tiếp" aria-label="Chạy tiếp" onClick={onResume}>▶</button>}
            {onDelete && <button title="Xóa" aria-label="Xóa" className="del" onClick={onDelete}><Icon name="trash" size={15} /></button>}
          </div>
        )}
      </div>
      <div className="sk-body">
        <h3>{skit.title || "(đang viết...)"}</h3>
        <p className="sk-idea">{skit.prompt}</p>
        {state === "running" || state === "failed" ? (
          <div className="sk-progress">
            <div className="sk-progress-text">
              <span className={state === "failed" ? "bad" : ""}>{skit.step?.label || "Đang khởi động"}</span>
              <span className="muted">{state === "running" ? duration(elapsed) : `${skit.steps_done}/${skit.steps_total}`}</span>
            </div>
            <div className="bar"><div className={`fill ${state === "failed" ? "bad" : "accent"}`} style={{ width: `${Math.max(pct, 4)}%` }} /></div>
            {skit.progress?.kaggle && state === "running" && <span className="muted small">Kaggle: {skit.progress.kaggle.done}/{skit.progress.kaggle.total} ảnh</span>}
          </div>
        ) : (
          <div className="sk-tags">
            {skit.format && <span>{FORMATS[skit.format] || skit.format}</span>}
            {skit.lines > 0 && <span>{skit.lines} câu</span>}
            {skit.cast > 0 && <span>{skit.cast} vai</span>}
            {skit.inserts > 0 && <span>{skit.inserts} cảnh chèn</span>}
            {GRADES[skit.grade] && <span>{GRADES[skit.grade]}</span>}
          </div>
        )}
        <div className="sk-meta">
          {skit.owner && <><Avatar name={skit.owner} size={18} /><span>{skit.owner}</span></>}
          <span className="grow" />
          {skit.output ? <PostedToggle kind="skit" name={skit.name} posted={skit.posted} manage={manage} notify={notify} refresh={refresh} />
            : <span className="muted">{ago(skit.updated)}</span>}
        </div>
      </div>
    </article>
  );
}

function LiveSteps({ skit }) {
  // Bảng tiến trình trực tiếp (khi chưa có video): từng bước, bước đang chạy, ảnh Kaggle
  const steps = Object.entries(skit.progress?.steps || {});
  const running = skit.run?.status === "running";
  const elapsed = skit.run ? (skit.run.ended || Date.now() / 1000) - skit.run.started : 0;
  const k = skit.progress?.kaggle;
  return (
    <div className="sk-live">
      <div className="sk-live-head">
        <span className={`sk-live-icon ${running ? "on" : ""}`}>{running ? <i className="spin" /> : skit.progress?.error ? "!" : "🎭"}</span>
        <div>
          <b>{running ? (skit.step?.label || "Đang khởi động") : skit.progress?.error ? "Đã dừng vì lỗi" : "Chưa chạy xong"}</b>
          <span>{running ? `đã chạy ${duration(elapsed)}` : skit.run ? `lần chạy cuối ${ago(skit.run.started)}` : "chưa chạy"}</span>
        </div>
      </div>
      <ol className="sk-live-steps">
        {steps.length === 0 && <li className="pending"><i />Đang chuẩn bị...</li>}
        {steps.map(([key, st]) => (
          <li key={key} className={st.status}>
            <i>{st.status === "running" ? <span className="spin" /> : st.status === "failed" ? "!" : ["done", "skipped"].includes(st.status) ? "✓" : ""}</i>
            <div><b>{st.label}</b>{st.note && <span>{st.note}</span>}</div>
          </li>
        ))}
      </ol>
      {k && running && (
        <div className="sk-live-kaggle">
          <div className="sk-progress-text"><span>{k.loading ? "Kaggle đang nạp model" : `Kaggle vẽ ${k.done}/${k.total} ảnh`}</span>
            {k.failed > 0 && <span className="bad">{k.failed} lỗi</span>}</div>
          <div className="bar"><div className="fill accent" style={{ width: `${k.total ? (k.done / k.total) * 100 : 3}%` }} /></div>
        </div>
      )}
    </div>
  );
}

function SkitDetail({ skit, onResume, onDelete, manage, notify, refresh }) {
  const running = skit.run?.status === "running";
  const [tab, setTab] = useState(skit.output ? "info" : "log");
  const [more, setMore] = useState(false);
  const long = (skit.prompt || "").length > 160;
  const facts = [
    skit.format && ["Khuôn", `${FORMATS[skit.format] || skit.format}${GRADES[skit.grade] ? ` · tông ${GRADES[skit.grade]}` : ""}`],
    skit.lines > 0 && ["Nội dung", `${skit.lines} câu · ${skit.cast} vai · ${skit.inserts} cảnh chèn${skit.seconds ? ` · ${Math.round(skit.seconds)} giây` : ""}`],
    ["Model", `${skit.script_model || "—"}${skit.directed ? " · đã qua đạo diễn" : ""}`],
    skit.owner && ["Người tạo", skit.owner],
    skit.credits && ["Ghi khi đăng", <code key="c">{skit.credits.split("\n").join(", ")}</code>],
  ].filter(Boolean);
  return (
    <div className="sk-detail">
      <div className="sk-detail-media">
        {skit.output
          ? <video src={`/skits/${skit.name}/output.mp4?v=${Math.round(skit.updated)}`} poster={skit.poster ? `/skits/${skit.name}/${skit.poster}` : undefined}
            controls playsInline />
          : <LiveSteps skit={skit} />}
      </div>
      <div className="sk-detail-side">
        <div className="sk-detail-top">
          <span className={`sk-pill ${running ? "running" : skit.output ? "done" : skit.progress?.error ? "failed" : ""}`}>
            {running ? "Đang chạy" : skit.output ? "Xong" : skit.progress?.error ? "Lỗi" : "Chưa xong"}</span>
          <code className="sk-slug">{skit.name}</code>
          <span className="grow" />
          {skit.output && <PostedToggle kind="skit" name={skit.name} posted={skit.posted} manage={manage} notify={notify} refresh={refresh} />}
          {skit.output && <a className="primary" href={`/skits/${skit.name}/output.mp4?download=1`}><Icon name="download" size={15} /> Tải video</a>}
          {onResume && <button className="primary" onClick={onResume}>▶ Chạy tiếp</button>}
          {onDelete && <button className="danger ghost" onClick={onDelete}><Icon name="trash" size={14} /> Xóa</button>}
        </div>
        {skit.prompt && (
          <div className="sk-prompt">
            <span className="sk-label">Ý tưởng</span>
            <p className={long && !more ? "clamp" : ""}>{skit.prompt}</p>
            {long && <button className="link" onClick={() => setMore(!more)}>{more ? "Thu gọn" : "Xem đầy đủ"}</button>}
          </div>
        )}
        {skit.structure?.length > 0 && (
          <div className="sk-prompt">
            <span className="sk-label">Cấu trúc AI tự thiết kế</span>
            <ol className="sk-beats">{skit.structure.map((b, i) => <li key={i}>{b}</li>)}</ol>
          </div>
        )}
        <dl className="sk-facts">
          {facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
        {skit.faces?.length > 0 && <div className="sk-detail-cast">{skit.faces.map((f) => <img key={f} src={`/skits/${skit.name}/${f}`} alt="" />)}</div>}
        {skit.progress?.error && !running && <p className="note bad">{skit.progress.error}</p>}
        {skit.run && <>
          <div className="sk-tabs small-tabs">
            {skit.output && <button className={tab === "info" ? "on" : ""} onClick={() => setTab("info")}>Tiến trình</button>}
            <button className={tab === "log" || !skit.output ? "on" : ""} onClick={() => setTab("log")}>Nhật ký</button>
          </div>
          {tab === "info" && skit.output ? <Stepper progress={skit.progress} /> : <LogView runId={skit.run.id} follow={running} />}
        </>}
      </div>
    </div>
  );
}
