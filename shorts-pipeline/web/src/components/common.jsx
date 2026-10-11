import { useEffect, useRef, useState } from "react";
import { api, hours, hue, initials, STEP_ICON } from "../api.js";

export function Logo() {
  return (
    <span className="logo">
      <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden="true">
        <path d="M1 1.5v13a1 1 0 0 0 1.5.87l11-6.5a1 1 0 0 0 0-1.74l-11-6.5A1 1 0 0 0 1 1.5Z" fill="#fff" />
      </svg>
    </span>
  );
}

export function Avatar({ name, size = 36, online }) {
  return (
    <span className="avatar" style={{ "--h": hue(name), width: size, height: size, fontSize: size * 0.38 }}>
      {initials(name)}
      {online !== undefined && <i className={`presence ${online ? "on" : ""}`} />}
    </span>
  );
}

// Giờ GPU thật lấy từ Kaggle (kaggle quota)
export function QuotaBar({ quota, compact }) {
  if (!quota || quota.used == null) {
    return <div className="quota muted">{quota?.error ? `GPU: ${quota.error.slice(0, 60)}` : "GPU: đang hỏi Kaggle..."}</div>;
  }
  const pct = Math.min(100, (quota.used / quota.total) * 100);
  const level = quota.remaining < 3 ? "bad" : quota.remaining < 8 ? "warn" : "ok";
  return (
    <div className="quota">
      <div className="quota-text">
        <span>GPU còn <b className={level}>{hours(quota.remaining)}</b></span>
        {!compact && <span className="muted">đã dùng {hours(quota.used)} / {hours(quota.total)}</span>}
      </div>
      <div className="bar"><div className={`fill ${level}`} style={{ width: `${pct}%` }} /></div>
      {!compact && quota.refresh && (
        <div className="muted small">Kaggle cấp lại lúc {new Date(quota.refresh).toLocaleString("vi-VN",
          { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" })}</div>
      )}
    </div>
  );
}

export function Stepper({ progress }) {
  if (!progress) return null;
  const steps = Object.entries(progress.steps);
  return (
    <ol className="stepper">
      {steps.map(([key, s]) => (
        <li key={key} className={s.status} title={s.note || ""}>
          <span className="node">{s.status === "running" ? <i className="spin" /> : STEP_ICON[s.status]}</span>
          <span className="label">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}

// Đang sửa cảnh bằng AI: cảnh nào, AI sửa k/n ảnh → tách nền → bố cục → dựng video
const FIX_PHASES = [["ai", "AI sửa ảnh"], ["cutouts", "Tách nền"], ["preview", "Bố cục cảnh"], ["build", "Dựng video"]];
export function FixProgress({ fix, compact }) {
  if (!fix) return null;
  const at = FIX_PHASES.findIndex(([k]) => k === fix.phase);
  const pct = fix.phase === "ai" ? (fix.total ? (fix.done / fix.total) * 40 : 0) : ((at < 0 ? 4 : at) / 4) * 100 + 10;
  return (
    <div className="fix-progress">
      <div className="fix-progress-head">
        <span className="fix-pill">✨ Đang sửa {fix.scenes.length ? `${fix.scenes.length} ` : ""}cảnh</span>
        {fix.scenes.length > 0 && <span className="muted small">cảnh {fix.scenes.join(", ")}</span>}
      </div>
      {!compact && (
        <ol className="fix-steps">
          {FIX_PHASES.map(([k, label], i) => (
            <li key={k} className={i < at || fix.phase === "done" ? "done" : i === at ? "now" : ""}>
              {label}{k === "ai" && ` ${fix.done}/${fix.total}`}
            </li>
          ))}
        </ol>
      )}
      <div className="quota-text">
        <span>{fix.phase === "ai" ? (fix.total ? `AI sửa ảnh ${fix.done}/${fix.total}` : "AI đang sửa ảnh, rồi dựng lại video")
          : FIX_PHASES[at]?.[1] || "Xong"}</span>
        <span className="muted">{fix.current}</span>
      </div>
      <div className="bar big"><div className="fill accent" style={{ width: `${Math.min(pct, 100)}%` }} /></div>
    </div>
  );
}

export function KaggleProgress({ progress }) {
  const k = progress?.kaggle;
  if (!k) return null;
  const pct = k.total ? (k.done / k.total) * 100 : 0;
  return (
    <div className="kaggle-progress">
      <div className="quota-text">
        <span>{k.loading ? "Kaggle đang nạp model..." : `Ảnh: ${k.done}/${k.total}`}
          {k.failed > 0 && <b className="bad"> · {k.failed} lỗi</b>}</span>
        <span className="muted">{k.current?.length ? `đang vẽ ${k.current.join(", ")}` : ""}</span>
      </div>
      <div className="bar big"><div className="fill accent" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export function LogView({ runId, follow }) {
  const [text, setText] = useState("");
  const pre = useRef(null);
  useEffect(() => {
    if (!runId) return undefined;
    const load = () => api(`/api/log?id=${runId}`).then((r) => {
      const el = pre.current;
      const atEnd = !el || el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
      setText(r.text);
      if (atEnd) requestAnimationFrame(() => { if (pre.current) pre.current.scrollTop = pre.current.scrollHeight; });
    }).catch((e) => setText(e.message));
    load();
    if (!follow) return undefined;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [runId, follow]);
  return <pre className="log" ref={pre}>{text || "..."}</pre>;
}

// Log của kernel Kaggle (tài khoản chủ video): đọc luồng log trực tiếp khi kernel đang chạy, 30 giây làm mới một lần
export function KaggleLog({ video, follow }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const pre = useRef(null);
  const load = () => {
    setBusy(true);
    api(`/api/kaggle_log?video=${encodeURIComponent(video)}`).then((r) => {
      setData(r); setError("");
      requestAnimationFrame(() => { if (pre.current) pre.current.scrollTop = pre.current.scrollHeight; });
    }).catch((e) => setError(e.message)).finally(() => setBusy(false));
  };
  useEffect(() => {
    load();
    if (!follow) return undefined;
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [video, follow]);
  // thanh tiến trình tqdm ghi đè bằng \r: chỉ giữ trạng thái cuối của mỗi dòng
  const text = (data?.text || "").split("\n").map((l) => l.split("\r").filter(Boolean).pop() || "").join("\n");
  const done = (text.match(/GPU \d+ xong: /g) || []).length;
  return (
    <div>
      <div className="kaggle-log-head">
        {data && <>
          <span className="chip plain small">{data.kernel}</span>
          <span className={`small ${data.status === "running" ? "warn" : data.status === "complete" ? "ok" : "muted"}`}>● {data.status}</span>
          {done > 0 && <span className="small">{done} ảnh đã xong</span>}
          {data.video && data.video !== video && <span className="small bad">Kernel này đang / vừa chạy cho video {data.video}</span>}
          <span className="muted small">cập nhật {new Date(data.checked * 1000).toLocaleTimeString("vi-VN")}</span>
        </>}
        <span className="grow" />
        <button className="ghost small-btn" onClick={load} disabled={busy}>{busy ? "Đang lấy..." : "↻ Làm mới"}</button>
      </div>
      {error ? <p className="note bad">{error}</p>
        : <pre className="log" ref={pre}>{data ? text.trim() || "(Kernel chưa in dòng nào: đang khởi động máy hoặc chờ máy GPU)" : "Đang hỏi Kaggle... (~15 giây)"}</pre>}
    </div>
  );
}

export function Empty({ icon, title, children }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

export function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    const esc = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${wide ? "wide" : ""}`} role="dialog" aria-modal="true">
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Đóng">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

// Ô đánh dấu đã đăng TikTok (video truyện kể: kind "video", tiểu phẩm: "skit"). Lưu ở meta.json, mọi người thấy như nhau.
export function PostedToggle({ kind, name, posted, manage, notify, refresh }) {
  const [busy, setBusy] = useState(false);
  const [on, setOn] = useState(Boolean(posted));
  useEffect(() => setOn(Boolean(posted)), [posted]);
  const toggle = async (e) => {
    e.stopPropagation();
    if (!manage || busy) return;
    setBusy(true);
    setOn(!on);
    try {
      await api("/api/posted", { kind, name, posted: !on });
      refresh?.();
    } catch (err) {
      setOn(on);
      notify?.(err.message, "bad");
    } finally {
      setBusy(false);
    }
  };
  const when = posted?.at ? new Date(posted.at * 1000).toLocaleDateString("vi-VN") : "";
  return (
    <button type="button" role="checkbox" aria-checked={on} disabled={!manage}
      className={`posted-toggle ${on ? "on" : ""}`} onClick={toggle}
      title={on ? `Đã đăng TikTok${posted?.by ? ` (${posted.by}${when ? `, ${when}` : ""})` : ""}` : manage ? "Bấm khi đã đăng lên TikTok" : "Chưa đăng TikTok"}>
      <span className="posted-box">{on ? "✓" : ""}</span>{on ? "Đã đăng" : "Chưa đăng"}
    </button>
  );
}
