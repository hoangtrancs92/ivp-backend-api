import { useState } from "react";
import { duration, RUN_STATUS, when } from "../api.js";
import { Avatar, Empty, LogView } from "./common.jsx";

export default function Activity({ state, openVideo }) {
  const [logId, setLogId] = useState(null);
  const now = Date.now() / 1000;
  if (state.runs.length === 0) return <Empty icon="≡" title="Chưa có hoạt động">Mỗi lần ai đó chạy việc sẽ được ghi ở đây.</Empty>;

  return (
    <div className="panel">
      <div className="table">
        <table>
          <thead>
            <tr><th>Người dùng</th><th>Việc</th><th>Video / đề tài</th><th>Bắt đầu</th><th>Thời gian</th><th>Trạng thái</th><th /></tr>
          </thead>
          <tbody>
            {state.runs.map((r) => {
              const [text, cls] = RUN_STATUS[r.status] || [r.status, ""];
              return (
                <tr key={r.id} className={r.id === logId ? "selected" : ""}>
                  <td>
                    <span className="chip plain"><Avatar name={r.user} size={22} /> {r.user}</span>
                    {r.by && r.by !== r.user && <div className="muted small">bấm bởi {r.by}</div>}
                  </td>
                  <td>{r.label}</td>
                  <td className="clip">
                    {r.video ? <button className="link" onClick={() => openVideo(r.video)}>{r.video}</button> : "-"}
                    {r.prompt && <div className="muted small clip">{r.prompt}</div>}
                  </td>
                  <td className="muted">{when(r.started)}</td>
                  <td>{duration((r.ended || now) - r.started)}</td>
                  <td><span className={`badge inline ${cls}`}>{text}</span></td>
                  <td><button className="ghost" onClick={() => setLogId(logId === r.id ? null : r.id)}>Log</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {logId && <LogView runId={logId} follow={state.runs.find((r) => r.id === logId)?.status === "running"} />}
    </div>
  );
}
