import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ask } from "./Confirm.jsx";

const KINDS = { all: "Tất cả", character: "Nhân vật, đồ vật", background: "Ảnh nền", photo: "Ảnh thật" };

// Tên tiêu chí AI chấm (config/review_guide.md) để hiện khi rê chuột vào huy hiệu "AI x/5"
const CRITERIA = {
  character: "đúng nhân vật", outfit: "trang phục", body: "cơ thể", objects: "đồ vật", extras: "thứ thừa", action: "hành động",
  object: "đồ vật", count: "số lượng", style: "nét vẽ", shape: "hình dạng", place: "nơi chốn", empty: "không người / chữ", mood: "thời gian, không khí",
};
const aiDetail = (ai) => [
  ai.failed?.length ? `Trượt vì: ${ai.failed.map((k) => CRITERIA[k] || k).join(", ")}` : "",
  Object.entries(ai.checks || {}).map(([k, v]) => `${CRITERIA[k] || k}: ${v}/5`).join(" · "),
  ...(ai.problems || []),
].filter(Boolean).join("\n") || "Không có lỗi";

// Duyệt ảnh bằng mắt sau khi Kaggle vẽ xong: xem, chọn ảnh nghi ngờ, rồi làm tiếp / nhờ AI chấm / vẽ lại
export default function ReviewPanel({ video, notify, refresh, canAct }) {
  const items = video.review || [];
  const [selected, setSelected] = useState(() => new Set());
  const [kind, setKind] = useState("all");
  const [zoom, setZoom] = useState(null);       // chỉ số ảnh đang phóng to trong danh sách đang lọc
  const [busy, setBusy] = useState(false);
  const [notes, setNotes] = useState({});        // ghi chú khi vẽ lại, theo khóa ảnh
  const noteOf = (it) => notes[it.key] ?? it.note ?? "";
  const shown = items.filter((it) => kind === "all" || it.kind === kind);
  const n = selected.size;

  const toggle = (key) => setSelected((s) => {
    const next = new Set(s);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });

  const send = async (action) => {
    const keys = [...selected];
    const texts = {
      approve: n
        ? { title: "Bỏ qua các ảnh đã chọn và làm tiếp?", confirmText: "Ảnh ổn, làm tiếp",
          message: `Bạn đang chọn ${n} ảnh nhưng bấm duyệt: các ảnh này giữ nguyên và video được dựng luôn.` }
        : null,
      ai_all: { title: "Để AI duyệt hết rồi làm tiếp?", confirmText: "Để AI duyệt", tone: "info",
        message: "AI chấm mọi ảnh (đạt từ 3/5), tự vẽ lại ảnh hỏng tối đa 3 lượt rồi dựng video luôn, bạn không cần quay lại duyệt. Tốn thêm tiền API và giờ GPU." },
      ai: { title: `Nhờ AI chấm ${n} ảnh?`, confirmText: "AI kiểm tra", tone: "info",
        message: "AI chấm từng ảnh đã chọn. Ảnh dưới 3/5 điểm được Kaggle vẽ lại bằng seed khác (tốn giờ GPU), ảnh đạt giữ nguyên. Xong sẽ quay lại màn hình này." },
      regen: { title: `Vẽ lại ${n} ảnh?`, confirmText: "Vẽ lại", tone: "warn",
        message: "Các ảnh đã chọn bị bỏ và Kaggle vẽ lại bằng seed khác (tốn giờ GPU). Ảnh tư thế thứ hai đi kèm cũng được vẽ lại. Xong sẽ quay lại màn hình này." },
    }[action];
    if (texts && !(await ask(texts))) return;
    setBusy(true);
    try {
      const sent = Object.fromEntries(keys.map((k) => [k, notes[k]]).filter(([, v]) => v && v.trim()));
      await api("/api/review", { video: video.name, action, keys, notes: sent });
      setNotes({});
      notify({ approve: "Đã duyệt, đang dựng video", ai: "AI đang chấm ảnh đã chọn", regen: "Đang gửi Kaggle vẽ lại",
        ai_all: "AI đang duyệt hết ảnh, xong sẽ tự dựng video" }[action]);
      setSelected(new Set());
      refresh();
    } catch (e) {
      notify(e.message, "bad");
    } finally {
      setBusy(false);
    }
  };

  // Phím trong chế độ phóng to: ← → chuyển ảnh, Space chọn / bỏ chọn, Esc đóng
  useEffect(() => {
    if (zoom === null) return undefined;
    const key = (e) => {
      if (e.key === "ArrowRight") setZoom((z) => Math.min(shown.length - 1, z + 1));
      else if (e.key === "ArrowLeft") setZoom((z) => Math.max(0, z - 1));
      else if (e.key === " ") { e.preventDefault(); toggle(shown[zoom].key); }
      else if (e.key === "Escape") { e.stopPropagation(); setZoom(null); }
    };
    window.addEventListener("keydown", key, true);
    return () => window.removeEventListener("keydown", key, true);
  }, [zoom, shown]);

  return (
    <section className="review-panel">
      <div className="review-head">
        <div>
          <h3>Duyệt ảnh <span className="muted">({items.length})</span></h3>
          <p className="muted small">
            Bấm vào ảnh để xem lớn (← → chuyển ảnh, Space chọn). Tích chọn ảnh chưa ổn, rồi nhờ AI kiểm tra hoặc vẽ lại.
            Không cần sửa gì thì bấm <b>Ảnh ổn, làm tiếp</b>.
          </p>
        </div>
        <div className="segmented small">
          {Object.entries(KINDS).map(([k, label]) => (
            <button key={k} className={kind === k ? "active" : ""} onClick={() => setKind(k)}>
              {label} ({k === "all" ? items.length : items.filter((it) => it.kind === k).length})
            </button>
          ))}
        </div>
      </div>

      <div className="review-grid">
        {shown.map((it, i) => (
          <figure key={it.key} className={`review-card ${it.kind} ${selected.has(it.key) ? "picked" : ""}`}>
            <button className="review-img" onClick={() => setZoom(i)} title="Xem lớn">
              <img src={it.url} alt={it.caption} loading="lazy" />
            </button>
            {canAct && (
              <label className="review-check" title="Chọn ảnh này">
                <input type="checkbox" checked={selected.has(it.key)} onChange={() => toggle(it.key)} />
              </label>
            )}
            {it.ai && (
              <span className={`ai-badge ${it.ai.verdict === "đạt" ? "ok" : "bad"}`} title={aiDetail(it.ai)}>
                AI {it.ai.score}/5
              </span>
            )}
            <figcaption title={it.caption}>{it.caption}</figcaption>
            {noteOf(it) && <span className="note-badge" title={`Ghi chú khi vẽ lại: ${noteOf(it)}`}>✎</span>}
          </figure>
        ))}
      </div>

      {canAct ? (
        <div className="review-bar">
          <span className="muted">{n ? <>Đã chọn <b>{n}</b> ảnh · <button className="link-btn" onClick={() => setSelected(new Set())}>Bỏ chọn</button></> : "Chưa chọn ảnh nào"}</span>
          <span className="grow" />
          <button className="ghost" disabled={busy} onClick={() => send("ai_all")} title="Bận? Để AI duyệt hết và tự làm tiếp">🤖 Để AI duyệt hết</button>
          <button className="ghost" disabled={busy || !n} onClick={() => send("ai")}>🔍 AI kiểm tra {n || ""} ảnh</button>
          <button className="ghost" disabled={busy || !n} onClick={() => send("regen")}>↻ Vẽ lại {n || ""} ảnh</button>
          <button className="primary" disabled={busy} onClick={() => send("approve")}>✓ Ảnh ổn, làm tiếp</button>
        </div>
      ) : <p className="muted small">Chỉ người tạo video hoặc admin duyệt được ảnh.</p>}

      {zoom !== null && shown[zoom] && (
        <div className="lightbox" onMouseDown={(e) => e.target === e.currentTarget && setZoom(null)}>
          <button className="lb-nav prev" disabled={zoom === 0} onClick={() => setZoom(zoom - 1)} aria-label="Ảnh trước">‹</button>
          <figure className={shown[zoom].kind}>
            <img src={shown[zoom].url} alt={shown[zoom].caption} />
            <figcaption>
              <span>{zoom + 1}/{shown.length} · {shown[zoom].caption}</span>
              {shown[zoom].ai && <span className="lb-ai" title={aiDetail(shown[zoom].ai)}>AI {shown[zoom].ai.score}/5: {(shown[zoom].ai.problems || []).join("; ") || "ổn"}</span>}
              {canAct && (
                <textarea className="lb-note" rows={2} value={noteOf(shown[zoom])} onKeyDown={(e) => e.stopPropagation()}
                  placeholder="Ghi chú khi vẽ lại (tiếng Việt được), vd: chỉ cầm 1 cái mũ ở tay phải, không đội mũ"
                  onChange={(e) => {
                    const key = shown[zoom].key;
                    setNotes({ ...notes, [key]: e.target.value });
                    if (e.target.value.trim() && !selected.has(key)) toggle(key);
                  }} />
              )}
              {canAct && (
                <button className={selected.has(shown[zoom].key) ? "primary small-btn" : "ghost small-btn"} onClick={() => toggle(shown[zoom].key)}>
                  {selected.has(shown[zoom].key) ? "✓ Đã chọn" : "Chọn ảnh này"}
                </button>
              )}
            </figcaption>
          </figure>
          <button className="lb-nav next" disabled={zoom === shown.length - 1} onClick={() => setZoom(zoom + 1)} aria-label="Ảnh sau">›</button>
          <button className="lb-close" onClick={() => setZoom(null)} aria-label="Đóng">✕</button>
        </div>
      )}
    </section>
  );
}
