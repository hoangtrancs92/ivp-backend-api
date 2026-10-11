import { Avatar, Logo, QuotaBar } from "./common.jsx";
import Icon from "./Icon.jsx";

const ICONS = { studio: "sparkles", skits: "film", library: "grid", activity: "activity", members: "users", feedback: "message", settings: "settings" };

export default function Sidebar({ state, me, user, admin, page, pages, goto, editUser, logout }) {
  // Tạo video và Tiểu phẩm độc lập: mỗi mục chỉ đếm việc của mình
  const running = state.runs.filter((r) => r.status === "running" && r.action !== "skit").length
    + state.videos.filter((v) => v.review && (admin || v.owner === me)).length;
  const skitsRunning = (state.skits || []).filter((s) => s.run?.status === "running").length;
  const openFeedback = state.feedback.filter((f) => !f.parent && !f.resolved).length;
  return (
    <aside className="sidebar">
      <div className="brand">
        <Logo />
        <div><b>Shorts Studio</b><span>Irasutoya pipeline</span></div>
      </div>

      <nav>
        {Object.entries(pages).map(([key, [label]]) => (
          <button key={key} className={page === key ? "active" : ""} onClick={() => goto(key)}>
            <span className="nav-icon"><Icon name={ICONS[key]} size={18} /></span>{label}
            {key === "studio" && running > 0 && <span className="pill">{running}</span>}
            {key === "skits" && skitsRunning > 0 && <span className="pill">{skitsRunning}</span>}
            {key === "feedback" && openFeedback > 0 && <span className="pill">{openFeedback}</span>}
          </button>
        ))}
      </nav>

      <div className="side-stats">
        <div><b>{state.stats.online}</b><span>đang online</span></div>
        <div><b>{state.stats.users}</b><span>thành viên</span></div>
        <div><b>{state.stats.videos}</b><span>video xong</span></div>
      </div>

      <div className="me-card">
        <div className="me-row">
          <Avatar name={me} size={36} online />
          <div className="me-name">
            <b>{me}</b>
            <span className={`role ${admin ? "admin" : ""}`}>{admin ? "Admin" : "Thành viên"}</span>
          </div>
          <button className="icon-btn light" title="Đăng xuất" aria-label="Đăng xuất" onClick={logout}><Icon name="logout" size={17} /></button>
        </div>
        {user && <QuotaBar quota={user.quota} compact />}
        <button className="link" onClick={() => editUser(me)}>Hồ sơ, khóa API, mật khẩu</button>
      </div>
    </aside>
  );
}
