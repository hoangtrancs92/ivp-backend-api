import { useState } from "react";
import { api } from "../api.js";
import { ask } from "./Confirm.jsx";

const CHOICES = [["use", "✓ Dùng"], ["redo", "↻ Vẽ lại"], ["skip", "✕ Bỏ"]];

// AI đã vẽ bản sửa: xem ảnh cũ | ảnh mới, chọn Dùng / Vẽ lại (sửa ghi chú) / Bỏ, rồi áp dụng và dựng lại video.
export default function FixReview({ video, notify, onStarted, refresh }) {
  const items = video.fix_review;
  const [choice, setChoice] = useState(() => Object.fromEntries(items.map((it) => [it.name, "use"])));
  const [notes, setNotes] = useState(() => Object.fromEntries(items.map((it) => [it.name, it.note || ""])));
  const [busy, setBusy] = useState(false);
  const pick = (kind) => items.filter((it) => choice[it.name] === kind);
  const redo = pick("redo"), use = pick("use");

  const run = async (fn) => {
    setBusy(true);
    try { await fn(); } catch (e) { notify(e.message, "bad"); } finally { setBusy(false); }
  };
  const redraw = () => run(async () => {
    const r = await api("/api/fix", { video: video.name, images: redo.map((it) => ({ name: it.name, note: notes[it.name] })) });
    notify(`AI đang vẽ lại ${redo.length} ảnh`);
    onStarted(r.id);
  });
  const applyAll = () => run(async () => {
    const ok = await ask({
      tone: use.length ? "warn" : "danger", confirmText: use.length ? "Áp dụng và dựng lại" : "Bỏ hết bản sửa",
      title: use.length ? `Dùng ${use.length} ảnh sửa và dựng lại video?` : "Bỏ hết bản sửa?",
      details: use.length
        ? [`Thay ${use.length} ảnh vào video (ảnh cũ giữ ở rejected/)`, ...(items.length > use.length ? [`Bỏ ${items.length - use.length} bản sửa còn lại`] : []),
          "Tách nền và dựng lại video (vài phút); video cũ giữ ở work/output_truoc_sua.mp4"]
        : ["Video giữ nguyên ảnh cũ, không dựng lại"],
    });
    if (!ok) return;
    const r = await api("/api/fix/apply", { video: video.name, apply: use.map((it) => it.name) });
    if (r.discarded) { notify("Đã bỏ các bản sửa"); refresh(); } else { notify(`Đang dựng lại với ${use.length} ảnh sửa`); onStarted(r.id); }
  });

  return (
    <div className="review-panel">
      <div className="review-head">
        <div>
          <h3>✨ Xem ảnh AI vừa sửa ({items.length})</h3>
          <p className="muted small">
            So ảnh cũ và ảnh mới. Ảnh ưng thì để <b>Dùng</b>; chưa ưng thì chọn <b>Vẽ lại</b>, sửa ghi chú cho rõ hơn rồi bấm
            "Vẽ lại"; muốn giữ ảnh cũ thì chọn <b>Bỏ</b>. Video chỉ đổi khi bấm "Áp dụng và dựng lại". Bấm vào ảnh để xem to.
          </p>
        </div>
      </div>
      <div className="fix-review-list">
        {items.map((it) => (
          <div key={it.name} className={`fix-review-item ${choice[it.name]}`}>
            <div className="fix-pair">
              <figure><a href={it.before} target="_blank" rel="noreferrer"><img src={it.before} alt="" /></a><figcaption>Ảnh cũ</figcaption></figure>
              <span className="fix-arrow">→</span>
              <figure><a href={it.after} target="_blank" rel="noreferrer"><img src={it.after} alt="" /></a>
                <figcaption>Ảnh mới{it.tries > 1 && ` · lần ${it.tries}`}</figcaption></figure>
            </div>
            <div className="fix-review-side">
              <b>Cảnh {it.scene} <span className="muted small">· {it.name}</span></b>
              <div className="segmented small">
                {CHOICES.map(([k, label]) => (
                  <button key={k} className={choice[it.name] === k ? "active" : ""} onClick={() => setChoice({ ...choice, [it.name]: k })}>
                    {label}
                  </button>
                ))}
              </div>
              {choice[it.name] === "redo" && (
                <textarea rows={3} value={notes[it.name]} onChange={(e) => setNotes({ ...notes, [it.name]: e.target.value })}
                  placeholder="Chưa ưng chỗ nào? Vd: vẫn còn 6 ngón tay; giữ lại lon bia trên tay phải" />
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="review-bar">
        <span className="muted small">Dùng {use.length} · Vẽ lại {redo.length} · Bỏ {items.length - use.length - redo.length}</span>
        <span className="grow" />
        {redo.length > 0 ? <>
          <button className="ghost" disabled title="Vẽ lại xong các ảnh đang chọn Vẽ lại rồi mới áp dụng">
            Áp dụng{use.length ? ` ${use.length} ảnh` : ""}
          </button>
          <button className="primary redo-btn" disabled={busy} onClick={redraw}>↻ Vẽ lại {redo.length} ảnh</button>
        </> : (
          <button className={use.length ? "primary" : "danger"} disabled={busy} onClick={applyAll}>
            {use.length ? `Áp dụng ${use.length} ảnh và dựng lại` : "Bỏ hết bản sửa"}
          </button>
        )}
      </div>
    </div>
  );
}
