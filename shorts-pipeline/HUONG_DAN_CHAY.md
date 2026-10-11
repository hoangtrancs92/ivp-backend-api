# Hướng dẫn chạy trang web làm video (mỗi lần bật máy)

## Cách nhanh: bấm đúp `chay_web.bat`

File nằm ở `D:\videoprogenai\shorts-pipeline\chay_web.bat`. Bấm đúp là mở 2 cửa sổ đen:

| Cửa sổ | Là gì | Thấy gì là chạy được |
|---|---|---|
| **Shorts web** | server trang web | `Mở http://127.0.0.1:8000` |
| **Cloudflare** | đường hầm cho máy khác vào | một dòng có link `https://<chữ-ngẫu-nhiên>.trycloudflare.com` |

**Đừng tắt hai cửa sổ này** khi còn dùng trang. Tắt cửa sổ "Shorts web" là tắt trang web.

File .bat cũng bật **VOICEVOX** (giọng đọc nhân vật) chạy nền, thu nhỏ dưới thanh tác vụ. Quên bật cũng không sao: bước giọng
đọc tự bật VOICEVOX khi cần. Khi đăng video có giọng VOICEVOX, chép dòng "VOICEVOX:..." ở cửa sổ video vào phần mô tả.

## Lấy link Cloudflare

1. Nhìn cửa sổ **Cloudflare**, tìm khung có dòng dạng:
   ```
   Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):
   https://naval-rehab-returning-displaying.trycloudflare.com
   ```
2. Chép link đó, gửi cho mọi người (tustruyen, phuctran, phuctran2...). Link mở được trên điện thoại, máy khác.
3. **Link đổi mỗi lần chạy lại Cloudflare**, nên mỗi ngày phải gửi lại link mới.
4. (Tùy chọn) Đăng nhập admin → **Cài đặt** → mục Thông báo Telegram → ô **Địa chỉ trang web**: dán link mới, bấm Lưu,
   để tin nhắn Telegram có link bấm vào được.

Link mới tạo đôi khi cần 10-30 giây mới vào được. Báo lỗi 1033 / 530 thì chờ chút rồi tải lại.

## Chạy tay (khi không dùng file .bat)

Mở 2 cửa sổ PowerShell:

```powershell
# Cửa sổ 1: server
cd D:\videoprogenai\shorts-pipeline
$env:PYTHONUTF8 = "1"
python web\app.py --host 0.0.0.0
```

```powershell
# Cửa sổ 2: Cloudflare
& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --no-autoupdate --url http://127.0.0.1:8000
```

- Chỉ dùng trên máy này: mở `http://127.0.0.1:8000`, không cần Cloudflare.
- Máy khác cùng mạng wifi: `http://<IP máy này>:8000` (xem IP bằng lệnh `ipconfig`, dòng IPv4).

## Tài khoản

| Tên | Quyền | Kaggle |
|---|---|---|
| nickytiktok | admin | tranhoang1124 |
| tustruyen | thành viên | miracle156 |
| phuctran | thành viên | localhost0000 |
| phuctran2 | thành viên | kienchi2210 |

Mật khẩu ban đầu đều là `123456`: nên đổi trong **Hồ sơ**.

## Khi tắt máy giữa chừng

- Video đang **vẽ ảnh trên Kaggle** vẫn chạy tiếp trên Kaggle dù máy tắt. Hôm sau bấm **"↻ Chạy tiếp"**: máy kiểm tra
  Kaggle, có ảnh rồi thì tải về luôn, không vẽ lại.
- Video đang **dựng / tách nền / giọng đọc** (chạy trên máy) bị ngắt, trạng thái "Bị ngắt". Bấm **"↻ Chạy tiếp"** để làm
  nốt; phần đã xong được giữ.
- Video đang **sửa cảnh bằng AI** bị ngắt thì bấm lại "Sửa cảnh lỗi".

## Gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| Cửa sổ "Shorts web" báo `address already in use` / port 8000 | Đã có một server đang chạy (cửa sổ cũ chưa tắt). Tắt cửa sổ cũ hoặc dùng luôn nó. |
| Cửa sổ Cloudflare báo lỗi, không có link | Tắt cửa sổ đó, chạy lại dòng lệnh Cloudflare ở trên. Kiểm tra mạng. |
| Trang hiện giao diện cũ / thiếu nút mới | Tải lại trang (F5, hoặc Ctrl+F5). |
| `python` không chạy | Dùng đường dẫn đầy đủ: `C:\Users\Tran Hoang\AppData\Local\Programs\Python\Python312\python.exe` |
| AI duyệt ảnh lỗi "No available channel for model ..." | ShopAIKey tạm hết model đó: **Cài đặt** → đổi model duyệt ảnh (vd `claude-opus-5-5`). |
| Xem Kaggle đang làm gì | Mở video → tab **📜 Nhật ký** → **☁️ Log Kaggle**. |

Lịch sử các thay đổi: `docs/CHANGELOG.md`.
