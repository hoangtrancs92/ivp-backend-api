import { useState } from "react";
import { api, KEYS } from "../api.js";
import { Modal } from "./common.jsx";
import { ask } from "./Confirm.jsx";

const FIELDS = [
  ["kaggle_key", "Kaggle API token", "KGAT_...", "kaggle.com/settings/api → Generate New Token, hoặc chạy: kaggle auth print-access-token"],
  ["hf_token", "Hugging Face token", "hf_...", "huggingface.co/settings/tokens, quyền read"],
  ["ai_api_key", "AI API key (ShopAIKey)", "sk-...", "Khóa ở trang ShopAIKey; dùng để viết kịch bản và duyệt từng ảnh"],
];

// user: hồ sơ đang sửa (khóa chỉ là true/false, server không gửi khóa thật), undefined: thành viên mới (chỉ admin)
export default function UserModal({ user, me, admin, bot, onClose, onSaved }) {
  const self = user?.name === me;
  const [form, setForm] = useState({
    name: user?.name || "", kaggle_username: user?.kaggle_username || "", role: user?.role || "user",
    password: "", old_password: "", ...Object.fromEntries(KEYS.map((k) => [k, ""])),
    telegram_chat_id: user?.telegram_chat_id || "", telegram_notify: user?.telegram_notify || "all",
  });
  const [error, setError] = useState("");
  const [tg, setTg] = useState({ chats: null, msg: "", busy: false });   // tìm chat ID, gửi thử
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const findChats = async () => {
    setTg({ ...tg, busy: true, msg: "" });
    try {
      const { chats } = await api("/api/telegram/chats", {});
      setTg({ chats, busy: false, msg: chats.length ? "" : "Chưa thấy ai nhắn cho bot. Mở bot trên Telegram, bấm Start (hoặc nhắn /start), rồi bấm lại." });
    } catch (err) { setTg({ chats: null, busy: false, msg: err.message }); }
  };
  const testSend = async () => {
    setTg({ ...tg, busy: true, msg: "" });
    try { await api("/api/telegram/test", { chat_id: form.telegram_chat_id, user: form.name }); setTg({ ...tg, busy: false, msg: "✓ Đã gửi tin thử, kiểm tra Telegram." }); }
    catch (err) { setTg({ ...tg, busy: false, msg: err.message }); }
  };

  const save = async (e) => {
    e.preventDefault();
    try { await api("/api/user", form); onSaved(`Đã lưu hồ sơ ${form.name.trim()}`); }
    catch (err) { setError(err.message); }
  };
  const remove = async () => {
    const ok = await ask({
      tone: "danger", title: "Xóa thành viên?", confirmText: "Xóa thành viên", subject: <b>{user.name}</b>,
      details: ["Xóa hồ sơ, mật khẩu và các khóa API", "Đăng xuất người này khỏi mọi máy", "Video của họ vẫn giữ nguyên"],
    });
    if (!ok) return;
    try { await api("/api/user/delete", { name: user.name }); onSaved(`Đã xóa ${user.name}`); }
    catch (err) { setError(err.message); }
  };

  return (
    <Modal title={!user ? "Thành viên mới" : self ? "Hồ sơ của tôi" : `Hồ sơ của ${user.name}`} onClose={onClose}>
      <form className="form" onSubmit={save}>
        <div className="form-row">
          <label>Tên đăng nhập
            <input value={form.name} onChange={set("name")} disabled={!!user} placeholder="vd: tusthao" autoFocus={!user} />
          </label>
          {admin && !self ? (
            <label>Quyền
              <select value={form.role} onChange={set("role")}>
                <option value="user">Thành viên</option>
                <option value="admin">Admin</option>
              </select>
            </label>
          ) : <span />}
        </div>

        <fieldset>
          <legend>Mật khẩu</legend>
          <div className="form-row">
            {self && !admin && (
              <label>Mật khẩu hiện tại
                <input type="password" value={form.old_password} onChange={set("old_password")} autoComplete="current-password" />
              </label>
            )}
            <label>{user ? "Mật khẩu mới" : "Mật khẩu"}
              <input type="password" value={form.password} onChange={set("password")} autoComplete="new-password"
                placeholder={user ? "để trống nếu không đổi" : "ít nhất 6 ký tự"} />
            </label>
          </div>
        </fieldset>

        <fieldset>
          <legend>Kaggle, Hugging Face, AI</legend>
          <label>Kaggle username
            <input value={form.kaggle_username} onChange={set("kaggle_username")} placeholder="phần sau kaggle.com/ trên trang hồ sơ" />
          </label>
          {FIELDS.map(([key, text, ph, help]) => (
            <label key={key}>
              <span>{text} {user?.[key] && <em className="ok">✓ đã có</em>}</span>
              <input type="password" autoComplete="off" value={form[key]} onChange={set(key)}
                placeholder={user?.[key] ? "để trống để giữ khóa cũ" : ph} />
              <small>{help}</small>
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>Thông báo Telegram (tùy chọn)</legend>
          <div className="form-row">
            <label>Chat ID
              <input value={form.telegram_chat_id} onChange={set("telegram_chat_id")} placeholder="vd 123456789; để trống = tắt" inputMode="numeric" />
            </label>
            <label>Báo khi
              <select value={form.telegram_notify} onChange={set("telegram_notify")} disabled={!form.telegram_chat_id}>
                <option value="all">Xong, lỗi và chờ duyệt ảnh</option>
                <option value="errors">Chỉ khi lỗi</option>
                <option value="">Tắt</option>
              </select>
            </label>
          </div>
          {form.telegram_chat_id.includes(":")
            ? <small className="bad">Đây là token bot, không phải chat ID. Token dán ở trang Cài đặt (admin); chat ID chỉ gồm chữ số.</small>
            : <small>
                Mở bot của nhóm {bot
                  ? <a href={`https://t.me/${bot}`} target="_blank" rel="noreferrer"><b>t.me/{bot}</b></a>
                  : "trên Telegram"}, bấm Start, rồi bấm "Tìm chat ID" để chọn tên mình.
              </small>}
          <div className="row-between">
            <button type="button" className="ghost small-btn" onClick={findChats} disabled={tg.busy}>🔎 Tìm chat ID</button>
            <button type="button" className="ghost small-btn" onClick={testSend} disabled={tg.busy || !form.telegram_chat_id}>📨 Gửi thử</button>
          </div>
          {tg.chats?.length > 0 && (
            <div className="model-pick">
              {tg.chats.map((c) => (
                <button type="button" key={c.id} className={form.telegram_chat_id === c.id ? "on" : ""}
                  onClick={() => setForm({ ...form, telegram_chat_id: c.id })}>
                  {c.name || c.id}{c.username && ` @${c.username}`}
                </button>
              ))}
            </div>
          )}
          {tg.msg && <small>{tg.msg}</small>}
        </fieldset>
        <p className="note">Khóa chỉ lưu trên máy chạy server (data/users.json) và không bao giờ hiện lại trên trang.</p>
        {error && <p className="note bad">{error}</p>}
        <div className="modal-actions">
          {admin && user && !self && <button type="button" className="danger ghost" onClick={remove}>Xóa thành viên</button>}
          <span className="grow" />
          <button type="button" className="ghost" onClick={onClose}>Hủy</button>
          <button type="submit" className="primary">Lưu</button>
        </div>
      </form>
    </Modal>
  );
}
