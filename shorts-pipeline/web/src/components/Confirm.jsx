import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";

// Hộp xác nhận thay cho confirm() của trình duyệt.
// Dùng: if (!(await ask({ title, message, details, confirmText, tone: "danger" }))) return;
let open = null;
export const ask = (options) => new Promise((resolve) => open?.({ ...options, resolve }));

const TONES = {
  danger: { icon: "trash", confirmClass: "danger" },
  warn: { icon: "stop", confirmClass: "danger" },
  info: { icon: "upload", confirmClass: "primary" },
};

export default function ConfirmHost() {
  const [dialog, setDialog] = useState(null);
  const confirmBtn = useRef(null);

  useEffect(() => {
    open = setDialog;
    return () => { open = null; };
  }, []);

  useEffect(() => {
    if (!dialog) return undefined;
    confirmBtn.current?.focus();
    const key = (e) => { if (e.key === "Escape") close(false); };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });

  if (!dialog) return null;
  const tone = TONES[dialog.tone || "info"];
  function close(value) {
    dialog.resolve(value);
    setDialog(null);
  }

  return (
    <div className="overlay confirm-overlay" onMouseDown={(e) => e.target === e.currentTarget && close(false)}>
      <div className="confirm" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <div className={`confirm-icon ${dialog.tone || "info"}`}><Icon name={tone.icon} size={22} /></div>
        <h2 id="confirm-title">{dialog.title}</h2>
        {dialog.subject && <div className="confirm-subject">{dialog.subject}</div>}
        {dialog.message && <p>{dialog.message}</p>}
        {dialog.details && (
          <ul className="confirm-details">{dialog.details.map((d) => <li key={d}>{d}</li>)}</ul>
        )}
        <div className="confirm-actions">
          <button className="ghost" onClick={() => close(false)}>{dialog.cancelText || "Hủy"}</button>
          <button ref={confirmBtn} className={tone.confirmClass} onClick={() => close(true)}>{dialog.confirmText || "Đồng ý"}</button>
        </div>
      </div>
    </div>
  );
}
