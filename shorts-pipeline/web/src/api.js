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
export const REVIEW_MODES = {   // thứ tự hiện trên trang; "none" là mặc định
  none: { icon: "⏩", label: "Không duyệt", short: "Dùng luôn ảnh Kaggle vẽ, dựng ngay. Nhanh, rẻ nhất.",
    hint: "Dùng luôn ảnh Kaggle vẽ ra và dựng video ngay. Nhanh và rẻ nhất. Ảnh lỗi sửa sau bằng Sửa cảnh lỗi." },
  manual: { icon: "👀", label: "Tôi tự duyệt", short: "Dừng chờ bạn xem ảnh, chọn ảnh vẽ lại.",
    hint: "Kaggle vẽ xong thì dừng chờ bạn xem bằng mắt, chọn ảnh cần vẽ lại rồi mới dựng video." },
  ai: { icon: "🤖", label: "AI duyệt", short: "AI chấm mọi ảnh, tự vẽ lại ảnh hỏng.",
    hint: "AI chấm mọi ảnh (đạt từ 3/5), tự vẽ lại ảnh hỏng tối đa 3 lượt rồi dựng luôn. Tốn thêm tiền API và giờ GPU." },
};

// Kiểu kể khi tạo video: AI viết kịch bản theo kiểu này và tự chọn giọng VOICEVOX cho từng nhân vật
export const VOICE_MODES = {
  narration: { icon: "🎙", label: "Một giọng kể chính", short: "Lời kể là chính, nhân vật nói xen. Hợp 2ch, cảm động.", hint: "Phần lớn là lời kể (người kể hoặc nhân vật chính tự kể), nhân vật khác nói xen ở câu then chốt. Hợp truyện 2ch, cảm động." },
  dialogue: { icon: "💬", label: "Nhân vật nói chuyện", short: "Thoại qua lại, mỗi người một giọng. Hợp hài, gia đình.", hint: "Phần lớn là thoại qua lại giữa các nhân vật, mỗi người một giọng, lời kể chỉ để nối. Hợp hài, cãi nhau, gia đình, công sở." },
};

export const STEP_ICON = { done: "✓", skipped: "✓", running: "", failed: "!", pending: "", waiting: "👀" };

export const RUN_STATUS = {
  running: ["Đang chạy", "warn"], done: ["Hoàn thành", "ok"], failed: ["Lỗi", "bad"],
  stopped: ["Đã dừng", "muted"], interrupted: ["Bị ngắt", "muted"], waiting: ["Chờ duyệt ảnh", "warn"],
};

// Kiểu chuyện khi tạo video: AI viết kịch bản theo công thức này ("auto" = AI tự chọn theo đề tài)
export const STORY_MODES = {
  auto: { icon: "✨", label: "AI tự chọn", short: "Chọn thể loại hợp đề tài nhất.", hint: "AI tự chọn thể loại, cấu trúc theo đề tài." },
  twist: { icon: "🔄", label: "Bí mật + cú lật", short: "Lộ dần manh mối, câu cuối lật ngược.",
    hint: "Kiểu 「スカッと迷言集」: điều bất thường ở câu đầu, sự thật lộ dần, tưởng đã xong thì câu cuối lật ngược, kết cụt. Có cảnh màn hình điện thoại." },
  sukatto: { icon: "⚖️", label: "Sảng khoái trả đũa", short: "Kẻ xấu chèn ép rồi bị trả giá.",
    hint: "スカッと: nhân vật chính bị chèn ép ngày càng quá đáng, rồi lật thế, kẻ xấu bị trả giá thích đáng." },
  touching: { icon: "😢", label: "Cảm động", short: "Bí mật hy sinh, kết ấm áp / day dứt.",
    hint: "Gia đình, tình thân, tình bạn; hiểu lầm hoặc hy sinh lộ ra ở cuối." },
  comedy: { icon: "😂", label: "Hài", short: "Leo thang vô lý, câu chốt bất ngờ.",
    hint: "Tình huống đời thường leo thang vô lý, nhiều thoại, nhịp nhanh." },
  kaigai: { icon: "🇯🇵", label: "Nhật Bản và các nước", short: "Phân tích khoảng 2 phút, hình gọn, dẫn chứng rõ.",
    hint: "Một câu hỏi chính, 3 luận điểm có dẫn chứng và phản biện. Giọng kể dẫn dắt, linh vật xuất hiện ở vài mốc; bảng số liệu dễ đọc, ít hiệu ứng." },
};

// Cách dựng video truyện kể: "new" = như kênh スカッと迷言集 (video mẫu): tranh vẽ cả cảnh, bí mật + cú lật, nhạc rõ
export const STYLES = {
  classic: { icon: "🎬", label: "Cách dựng hiện tại", short: "Nhân vật cắt rời ghép lên nền, nhiều chuyển động.",
    hint: "Như các video trước: ảnh nhân vật tách nền ghép lên ảnh bối cảnh, chuyển động nhân vật, hiệu ứng." },
  new: { icon: "✨", label: "Cách dựng mới (theo video mẫu)", short: "Mỗi cảnh một tranh có người, bí mật + cú lật, cảnh điện thoại.",
    hint: "Như kênh スカッと迷言集: kể ngôi thứ nhất, bí mật lộ dần, câu cuối lật ngược; mỗi cảnh một tranh vẽ cả cảnh có 1-2 người ở cự ly gần; cảnh màn hình điện thoại; nhạc nền rõ hơn." },
};

// Trang Tạo video: 3 ô cách dựng (style + kiểu chuyện gửi cho server, xem steps/01_script.py)
export const BUILD_MODES = {
  classic: { icon: "🎬", label: "Dựng hiện tại", style: "classic", story: "auto",
    short: "Nhân vật cắt rời ghép lên nền, nhiều chuyển động.", hint: "Như các video trước: AI tự chọn thể loại." },
  anime: { icon: "🖼", label: "Tĩnh có anime", style: "new", story: "twist",
    short: "Mỗi cảnh một tranh, nữ đẹp nét anime, bí mật + cú lật.", hint: "Như video mẫu スカッと迷言集: tranh vẽ cả cảnh, cảnh điện thoại, câu cuối lật ngược." },
  contrast: { icon: "⚖️", label: "Tương phản", style: "new", story: "contrast",
    short: "Chuyện chia hai phe, hoặc Nhật đấu nước khác.", hint: "Hai bên đối lập, ai cũng có lý, người xem tự chọn phe." },
};
export const CONTRAST_KINDS = {
  random: { icon: "🎲", label: "Ngẫu nhiên", hint: "Từ đề tài bạn nhập, AI viết dàn ý chia hai phe theo quy tắc móc câu + tương phản, rồi mới viết kịch bản." },
  japan: { icon: "🇯🇵", label: "Nhật Bản vs nước khác", hint: "Phân tích khoảng 2 phút: 3 luận điểm, dẫn chứng đúng chủ đề, phản biện và kết luận rõ. Hình gọn, ít hiệu ứng." },
};
// = steps/compare_facts.py COUNTRIES
export const COUNTRIES = {
  CHN: "Trung Quốc", KOR: "Hàn Quốc", USA: "Mỹ", VNM: "Việt Nam", IND: "Ấn Độ", THA: "Thái Lan", PHL: "Philippines",
  IDN: "Indonesia", GBR: "Anh", FRA: "Pháp", DEU: "Đức", RUS: "Nga", BRA: "Brazil",
};
