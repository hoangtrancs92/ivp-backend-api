import { useState } from "react";
import { api } from "../api.js";
import { Logo } from "./common.jsx";

export default function Login({ onLogin }) {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/login", { name: name.trim(), password });
      onLogin();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={submit}>
        <div className="brand dark">
          <Logo />
          <div><b>Shorts Studio</b><span>Irasutoya pipeline</span></div>
        </div>
        <h1>Đăng nhập</h1>
        <p className="muted">Mỗi thành viên dùng tài khoản riêng để biết ai đang làm gì.</p>
        <label>Tên đăng nhập
          <input value={name} onChange={(e) => setName(e.target.value)} autoFocus autoComplete="username" />
        </label>
        <label>Mật khẩu
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
        </label>
        {error && <p className="note bad">{error}</p>}
        <button className="primary big" disabled={busy || !name.trim() || !password}>{busy ? "Đang vào..." : "Đăng nhập"}</button>
      </form>
    </div>
  );
}
