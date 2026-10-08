// Gọi API của web/app.py. Lỗi từ server (400) trả về { error } và được ném ra thành Error.
export async function api(path, body) {
  const res = await fetch(path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {});
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || res.statusText);
    err.status = res.status;
    if (res.status === 401) window.dispatchEvent(new Event("logged-out"));   // App chuyển về trang đăng nhập
    throw err;
  }
  return data;
}

export const KEYS = ["kaggle_key", "hf_token", "ai_api_key"];

export const when = (t) => t ? new Date(t * 1000).toLocaleString("vi-VN",
  { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "2-digit" }) : "";

export const duration = (s) => s < 60 ? `${Math.max(0, Math.round(s))} giây`
  : s < 3600 ? `${Math.round(s / 60)} phút` : `${Math.floor(s / 3600)} giờ ${Math.round((s % 3600) / 60)} phút`;

export const ago = (t) => {
  const s = Date.now() / 1000 - t;
  if (s < 60) return "vừa xong";
  if (s < 3600) return `${Math.floor(s / 60)} phút trước`;
  if (s < 86400) return `${Math.floor(s / 3600)} giờ trước`;
  if (s < 7 * 86400) return `${Math.floor(s / 86400)} ngày trước`;
  return when(t);
};

export const hours = (h) => h == null ? "?" : `${h.toFixed(1)} giờ`;

export const initials = (name) => name.split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();

// Màu avatar cố định theo tên
export const hue = (name) => [...name].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);

// localStorage có thể bị chặn (cửa sổ ẩn danh): lỗi thì bỏ qua
export const store = {
  get: (k, d = "") => { try { return localStorage.getItem(k) ?? d; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* bỏ qua */ } },
};

// Chế độ duyệt ảnh khi tạo video
export const REVIEW_MODES = {
  manual: { icon: "👀", label: "Tôi tự duyệt", hint: "Kaggle vẽ xong thì dừng chờ bạn xem bằng mắt, chọn ảnh cần vẽ lại rồi mới dựng video." },
  ai: { icon: "🤖", label: "AI duyệt tự động", hint: "Lúc bận: AI chấm mọi ảnh (đạt từ 3/5), tự vẽ lại ảnh hỏng tối đa 3 lượt rồi dựng luôn. Tốn thêm tiền API và giờ GPU." },
  none: { icon: "⏩", label: "Không duyệt", hint: "Dùng luôn ảnh Kaggle vẽ ra và dựng video ngay. Nhanh và rẻ nhất." },
};

export const STEP_ICON = { done: "✓", skipped: "✓", running: "", failed: "!", pending: "", waiting: "👀" };

export const RUN_STATUS = {
  running: ["Đang chạy", "warn"], done: ["Hoàn thành", "ok"], failed: ["Lỗi", "bad"],
  stopped: ["Đã dừng", "muted"], interrupted: ["Bị ngắt", "muted"], waiting: ["Chờ duyệt ảnh", "warn"],
};
