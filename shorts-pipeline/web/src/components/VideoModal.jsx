import { useEffect, useRef, useState } from "react";
import { api, duration, hours, REVIEW_MODES, RUN_STATUS, when } from "../api.js";
import { FixProgress, KaggleLog, KaggleProgress, LogView, Modal, Stepper } from "./common.jsx";
import { canManage, deleteVideo, downloadUrl, videoStatus } from "./Library.jsx";
import { ask } from "./Confirm.jsx";
import Icon from "./Icon.jsx";
import Comments from "./Comments.jsx";
import ReviewPanel from "./ReviewPanel.jsx";
import FixPanel from "./FixPanel.jsx";
import FixReview from "./FixReview.jsx";

export default function VideoModal({ video, state, me, admin, notify, refresh, onClose }) {
  const mine = canManage(video, me, admin);
  const player = useRef(null);
  const runs = state.runs.filter((r) => r.video === video.name);
  const [logId, setLogId] = useState(runs[0]?.id);
  const run = video.run;
  const running = run?.status === "running";
  const [status, cls] = videoStatus(video);
  const canFix = mine && video.output && !running && !video.review;
  const comments = state.feedback.filter((f) => f.video === video.name).length;
  // phần dưới chia tab: sửa cảnh (video đã xong) · góp ý · nhật ký; đang chạy / lỗi thì mở sẵn nhật ký
  const kaggleRunning = video.progress?.steps?.kaggle?.status === "running";
  const [logKind, setLogKind] = useState(running && kaggleRunning ? "kaggle" : "local");   // log máy / log Kaggle
  const [tab, setTab] = useState(running || runs[0]?.status === "failed" ? "log" : canFix ? "fix" : video.output ? "comments" : "log");
  // AI vừa vẽ xong bản sửa (hoặc lần chạy vừa kết thúc): tự mở tab xem ảnh sửa
  const hasReview = !!video.fix_review;
  useEffect(() => { if (hasReview && canFix) setTab("fix"); }, [hasReview, canFix]);

  const resume = () => api("/api/resume", { user: me, video: video.name })
    .then((r) => { notify(`Chạy tiếp ${video.name}`); setLogId(r.id); refresh(); })
    .catch((e) => notify(e.message, "bad"));
  const stop = async () => {
    const ok = await ask({
      tone: "warn", title: "Dừng video đang chạy?", confirmText: "Dừng lại",
      message: "Lô ảnh đã gửi lên Kaggle vẫn chạy nốt trên Kaggle. Bấm Chạy tiếp sau để lấy kết quả và làm tiếp.",
    });
    if (!ok) return;
    api("/api/stop", { id: run.id }).then(refresh).catch((e) => notify(e.message, "bad"));
  };

  return (
    <Modal title={video.title || video.name} onClose={onClose} wide>
      {video.review && (
        <div className="detail-review top">
          <ReviewPanel video={video} notify={notify} refresh={refresh} canAct={mine} />
        </div>
      )}

      <div className="video-detail">
        <div className="player">
          {video.output
            ? <video ref={player} src={`/videos/${encodeURIComponent(video.name)}/output.mp4`} controls playsInline />
            : video.thumb
              ? <img src={`/videos/${encodeURIComponent(video.name)}/${video.thumb}`} alt="" />
              : <div className="player-empty">Chưa có video</div>}
        </div>
        <div className="detail-side">
          <div className="detail-meta">
            <span className={`badge inline ${cls}`}>{status}</span>
            <span className="muted small">{video.name}{video.owner && ` · tạo bởi ${video.owner}`}</span>
            {video.progress?.gpu_hours > 0 && <span className="muted small">GPU đã dùng {hours(video.progress.gpu_hours)}</span>}
          </div>
          {video.models?.script_model && (
            <div className="detail-meta">
              <span className="chip plain muted small">Kịch bản: <b>{video.models.script_model}</b></span>
              <span className="chip plain muted small">Model duyệt: <b>{video.models.review_model}</b></span>
              {video.models.review_mode && (
                <span className="chip plain muted small">
                  {REVIEW_MODES[video.models.review_mode]?.icon} {REVIEW_MODES[video.models.review_mode]?.label}
                </span>
              )}
            </div>
          )}
          <h4>Đề tài</h4>
          <p className="prompt-full">{video.prompt || "(viết tay, không có đề tài)"}</p>
          {video.fix ? <FixProgress fix={video.fix} /> : <>
            <Stepper progress={video.progress} />
            <KaggleProgress progress={video.progress} />
          </>}
          {video.progress?.error && <p className="note bad">{video.progress.error}</p>}
          <div className="detail-actions">
            {mine && (running
              ? <button className="danger" onClick={stop}><Icon name="stop" /> Dừng</button>
              : !video.output && !video.review && <button className="primary" onClick={resume}>↻ Chạy tiếp</button>)}
            {video.output && (
              <a className="button" href={downloadUrl(video)} title="Lưu về máy bạn đang dùng"><Icon name="download" /> Tải về máy</a>
            )}
            {mine && (
              <button className="danger ghost push-right" onClick={async () => { if (await deleteVideo(video, notify, refresh)) onClose(); }}>
                <Icon name="trash" /> Xóa video
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="detail-tabs">
        {canFix && <button className={tab === "fix" ? "active" : ""} onClick={() => setTab("fix")}>
          ✨ {video.fix_review ? `Xem ảnh sửa (${video.fix_review.length})` : "Sửa cảnh lỗi"}</button>}
        {video.output && <button className={tab === "comments" ? "active" : ""} onClick={() => setTab("comments")}>💬 Góp ý ({comments})</button>}
        {runs.length > 0 && (
          <button className={tab === "log" ? "active" : ""} onClick={() => setTab("log")}>
            📜 Nhật ký <span className={RUN_STATUS[runs[0].status]?.[1]}>· {RUN_STATUS[runs[0].status]?.[0]}</span>
          </button>
        )}
      </div>

      {tab === "fix" && canFix && video.fix_review && (
        <div className="detail-review">
          <FixReview video={video} notify={notify} refresh={refresh} onStarted={(id) => { setLogId(id); setTab("log"); refresh(); }} />
        </div>
      )}

      {tab === "fix" && canFix && !video.fix_review && (
        <div className="detail-review">
          <FixPanel video={video} model={state.settings.image_model} player={player} notify={notify} onClose={() => setTab("comments")}
            onStarted={(id) => { setLogId(id); setTab("log"); refresh(); }} />
        </div>
      )}

      {tab === "comments" && video.output && (
        <div className="detail-comments">
          <Comments video={video} state={state} me={me} admin={admin} refresh={refresh} notify={notify} player={player} />
        </div>
      )}

      {tab === "log" && runs.length > 0 && (
        <div className="detail-runs">
          <div className="segmented small log-kind">
            <button className={logKind === "local" ? "active" : ""} onClick={() => setLogKind("local")}>🖥 Log máy</button>
            <button className={logKind === "kaggle" ? "active" : ""} onClick={() => setLogKind("kaggle")}>☁️ Log Kaggle</button>
          </div>
          {logKind === "kaggle" ? <KaggleLog video={video.name} follow={running && kaggleRunning} /> : <>
          <select className="runs-select" value={logId} onChange={(e) => setLogId(e.target.value)}>
            {runs.slice(0, 20).map((r) => (
              <option key={r.id} value={r.id}>
                {when(r.started)} · {r.label} · {r.user} · {RUN_STATUS[r.status]?.[0]} ({duration((r.ended || Date.now() / 1000) - r.started)})
              </option>
            ))}
          </select>
          <LogView runId={logId} follow={runs.find((r) => r.id === logId)?.status === "running"} />
          </>}
        </div>
      )}
    </Modal>
  );
}
