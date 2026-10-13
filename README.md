# Video generation pipeline

Source chính nằm trong [`shorts-pipeline`](shorts-pipeline/README.md).

## Chạy trên máy Windows mới

Cài Python 3.12, Node.js 22.12 trở lên và FFmpeg (gồm cả `ffmpeg` và `ffprobe`, thêm vào PATH), sau đó mở PowerShell:

```powershell
git clone https://github.com/hoangtrancs92/ivp-backend-api.git
cd ivp-backend-api/shorts-pipeline
$env:PYTHONUTF8 = '1'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.toml config.toml
cd web
npm.cmd ci
npm.cmd run build
cd ..
.\.venv\Scripts\python.exe web/app.py
```

Mở http://127.0.0.1:8000. Điền tài khoản và khóa của bạn trong `config.toml` hoặc hồ sơ người dùng trên web. Có thể tạo tài khoản quản trị bằng `.\.venv\Scripts\python.exe web/app.py --add-user <ten> <mat-khau> --admin`.

Để sinh ảnh, cần tài khoản Kaggle có GPU, token Hugging Face có quyền tải model và dataset LoRA cấu hình trong `config.toml`. Đăng nhập Kaggle bằng `.\.venv\Scripts\kaggle.exe auth login`, rồi kiểm tra dataset bằng `.\.venv\Scripts\kaggle.exe datasets list --mine`. Xem hướng dẫn pipeline để thiết lập LoRA.

Git không chứa khóa API, tài khoản web trong `data/`, môi trường Python, model, nhạc tải ngoài và kết quả video. Khi chuyển máy, tự cấu hình lại khóa; chép riêng dữ liệu và tài nguyên bị bỏ qua nếu muốn tiếp tục các video đã làm. Ảnh thiếu có thể sinh lại qua `tools/make_jobs.py` và `tools/run_kaggle.py`. Công cụ tải nhạc/hiệu ứng nằm trong `tools/fetch_bgm.py` và `tools/fetch_sfx.py`.
