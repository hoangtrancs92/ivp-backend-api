import { useEffect, useState } from "react";
import { api } from "../api.js";
import { ask } from "./Confirm.jsx";

const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;

// Video đã xong: chọn cảnh có hình lỗi (tay dị dạng, đồ vật méo...), AI sửa ảnh giữ ~90% giống ảnh cũ rồi dựng lại video.
export default function FixPanel({ video, model, player, notify, onStarted, onClose }) {
  const [scenes, setScenes] = useState(null);
  const [error, setError] = useState("");
  const [picked, setPicked] = useState({});        // id cảnh -> ghi chú
  useEffect(() => {
    api(`/api/scenes?video=${encodeURIComponent(video.name)}`)
      .then((r) => setScenes(r.scenes)).catch((e) => setError(e.message));
  }, [video.name]);

  const toggle = (sc) => {
    if (!sc.images.length) return;
    const next = { ...picked };
    if (sc.id in next) delete next[sc.id]; else next[sc.id] = "";
    setPicked(next);
  };
  const ids = Object.keys(picked);

  // dừng video ở chỗ thấy lỗi rồi bấm: chọn đúng cảnh đang hiện và cuộn tới nó
  const pickCurrent = () => {
    const t = player?.current?.currentTime ?? 0;
    const timed = (scenes || []).filter((x) => x.start != null);
    const sc = timed.find((x) => t >= x.start && t < x.end) || [...timed].reverse().find((x) => t >= x.start);
    if (!sc) return notify("Video này chưa có mốc giờ từng cảnh, chọn bằng ảnh bên dưới.", "bad");
    if (!sc.images.length) return notify(`Cảnh ${sc.id} (${mmss(t)}) chỉ có nền, không có ảnh nhân vật để sửa.`, "bad");
    setPicked((p) => (sc.id in p ? p : { ...p, [sc.id]: "" }));
    document.getElementById(`fix-scene-${sc.id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    notify(`Đã chọn cảnh ${sc.id} (${mmss(t)})`);
  };
  const seek = (sc) => {
    if (!player?.current || sc.start == null) return;
    player.current.currentTime = sc.start + 0.05;
    player.current.pause();
    player.current.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const submit = async () => {
    const ok = await ask({
      tone: "warn", title: `Sửa ${ids.length} cảnh bằng AI?`, confirmText: "Sửa và dựng lại",
      details: [
        `Model ${model} sửa ảnh nhân vật / đồ vật của các cảnh đã chọn, giữ khoảng 90% giống ảnh cũ`,
        "Không dùng Kaggle; tốn tiền API theo số ảnh (cảnh nhiều nhân vật / tư thế 2 có nhiều ảnh)",
        "Dựng lại video (vài phút); bản cũ giữ ở work/output_truoc_sua.mp4, ảnh cũ ở rejected/",
      ],
    });
    if (!ok) return;
    try {
      const r = await api("/api/fix", { video: video.name, scenes: ids.map((id) => ({ id, note: picked[id] })) });
      notify(`Đang sửa ${ids.length} cảnh của ${video.name}`);
      onStarted(r.id);
    } catch (e) { notify(e.message, "bad"); }
  };

  return (
    <div className="review-panel">
      <div className="review-head">
        <div>
          <h3>🛠 Sửa cảnh lỗi</h3>
          <p className="muted small">
            Cách 1: xem video, thấy lỗi thì dừng lại rồi bấm "📍 Chọn cảnh đang xem". Cách 2: bấm vào ảnh cảnh bên dưới
            (bấm ▶ mốc giờ để video nhảy tới cảnh đó xem lại). Lỗi hay gặp: tay, ngón tay dị dạng, đồ vật méo.
            Ghi thêm chỗ lỗi nếu muốn, AI sửa đúng chỗ đó. Cảnh chỉ có nền thì không sửa được.
          </p>
        </div>
        <div className="fix-actions">
          <button className="primary" onClick={pickCurrent} disabled={!scenes} title="Dừng video ở chỗ thấy lỗi rồi bấm">📍 Chọn cảnh đang xem</button>
          <button className="ghost" onClick={onClose}>Đóng</button>
        </div>
      </div>
      {error ? <p className="note bad">{error}</p> : !scenes ? <p className="muted">Đang tải các cảnh...</p> : (
        <div className="review-grid fix-grid">
          {scenes.map((sc) => (
            <figure key={sc.id} id={`fix-scene-${sc.id}`}
              className={`review-card background ${sc.id in picked ? "picked" : ""} ${sc.images.length ? "" : "bg-only"}`}>
              <button className="review-img" onClick={() => toggle(sc)} title={sc.images.length ? "Chọn cảnh này" : "Cảnh chỉ có nền"}>
                {sc.thumb
                  ? <img src={sc.thumb} alt="" loading="lazy"
                      onError={(e) => { if (!e.target.dataset.retry) { e.target.dataset.retry = 1; e.target.src = `${sc.thumb}&r=${Date.now()}`; } }} />
                  : <span className="muted small">Cảnh {sc.id}</span>}
                {!sc.images.length && <span className="bg-only-tag">Chỉ có nền</span>}
              </button>
              {sc.images.length > 0 && (
                <label className="review-check" title="Chọn cảnh này">
                  <input type="checkbox" checked={sc.id in picked} onChange={() => toggle(sc)} />
                </label>
              )}
              <figcaption title={sc.text}>
                {sc.start != null && (
                  <button className="link-btn" onClick={() => seek(sc)} title="Xem cảnh này trong video">▶ {mmss(sc.start)}</button>
                )}{" "}
                Cảnh {sc.id} · {sc.text.split("\n").join(" ")}
              </figcaption>
            </figure>
          ))}
        </div>
      )}
      {ids.length > 0 && scenes && (
        <div className="fix-picked">
          <h4>Cảnh đã chọn ({ids.length}) · ghi chú cho AI (không bắt buộc)</h4>
          {ids.map((id) => {
            const sc = scenes.find((x) => String(x.id) === String(id));
            return (
              <div key={id} className="fix-row">
                {sc?.thumb && <img src={sc.thumb} alt="" onClick={() => seek(sc)} title="Xem cảnh này trong video" />}
                <div className="fix-row-body">
                  <div className="row-between">
                    <b>Cảnh {id}{sc?.start != null && ` · ${mmss(sc.start)}`}</b>
                    <button className="link-btn" onClick={() => toggle(sc)}>Bỏ chọn</button>
                  </div>
                  <span className="muted small">{sc?.text.replace(/\n/g, " ")}</span>
                  <textarea rows={2} value={picked[id]} onChange={(e) => setPicked({ ...picked, [id]: e.target.value })}
                    placeholder="Lỗi ở đâu, cảnh muốn thể hiện gì. Vd: tay phải cầm lon bia bị dính vào tay đang gãi đầu; nhân vật đang ngượng, tự giới thiệu" />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <div className="review-bar">
        <span className="muted small">{ids.length ? `Đã chọn ${ids.length} cảnh: ${ids.join(", ")}` : "Chưa chọn cảnh nào"}</span>
        <span className="grow" />
        <button className="primary" disabled={!ids.length} onClick={submit}>Sửa {ids.length || ""} cảnh và dựng lại</button>
      </div>
    </div>
  );
}
