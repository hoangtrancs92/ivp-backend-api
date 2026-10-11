import { useCallback, useEffect, useState } from "react";
import { api, store } from "./api.js";
import Sidebar from "./components/Sidebar.jsx";
import Studio from "./components/Studio.jsx";
import Library from "./components/Library.jsx";
import Activity from "./components/Activity.jsx";
import Members from "./components/Members.jsx";
import UserModal from "./components/UserModal.jsx";
import VideoModal from "./components/VideoModal.jsx";
import Login from "./components/Login.jsx";
import ConfirmHost from "./components/Confirm.jsx";
import Settings from "./components/Settings.jsx";
import FeedbackPage from "./components/FeedbackPage.jsx";
import Skits from "./components/Skits.jsx";

const PAGES = {
  studio: ["Tạo video", "Nhập đề tài, mọi bước còn lại chạy tự động"],
  skits: ["Tiểu phẩm", "Tiểu phẩm hài một sân khấu: nhân vật lồng tiếng, chữ thoại theo người nói, cảnh chèn"],
  library: ["Thư viện", "Tất cả video đã và đang làm"],
  activity: ["Hoạt động", "Ai đã chạy gì, khi nào"],
  feedback: ["Góp ý", "Tổng hợp nhận xét của mọi người về các video, để cải thiện quy trình"],
  members: ["Thành viên", "Tài khoản và giờ GPU Kaggle của từng người"],
  settings: ["Cài đặt AI", "Cổng AI (ShopAIKey) và các model dùng để viết kịch bản, duyệt ảnh"],
};

export default function App() {
  const [state, setState] = useState(null);
  const [auth, setAuth] = useState("checking");     // checking | in | out
  const [page, setPage] = useState(() => {
    const hash = window.location.hash.slice(1);
    return PAGES[hash] ? hash : PAGES[store.get("page")] ? store.get("page") : "studio";
  });
  const [editing, setEditing] = useState(null);     // null: đóng, "": người dùng mới, tên: sửa hồ sơ
  const [open, setOpen] = useState(null);           // tên video đang mở
  const [toast, setToast] = useState(null);
  const [offline, setOffline] = useState(false);

  const refresh = useCallback(() => api("/api/state")
    .then((s) => { setState(s); setAuth("in"); setOffline(false); })
    .catch((e) => { if (e.status !== 401) setOffline(true); }), []);

  useEffect(() => {
    const out = () => { setAuth("out"); setState(null); };
    window.addEventListener("logged-out", out);
    return () => window.removeEventListener("logged-out", out);
  }, []);

  useEffect(() => {
    if (auth === "out") return undefined;
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [refresh, auth]);

  // Báo danh để server đếm người đang mở trang
  useEffect(() => {
    if (auth !== "in") return undefined;
    const ping = () => api("/api/ping", {}).catch(() => {});
    ping();
    const timer = setInterval(ping, 20000);
    return () => clearInterval(timer);
  }, [auth]);

  useEffect(() => {
    store.set("page", page);
    if (window.location.hash.slice(1) !== page) window.history.pushState(null, "", `#${page}`);
  }, [page]);
  useEffect(() => {
    const follow = () => { const h = window.location.hash.slice(1); if (PAGES[h]) setPage(h); };
    window.addEventListener("hashchange", follow);
    window.addEventListener("popstate", follow);
    return () => { window.removeEventListener("hashchange", follow); window.removeEventListener("popstate", follow); };
  }, []);

  const notify = (text, kind = "ok") => {
    setToast({ text, kind, id: Date.now() });
    setTimeout(() => setToast((t) => (t && Date.now() - t.id >= 4000 ? null : t)), 4200);
  };

  if (auth === "out") return <Login onLogin={() => { setAuth("checking"); refresh(); }} />;
  if (!state) {
    return <div className="splash">{offline ? "Không kết nối được server. Chạy: python web/app.py" : "Đang tải..."}</div>;
  }

  const me = state.me.name;
  const user = state.users.find((u) => u.name === me);
  const admin = state.me.role === "admin";
  const logout = () => api("/api/logout", {}).finally(() => { setAuth("out"); setState(null); });
  const ctx = { state, me, user, admin, refresh, notify, openVideo: setOpen, editUser: setEditing, goto: setPage };
  const pages = admin ? PAGES : Object.fromEntries(Object.entries(PAGES).filter(([k]) => k !== "settings"));
  const current = pages[page] ? page : "studio";

  return (
    <div className="layout">
      <Sidebar {...ctx} page={current} pages={pages} logout={logout} />
      <main className="content">
        {offline && <div className="banner">Mất kết nối tới server, đang thử lại...</div>}
        {state.stale && <div className="banner">Code server vừa được cập nhật nhưng server chưa khởi động lại: tắt cửa sổ "Shorts web" rồi chạy lại chay_web.bat (lựa chọn mới trên trang này chưa có tác dụng).</div>}
        <header className="page-head">
          <h1>{pages[current][0]}</h1>
          <p>{pages[current][1]}</p>
        </header>
        {current === "studio" && <Studio {...ctx} />}
        {current === "skits" && <Skits {...ctx} />}
        {current === "library" && <Library {...ctx} />}
        {current === "activity" && <Activity {...ctx} />}
        {current === "members" && <Members {...ctx} />}
        {current === "settings" && <Settings {...ctx} />}
        {current === "feedback" && <FeedbackPage {...ctx} />}
      </main>

      {editing !== null && (
        <UserModal key={editing} user={state.users.find((u) => u.name === editing)} me={me} admin={admin}
          bot={state.settings.telegram_bot_username}
          onClose={() => setEditing(null)}
          onSaved={(text) => { setEditing(null); notify(text); refresh(); }} />
      )}
      {open && state.videos.some((v) => v.name === open) && (
        <VideoModal {...ctx} video={state.videos.find((v) => v.name === open)} onClose={() => setOpen(null)} />
      )}
      <ConfirmHost />
      {toast && <div className={`toast ${toast.kind}`} key={toast.id}>{toast.text}</div>}
    </div>
  );
}
