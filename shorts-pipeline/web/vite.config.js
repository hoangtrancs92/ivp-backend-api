import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// npm run dev: giao diện ở http://localhost:5173, gọi API của web/app.py (cổng 8000)
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000", "/videos": "http://127.0.0.1:8000" } },
});
