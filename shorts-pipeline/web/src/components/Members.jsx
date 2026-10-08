import { api, when } from "../api.js";
import { Avatar, QuotaBar } from "./common.jsx";
import { ask } from "./Confirm.jsx";

const KEY_LABELS = [["kaggle_key", "Kaggle"], ["hf_token", "Hugging Face"], ["ai_api_key", "AI"]];

export default function Members({ state, me, admin, editUser, notify, refresh }) {
  const s = state.stats;
  const uploadLora = async (name) => {
    const ok = await ask({
      title: "Đưa LoRA lên Kaggle?", confirmText: "Đưa lên",
      message: `Tải file style.safetensors (khoảng 45 MB) lên tài khoản Kaggle của ${name}. Mỗi tài khoản chỉ cần làm một lần.`,
    });
    if (!ok) return;
    api("/api/upload_lora", { user: name }).then(() => { notify("Đang đưa LoRA lên, xem ở trang Hoạt động"); refresh(); })
      .catch((e) => notify(e.message, "bad"));
  };
  const recheck = (name) => api("/api/quota", { user: name }).then(refresh).catch((e) => notify(e.message, "bad"));

  return (
    <>
      <div className="stats">
        <Stat value={s.users} label="thành viên" />
        <Stat value={s.online} label="đang mở trang" dot />
        <Stat value={s.active} label="người đang chạy việc" />
        <Stat value={s.running} label="việc đang chạy" />
      </div>
      {admin && <div className="toolbar"><span /><button className="primary" onClick={() => editUser("")}>+ Thêm thành viên</button></div>}
      <div className="members">
        {state.users.map((u) => {
          const self = u.name === me;
          const manage = admin || self;
          return (
            <article key={u.name} className={`member ${self ? "is-me" : ""}`}>
              <div className="member-head">
                <Avatar name={u.name} size={44} online={u.online} />
                <div>
                  <h3>{u.name} <span className={`role ${u.role === "admin" ? "admin" : ""}`}>{u.role === "admin" ? "Admin" : "Thành viên"}</span></h3>
                  <p className="muted small">
                    {u.kaggle_username ? `kaggle.com/${u.kaggle_username}` : "chưa có Kaggle"} · {u.online ? "đang online" : `lần cuối ${when(u.last_seen) || "-"}`}
                  </p>
                </div>
              </div>
              <QuotaBar quota={u.quota} />
              <div className="keys">
                {KEY_LABELS.map(([k, label]) => <span key={k} className={`key ${u[k] ? "has" : ""}`}>{u[k] ? "✓" : "✗"} {label}</span>)}
              </div>
              <div className="member-stats">
                <span><b>{u.videos}</b> video</span>
                <span><b>{u.runs}</b> lần chạy</span>
                <span>{u.running.length ? <b className="warn">đang chạy {u.running.join(", ")}</b> : <span className="muted">rảnh</span>}</span>
              </div>
              {manage && (
                <div className="member-actions">
                  <button className="ghost" onClick={() => editUser(u.name)}>{self ? "Hồ sơ của tôi" : "Sửa"}</button>
                  <button className="ghost" onClick={() => recheck(u.name)}>↻ Giờ GPU</button>
                  <button className="ghost" onClick={() => uploadLora(u.name)}>Đưa LoRA lên</button>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </>
  );
}

function Stat({ value, label, dot }) {
  return <div className="stat">{dot && <i className="presence on static" />}<b>{value}</b><span>{label}</span></div>;
}
