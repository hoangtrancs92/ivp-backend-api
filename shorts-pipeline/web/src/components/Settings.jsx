import { useState } from "react";
import { api } from "../api.js";

// Trang Cài đặt AI (chỉ admin): cổng AI, danh sách model hiện ở dropdown, model mặc định cho từng việc
export default function Settings({ state, notify, refresh }) {
  const s = state.settings;
  const [form, setForm] = useState({
    ai_base_url: s.ai_base_url, models: s.models.join("\n"), script_model: s.script_model, review_model: s.review_model,
    telegram_bot_token: "", public_url: s.public_url || "", image_model: s.image_model || "gemini-2.5-flash-image",
    pexels_key: "", pixabay_key: "",
  });
  const [available, setAvailable] = useState(null);     // danh sách lấy từ cổng
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const models = [...new Set(form.models.split(/[\n,]+/).map((m) => m.trim()).filter(Boolean))];

  const save = async () => {
    try { await api("/api/settings", form); notify("Đã lưu cài đặt AI"); refresh(); }
    catch (e) { notify(e.message, "bad"); }
  };
  const fetchModels = async () => {
    setBusy(true);
    try { setAvailable((await api("/api/models", { ai_base_url: form.ai_base_url })).models); }
    catch (e) { notify(e.message, "bad"); }
    finally { setBusy(false); }
  };
  const toggle = (m) => setForm({
    ...form, models: (models.includes(m) ? models.filter((x) => x !== m) : [...models, m]).join("\n"),
  });

  return (
    <div className="settings">
      <section className="panel padded">
        <h2>Cổng AI</h2>
        <p className="muted">Endpoint chuẩn OpenAI của ShopAIKey (hoặc cổng khác cùng chuẩn). Khóa API mỗi người tự nhập ở hồ sơ của mình.</p>
        <label className="field">Endpoint
          <input value={form.ai_base_url} onChange={set("ai_base_url")} placeholder="https://api.shopaikey.com/v1" />
        </label>
      </section>

      <section className="panel padded">
        <h2>Model hiện ở dropdown</h2>
        <p className="muted">Mỗi dòng một model id (hoặc cách nhau bằng dấu phẩy). Đổi thoải mái khi ShopAIKey đổi tên model.</p>
        <div className="settings-grid">
          <label className="field">Danh sách model
            <textarea rows={8} value={form.models} onChange={set("models")} spellCheck={false} className="mono" />
          </label>
          <div className="field">
            <div className="row-between">
              <span>Model cổng đang có {available && <em className="muted">({available.length})</em>}</span>
              <button className="ghost small-btn" onClick={fetchModels} disabled={busy}>{busy ? "Đang lấy..." : "↻ Lấy từ cổng"}</button>
            </div>
            {available ? (
              <>
                <input placeholder="Lọc: claude, gpt, gemini..." value={filter} onChange={(e) => setFilter(e.target.value)} />
                <div className="model-pick">
                  {available.filter((m) => m.toLowerCase().includes(filter.toLowerCase())).map((m) => (
                    <button key={m} className={models.includes(m) ? "on" : ""} onClick={() => toggle(m)}>
                      {models.includes(m) ? "✓ " : "+ "}{m}
                    </button>
                  ))}
                </div>
              </>
            ) : <p className="muted small">Bấm "Lấy từ cổng" để xem mọi model khóa của bạn dùng được, bấm vào model để thêm hoặc bớt.</p>}
          </div>
        </div>
      </section>

      <section className="panel padded">
        <h2>Model mặc định</h2>
        <div className="form-row">
          <label className="field">Viết kịch bản
            <select value={form.script_model} onChange={set("script_model")}>{models.map((m) => <option key={m}>{m}</option>)}</select>
            <small className="muted">Model mặc định dùng để viết truyện tiếng Nhật.</small>
          </label>
          <label className="field">Duyệt ảnh
            <select value={form.review_model} onChange={set("review_model")}>{models.map((m) => <option key={m}>{m}</option>)}</select>
            <small className="muted">Phải là model đọc được ảnh (vision). Mỗi video duyệt khoảng 50-70 ảnh.</small>
          </label>
          <label className="field">Sửa ảnh lỗi (video đã xong)
            <input value={form.image_model} onChange={set("image_model")} list="image-models" className="mono" />
            <datalist id="image-models">
              {["gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview", "gpt-image-1", "gpt-image-1.5"]
                .map((m) => <option key={m} value={m} />)}
            </datalist>
            <small className="muted">Model vẽ / sửa ảnh của cổng AI. Nút "🛠 Sửa cảnh lỗi" ở video đã xong dùng model này.</small>
          </label>
        </div>
      </section>

      <section className="panel padded">
        <h2>Ảnh thật <em className="muted">(video Nhật Bản vs nước khác)</em></h2>
        <p className="muted">
          Kịch bản so sánh có 3-5 cảnh ảnh chụp thật làm dẫn chứng, tải tự động (miễn phí, dùng được cho video kiếm tiền, không bắt
          ghi nguồn). Pixabay: đăng ký tài khoản, đăng nhập rồi mở{" "}
          <a href="https://pixabay.com/api/docs/" target="_blank" rel="noreferrer">pixabay.com/api/docs</a>, khóa nằm ở mục
          Parameters (dòng key). Pexels đang tạm ngừng cấp khóa mới. Ngoài ra luôn tìm thêm Wikimedia Commons (không cần khóa, nhiều
          ảnh đúng mẫu xe; nguồn ảnh tự ghi vào credits.txt của video). Từ khóa có tên hãng thì tìm Wikimedia trước.
        </p>
        <div className="form-row">
          <label className="field">
            <span>Khóa API Pixabay {s.pixabay && <em className="ok">✓ đã có</em>}</span>
            <input type="password" autoComplete="off" value={form.pixabay_key} onChange={set("pixabay_key")}
              placeholder={s.pixabay ? "để trống để giữ khóa cũ" : "dán khóa API Pixabay"} />
          </label>
          <label className="field">
            <span>Khóa API Pexels {s.pexels && <em className="ok">✓ đã có</em>}</span>
            <input type="password" autoComplete="off" value={form.pexels_key} onChange={set("pexels_key")}
              placeholder={s.pexels ? "để trống để giữ khóa cũ" : "dán khóa API Pexels"} />
          </label>
        </div>
      </section>

      <section className="panel padded">
        <h2>Thông báo Telegram <em className="muted">(tùy chọn)</em></h2>
        <p className="muted">
          Báo về Telegram khi video xong, lỗi hoặc chờ duyệt ảnh. Tạo bot: nhắn <b>@BotFather</b> lệnh <code>/newbot</code>,
          đặt tên, rồi dán token nó gửi vào đây. Mỗi người tự nhập chat ID và chọn loại thông báo ở Hồ sơ của mình.
        </p>
        <div className="form-row">
          <label className="field">
            <span>Token bot {s.telegram_bot && <em className="ok">✓ đã có</em>}
            {s.telegram_bot_username && <> · bot: <a href={`https://t.me/${s.telegram_bot_username}`} target="_blank"
              rel="noreferrer">t.me/{s.telegram_bot_username}</a></>}</span>
            <input type="password" autoComplete="off" value={form.telegram_bot_token} onChange={set("telegram_bot_token")}
              placeholder={s.telegram_bot ? "để trống để giữ token cũ" : "123456789:AA..."} />
          </label>
          <label className="field">Địa chỉ trang web (gắn vào tin nhắn)
            <input value={form.public_url} onChange={set("public_url")} placeholder="https://....trycloudflare.com" />
            <small className="muted">Để trống thì tin nhắn không kèm link. Link Cloudflare đổi mỗi lần chạy lại.</small>
          </label>
        </div>
      </section>

      <div className="settings-actions"><button className="primary" onClick={save}>Lưu cài đặt</button></div>
    </div>
  );
}
