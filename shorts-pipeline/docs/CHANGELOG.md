# Lịch sử thay đổi

Mỗi mục: ngày, thay đổi gì, vì sao, và kết quả kiểm tra. Mục mới nhất ở trên.
Quyết định đang có hiệu lực được tóm tắt ở bảng "Quyết định đã chốt" trong `README.md`.

## 2026-10-08: sửa cảnh có xem trước (Dùng / Vẽ lại / Bỏ)

Người dùng: xem trước bản AI sửa, chưa ưng thì cho AI vẽ lại. `tools/fix_scenes.py` tách 2 bước:
- `--edit`: AI vẽ bản sửa vào `work/fix/<ảnh>` (+ `state.json`: cảnh, ghi chú, số lần vẽ), không đụng ảnh của video; thoát
  mã 3 (chờ người xem, Telegram báo "chờ duyệt"). Nhận `{"scenes": {...}}` (lần đầu) hoặc `{"images": {...}}` (vẽ lại ảnh).
- `--apply`: thay ảnh được chọn vào characters/ (ảnh cũ vào rejected/fix_<giờ>/), bỏ bản sửa còn lại, tách nền, dựng lại.
- Web: `/api/fix` (cảnh hoặc ảnh), `/api/fix/apply` (không chọn ảnh nào = bỏ hết, không dựng lại); `fix_review` trong thông
  tin video. `FixReview.jsx`: ảnh cũ → ảnh mới từng ảnh (bấm xem to), chọn ✓ Dùng / ↻ Vẽ lại (sửa ghi chú) / ✕ Bỏ; nút
  "Vẽ lại N ảnh" và "Áp dụng N ảnh và dựng lại". Tab đổi tên "✨ Xem ảnh sửa (N)"; thư viện hiện "✨ Chờ xem ảnh sửa".

## 2026-10-08: hiện rõ video đang được sửa cảnh

Thẻ "Đang chạy" của video đang sửa cảnh chỉ hiện tiêu đề và "(không có đề tài)", không biết đang làm gì.
- `tools/fix_scenes.py` ghi `work/fix_progress.json`: các cảnh đang sửa, AI sửa k/n ảnh, bước (ai / cutouts / preview / build).
- `web/app.py: fix_info` gửi kèm thông tin video khi lần chạy cuối là việc "fix" đang chạy (file cũ hoặc chưa có: chỉ báo đang sửa).
- Giao diện (`FixProgress`): nhãn "✨ Đang sửa N cảnh" (gradient, nhấp nháy nhẹ), danh sách cảnh, 4 bước AI sửa ảnh k/n → Tách nền
  → Bố cục cảnh → Dựng video, thanh tiến trình; dùng ở thẻ Đang chạy và cửa sổ video; thư viện hiện nhãn "✨ Đang sửa cảnh".

## 2026-10-08: kernel không còn vẽ lại cả lô cũ khi chỉ gửi vài ảnh

Video 014: AI chấm 4 ảnh người duyệt chọn, 3 ảnh cần vẽ lại, máy gửi lô 3 ảnh (kernel version 10); log Kaggle lại ghi
"Đã mã hóa 97 prompt": kernel gắn phiên bản CŨ của dataset `shorts-job` (lô 97 ảnh trước đó) vì `datasets status` báo
"ready" ngay sau khi tải lên (trạng thái của bản cũ) và máy gửi kernel luôn. Không phải do AI chấm lại hết.
- `tools/run_kaggle.py`: mỗi lô có mã (`spec["batch"]`) và file `batch_<mã>.txt` trong dataset; chờ tới khi
  `kaggle datasets files` có đúng file đó (tối đa 15 phút) rồi mới gửi kernel.
- `kaggle_job/kernel_main.py`: mã lô được ghi vào code kernel khi gửi; jobs.json khác mã thì in `STALE_BATCH` và dừng
  ngay (trước khi cài thư viện). Máy thấy `STALE_BATCH` trong log thì chờ 60 giây, gửi lại (tối đa 3 lần).
Kiểm tra: phần so mã lô chạy riêng với jobs.json đúng / sai mã (tiếp tục / dừng); `kaggle datasets files` liệt kê tên file.
Chưa chạy một lô thật với code mới.

## 2026-10-08: xem log Kaggle đang chạy; tiến trình Kaggle đếm đúng

`kaggle kernels logs` chỉ trả log khi kernel đã xong (đang chạy thì rỗng), nên thanh tiến trình Kaggle luôn hiện "0/N ảnh"
và không xem được kernel đang làm gì. `tools/kaggle_live.py`: mở luồng GetKernelSessionLogsStream của kagglesdk
(text/event-stream, phát lại log từ đầu), đọc ~8 giây rồi đóng, chạy bằng subprocess với tài khoản của từng người.
- `tools/run_kaggle.py: report()` đọc log bằng cách này: tiến trình đếm thật (thử với 016: 33/69 ảnh, trước đó 0/69).
  Việc đang chạy từ trước vẫn dùng code cũ đến lô sau.
- Trang web, tab Nhật ký: chọn "🖥 Log máy" / "☁️ Log Kaggle". Log Kaggle lấy trực tiếp từ kernel của chủ video (đang chạy:
  luồng log; đã xong: `kernels logs`), 30 giây tự làm mới, server nhớ kết quả 20 giây; báo nếu kernel đang chạy cho video khác.
Kiểm tra: API /api/kaggle_log với 014 (tài khoản kienchi2210): đang vẽ ảnh bình thường (bg_mood_warm_memory xong).

## 2026-10-08: sửa cảnh lỗi của video đã xong bằng model ảnh (không Kaggle)

Người dùng: video xong rồi vẫn có cảnh hình dị dạng; muốn chọn cảnh, AI đổi hình khác giống ~90%, rồi xuất lại video.
- Video đã xong có nút "🛠 Sửa cảnh lỗi" (`web/src/components/FixPanel.jsx`): lưới ảnh bố cục từng cảnh (work/preview),
  chọn cảnh, ghi chú chỗ lỗi (tùy chọn), bấm "Sửa N cảnh và dựng lại". Tối đa 15 cảnh một lần.
- `tools/fix_scenes.py` (việc "fix" của web, khóa AI của chủ video): mỗi ảnh characters/NNN*.png của cảnh gửi model ảnh
  (`steps/llm.py: edit_image`, chat/completions có ảnh vào, ảnh ra dạng data URL) với lời dặn: chỉ sửa tay / chân / đồ vật
  méo, giữ nguyên nhân vật, quần áo, tư thế, đồ đang cầm, nét Irasutoya, nền chroma. Ghi chú tiếng Việt dịch sang tiếng Anh.
  Ảnh cũ vào rejected/fix_<giờ>/, tách nền lại, cập nhật dấu duyệt, dựng lại (bản cũ: work/output_truoc_sua.mp4).
- Cài đặt: "Sửa ảnh lỗi" chọn model (mặc định gemini-2.5-flash-image; cổng có gemini-3-pro-image-preview, gpt-image-1...).
- Việc không dùng Kaggle (fix) không còn phải chờ tài khoản Kaggle rảnh.
- Chọn cảnh: "📍 Chọn cảnh đang xem" (dừng video ở chỗ lỗi rồi bấm), mốc giờ ▶ trên từng cảnh để nhảy tới xem;
  giờ từng cảnh lấy từ `work/timings.json` (build_video.py ghi từ nay) hoặc phụ đề `work/build/subs.ass` (video cũ).
- Lưới cảnh cuộn trong khung ~3 hàng; danh sách "Cảnh đã chọn" có ô ghi chú cho AI (tối đa 600 ký tự). Câu lệnh sửa ảnh
  kèm `action`, `emotion` của cảnh trong kịch bản và ghi chú đã dịch sang tiếng Anh.
- Khởi động lại server chỉ tắt tiến trình server (không tắt cây tiến trình): việc đang chạy được gắn lại theo pid.
Kiểm tra: chạy trọn tools/fix_scenes.py trên bản sao 015 (cảnh 2): sửa ảnh, tách nền, dựng lại 105,9 giây, không lỗi.
Lỗi thật của ảnh là một cánh tay có hai bàn tay; model bỏ bàn tay thừa cầm lon. Thử lời dặn "không được bỏ đồ vật" thì ra
nắm tay lơ lửng, nên lời dặn nay yêu cầu đúng giải phẫu, bỏ tay thừa, giữ đồ vật khi cầm được tự nhiên.
Kiểm tra đầu tiên: gọi thật gemini-2.5-flash-image với ảnh cảnh 2 video 015 (tay cầm lon lỗi): ra ảnh gần như giống hệt, tay tự nhiên,
nền xanh giữ nguyên, nhưng bỏ mất lon bia (lời dặn nay ghi giữ đồ đang cầm).

## 2026-10-08: câu chỉ có dấu câu thì im lặng, không lỗi giọng đọc

Video 012 dừng ở bước giọng đọc: cảnh 57 có lời `……。`; `clean()` bỏ `…` còn `。`, edge-tts báo `NoAudioReceived`.
`steps/06_voice.py`: câu không có chữ đọc được thì tạo khoảng lặng 0,5 giây (1,2 giây người dùng thấy quá lâu); script_guide.md cấm câu chỉ có dấu câu, để lời kể nói thay; edge-tts lỗi `NoAudioReceived` thì thử lại
tối đa 3 lần. Kiểm tra: `speakable()` đúng với `……。`, `…！？`, `「……」` (im lặng) và câu thường, `5年後`, `え？` (đọc).

## 2026-10-08: Chạy tiếp không vẽ lại ảnh Kaggle đã vẽ xong

Video 015 (bị ngắt) và 012 (bị dừng): Kaggle đã vẽ đủ 120/120 và 116/116 ảnh nhưng chưa tải về; bấm Chạy tiếp sẽ gửi lô mới
vẽ lại từ đầu. `tools/run_kaggle.py`: mỗi lần gửi ghi `build/<tài khoản>/last_run.json` (video, tên ảnh, đã tải chưa).
Trước khi gửi lô mới, `resume()`: kernel còn chạy thì chờ xong; kernel đã xong và kết quả có ảnh của video này (có dấu
lần gửi của video này, hoặc không có dấu nhưng khớp >= 80% ảnh cần sinh) thì tải về và bỏ qua lô mới. Kết quả đã tải
rồi (ảnh còn thiếu là ảnh lỗi / bị loại khi duyệt) thì vẫn gửi lô mới như cũ. Kernel đang chạy cho video khác: dừng, báo.
Kiểm tra: 6 tình huống với Kaggle giả (xong đủ ảnh, đã tải, đang chạy rồi xong, khớp ít, kernel lỗi, video khác).
Sửa ngay sau đó: lần chạy thật với 015 vẫn gửi lô mới (kernel version 18) vì liệt kê file dùng `--page-size 1000` (Kaggle
tối đa 200) nên đọc được 0 ảnh. Nay đọc theo trang 200; kiểm tra thật: đọc đủ 120 ảnh. Ảnh 015 (version 17) và 012
(version 11) tải về bằng `build/_tools/fetch_version.py` (tải từng file theo số version, chạy được khi kernel đang chạy
bản mới hơn): 015 chép 118 ảnh, 012 chép 116 ảnh.

## 2026-10-08: thông báo Telegram (tùy chọn)

- Admin nhập token bot (tạo qua @BotFather) và địa chỉ trang web ở trang Cài đặt; token không gửi về trình duyệt.
- Mỗi người nhập chat ID ở Hồ sơ ("Tìm chat ID" đọc getUpdates của bot, "Gửi thử"), chọn báo: xong + lỗi + chờ duyệt /
  chỉ lỗi / tắt.
- `web/app.py`: `finish_run` gửi tin cho chủ video và người bấm chạy (nếu khác): tiêu đề, thư mục, thời gian chạy;
  khi lỗi kèm 6 dòng cuối của log. Gửi lỗi thì chỉ ghi ra console, không làm hỏng việc chạy.
Kiểm tra: gọi Telegram thật với token sai báo "Unauthorized (token bot sai)"; xem trước tin nhắn của lần lỗi video 014
(gửi giả). Chưa gửi tin thật vì chưa có token bot.

## 2026-10-08: tự đưa LoRA lên tài khoản Kaggle mới

Video 014 (người dùng phuctran2, Kaggle kienchi2210) chạy 3 lượt ra 0/97 ảnh: kernel báo `not valid dataset sources:
['kienchi2210/irasutoya-style-lora']` vì tài khoản mới chưa bấm "Đưa LoRA lên Kaggle". `tools/run_kaggle.py`: trước khi đẩy
kernel, kiểm tra dataset LoRA; chưa có thì tự đưa `loras/style.safetensors` lên và chờ sẵn sàng (tối đa 15 phút). Kernel
vẫn báo thiếu dataset thì dừng ngay với thông báo rõ (trước đây chờ hết lượt rồi báo "thiếu 91 ảnh").

## 2026-10-08: độ dài 80-100 giây

Người dùng: 80-100 giây là đủ. Video 003 (58 cảnh, ~700 ký tự) ra 114 giây, nên `script_guide.md`: 50-60 cảnh, 550-700 ký tự,
nấc 12-18 cảnh. `01_script.py`: viết thêm khi dưới 45 cảnh hoặc dưới 80 giây; ước quá 105 giây thì cảnh báo.

## 2026-10-08: tiêu đề tự co cho vừa khung

Tiêu đề dài (vd 「スマホから顔を上げない男」) tràn ra ngoài khung. `build_video.py`: `title_sizes()` đo từng dòng bằng chính
font (quy đổi cỡ ASS = chiều cao dòng, không phải em), dòng 2 nhỏ hơn dòng 1 (x0,8), dòng dài tự co cho vừa bề ngang trừ
lề 40 px, tổng cao không vượt dải đen; mỗi dòng ghi `\fs` và `\bord` riêng. `settings.toml`: `title_size` 128 → 190,
`title_band` 330 → 380, `subtitle_top` 360 → 410 (tiêu đề to gần kín bề ngang như video mẫu 感動の迷言集).
Kiểm tra: dựng thử khung hình 3 tiêu đề (満員電車で/スマホから顔を上げない男, 感動の迷言集/七歳の手, 父の財布にあった/
知らない女の子の写真): cỡ 190/113, 190/152, 168/135, không dòng nào chạm mép.

## 2026-10-08: cảm xúc có hiệu ứng hình + tiếng, tiếng to hơn

Người dùng: video phải cuốn hút, bất ngờ thì có tiếng và hiệu ứng, cảm xúc nào cũng nên có effect, tiếng to hơn chút.
- `variety.py`: `EMOTION_FX` + `add_reaction()`: cảnh có `emotion` mạnh (11 nhóm: bất ngờ, tuyệt vọng, khóc, giận, sợ,
  đắc ý, vui, yêu, lúng túng, khó hiểu, buồn) mà kịch bản chưa đặt hiệu ứng / sticker / chữ thì tự gắn gói (vd bất ngờ:
  集中線 sau nhân vật + sticker ！ + `punch_in`; đắc ý: tia sáng + lấp lánh + `punch_in`). Không gắn cùng gói 2 cảnh liền.
  Khớp đầu từ, nhiều từ đồng nghĩa (aghast, startled, frightened...; "sobering" không còn khớp "sob").
- `build_video.py`: cảnh cảm xúc mạnh luôn được gắn tiếng (bỏ qua ngân sách và luật "cảnh trước vừa kêu");
  `SFX_SHARE` 0,15 → 0,3, mỗi tiếng tối đa 4 lần (whoosh 3); trần đỉnh 0,5 → 0,75 đỉnh giọng.
- `settings.toml`: `sfx_below_voice` 12 → 7 dB.
- `script_guide.md`: bảng emotion → gói phản ứng để model ghi đúng từ; bỏ đoạn "dùng ít".
Kiểm tra: chạy `variety.fill` + `sfx_events` trên kịch bản 009 (không dựng): `check()` không lỗi; 21/40 cảnh có tiếng
(trước ~7), các cảnh cảm xúc gần như đều có. Chưa nghe thử độ to mới.

## 2026-10-08: video dài 1 phút 20 đến 2 phút

Video cũ dưới 1 phút (30-40 cảnh). Giữ nguyên tốc độ đọc (1,2x) và nhịp 1-1,5 giây mỗi cảnh, tăng số cảnh:
- `config/script_guide.md`: 60-75 cảnh, 80-120 giây, tổng lời 650-950 ký tự; truyện 3-4 nấc; tách câu dài thành nhiều cảnh
  hình khác nhau; ít nhất 6 bối cảnh (tối đa 30% số cảnh một bối cảnh); cứ ~10 cảnh có 1 cảnh nhiều lớp hiệu ứng.
- `steps/01_script.py`: đếm cảnh và ký tự, ước số giây (8 ký tự/giây + 0,35 giây mỗi cảnh). Dưới 55 cảnh hoặc dưới 80 giây
  thì gửi lại bản cũ, nhờ model viết dài thêm (tối đa 2 lần, giữ bản dài nhất).
- Hệ quả: số ảnh mỗi video gần gấp đôi, thời gian Kaggle tăng tương ứng.
Chưa chạy thử với model thật (lệnh chạy bị chặn lúc sửa); hệ số 8 ký tự/giây là ước lượng, cần đối chiếu với video đầu tiên.

## 2026-10-08: làm theo phân tích video mẫu (950万再生 缶チューハイと絆, 愛彼女弁当)

Video mẫu 1 (56 giây, ~27 lần đổi hình): truyện kiểu 2ch感動スレ, hình Irasutoya thật, nhiều cảnh 2-3 nhân vật, nền cảm xúc,
dải đen tiêu đề chữ vàng, phụ đề chữ màu viền trắng, nhạc nền liên tục, gần như không hiệu ứng âm thanh. Video mẫu 2 (愛彼女弁当,
12 giây, đổi hình ~1 giây): nhạc hài nhịp nhanh khá to, tắt bặt ~0,6 giây đúng câu chốt "う〜ん味がしねぇ！" và ở mở đầu.
1. **Nhạc nền**: `tools/fetch_bgm.py` tải 24 bài (6 nhóm しみじみ, 悲しい, コミカル, 怪しい, ほのぼの, シリアス × 4) từ
   甘茶の音楽工房 (dùng thương mại được, không cần ghi nguồn; cấm phát tán lại, cấm Content ID; `library/bgm/` vào `.gitignore`).
   `build_video.py` chọn nhóm theo `genre` (hoặc `"bgm"`), mỗi video một bài cố định; đo độ to, nhạc nhỏ hơn giọng 18 dB (hài 11,
   ấm áp 15), mờ vào 1,5 giây, mờ ra 2,5 giây; tắt nhạc 0,7 giây ở đầu cảnh chốt (vào twist, shake / flash, `"music_stop": true`),
   tối đa 4 lần. `music.mp3` riêng của video vẫn được ưu tiên.
2. **Bố cục chữ**: dải đen trên cùng (`title_band` 330px) với tiêu đề chữ vàng viền nâu cỡ 128; phụ đề cỡ 144 → 122 (2 dòng ~8 chữ),
   chữ màu viền trắng dày: lời kể xanh dương (`narration_colour`), lời thoại màu nhân vật làm đậm; `subtitle_top` 360.
3. **Nhiều nhân vật trong khung**: `script_guide.md` yêu cầu ~1/3 số cảnh có 2-3 người, mỗi người hướng về người kia.
4. **Mẫu 2ch感動スレ** trong `script_guide.md` mục 0 (ngôi thứ nhất, mâu thuẫn 2 giây đầu, bí mật hé lộ + hồi tưởng, việc tử tế,
   nhảy thời gian, đồ vật biểu tượng, tiêu đề tên series + nội dung).
5. **Nền cảm xúc**: 8 bối cảnh `mood_*` trong `locations.json` (xoáy tối, đồng hồ nhảy thời gian, hoa anh đào, kỷ niệm ấm, vui
   lấp lánh, sốc, mưa buồn, đêm sao); vẽ khi kịch bản đầu tiên dùng tới.
6. **Hiệu ứng âm thanh còn ít hơn**: ~15% số cảnh, mỗi tiếng tối đa 2 lần.
- Kiểm tra: dựng 009 có nhạc (シリアス theo thể loại スカッと) và bố cục mới, so cạnh video mẫu; bộ lọc tắt nhạc thử trên đoạn 6 giây
  (đoạn tắt -180 dB, trước / sau ~-31 dB). Không dựng lại 009 với khoảng lặng (người dùng dặn không cần).

## 2026-10-08: tự gửi lại khi Kaggle không khởi động được kernel; log gọn

- Video 010-tao-mot-video-ke-chuyen (tài khoản localhost0000): kernel báo error sau ~2 phút, log trống hoàn toàn (code chưa chạy
  dòng nào). Kiểm tra: còn 29,3 / 30 giờ GPU, dataset job và LoRA "ready", file LoRA đủ → lỗi khởi động phiên phía Kaggle.
- `run_kaggle.py`: kernel lỗi mà log trống (`kernel_never_ran`) thì đợi 30 giây rồi gửi lại, tối đa 2 lần; lỗi có log vẫn dừng như cũ.
- Log: các dòng "bỏ \"object\": null" (mỗi cảnh vài dòng) gộp thành một dòng tóm tắt (`common.summarize_changes`).

## 2026-10-08: hiệu ứng âm thanh luôn nhỏ hơn giọng nói

Người dùng: hiệu ứng quá to, phải nhỏ hơn tiếng nhân vật đang nói.
- Trước: nhân một hệ số cố định (`sfx_volume`), mà file tải về to nhỏ rất khác nhau (taiko to hơn ピコッ nhiều) nên có tiếng át giọng.
- Nay `build_video.py` đo độ to từng file (RMS phần có tiếng, bỏ đoạn im) và độ to giọng của chính cảnh đó, rồi chỉnh để hiệu ứng
  nhỏ hơn giọng `sfx_below_voice = 12` dB, đỉnh không quá một nửa đỉnh giọng; tiếng nền nhỏ hơn giọng `ambient_below_voice = 22`
  dB. `sfx_volume`, `ambient_volume` còn lại là hệ số nhân thêm (1.0), 0 để tắt.
- Đo: mọi tiếng thấp hơn giọng ≥ 12 dB, đỉnh thấp hơn đỉnh giọng ~6 dB; nền lớp học thấp hơn giọng ~25 dB. Dựng lại 009: đỉnh cả
  video -4,8 dB = đỉnh giọng.

## 2026-10-08: sửa theo video 009 (âm thanh dày, màu xanh lá, đồ vật giống ảnh thật)

- **Hiệu ứng âm thanh thưa lại** (video 009: 68 tiếng / 52 giây, 39/40 cảnh): mỗi cảnh 1 tiếng, cao trào (tiếng mạnh) 2; chữ tượng
  thanh không có tiếng hợp thì im lặng (bỏ mặc định ポン); sticker chỉ kêu khi có trong bảng; anim do variety.py tự chọn không kêu
  (chỉ punch / jump / spin_in ghi tay); cảnh trước vừa có tiếng thì cảnh sau chỉ kêu tiếng mạnh; không lặp một tiếng trong 3 cảnh
  liền; mỗi tiếng tối đa 3 lần một video (whoosh 5); tổng ~45% số cảnh, chia đều theo tiến độ video; `sfx_volume` 0.95 → 0.7.
  Video 009 còn 19 tiếng / 16 cảnh. Dựng lại 009 (không tốn GPU).
- **Màu xanh lá trùng nền tách**: `make_jobs.py key_for` chọn nền theo prompt: có từ chỉ màu xanh lá (green, mint, olive,
  emerald, lime, leaf, plant, grass...) → nền xanh dương; có cả xanh dương (blue, navy, cobalt, denim...) → hồng tím; còn lại xanh lá
  như cũ. `04_cutouts.py` vốn tự nhận màu nền ở viền; `despill` bỏ qua nền hai kênh (hồng tím). `script_guide.md`: tránh xanh lá
  cho trang phục, đồ vật.
- **Đồ vật giống ảnh thật** (thùng rác, cuốn sổ cảnh cận): mô tả quá chi tiết kiểu ảnh chụp ("worn ivory B5 notebook with cobalt
  blue cloth spine... crumpled sheets"). Câu lệnh `OBJECT` thêm "simple flat cartoon clip art illustration..., thick clean outlines,
  flat colors, minimal detail, not a photo, not realistic, not 3D, no texture"; `script_guide.md`: mô tả đồ vật 1 câu ~15 từ, không
  tả chất liệu, vết mòn, ánh sáng, "close-up". `review_guide.md`: tiêu chí ★ `style` (nét vẽ phẳng; giống ảnh chụp / 3D = 1-2) cho
  nhân vật, đồ vật, ảnh nền.
- Ảnh đã vẽ của 009 không đổi (muốn sửa thùng rác / sổ: chọn ảnh ở màn duyệt, Vẽ lại; prompt đồ vật mới sẽ áp dụng).

## 2026-10-08: chấm ảnh rộng tay hơn

Người dùng: quy tắc chấm cứng nhắc quá (018 chồng sổ vẫn bị loại vì mô tả ghi "three notebooks").
- `review_guide.md` viết lại theo tinh thần "chấm rộng tay": cảnh chỉ hiện 1-2 giây, chỉ coi là lỗi khi người xem lướt TikTok
  nhận ra ngay (trông như người khác, áo đổi hẳn màu, tay chân dị dạng, thêm người, vật quan trọng biến mất / một thành hai);
  phân vân thì cho qua. Mục "không bao giờ trừ điểm": nền xanh / trắng, chữ trong ảnh, số lượng trong một nhóm đồ vật.
  Thang: 3 = lệch nhưng chấp nhận được, 1-2 = sai rõ ai xem cũng thấy. `count` (đồ vật) bỏ ★, chỉ ghi chú.
- Model trả thêm `"redraw": true/false` (người xem có thấy ngay ảnh sai không). `review.py decide`: chỉ vẽ lại khi
  `redraw` true VÀ có tiêu chí ★ ≤ 2; `redraw` false thì đạt dù điểm thấp.
- Thử `decide`: đồ vật 2 + redraw false → đạt; nhân vật 2 + redraw true → vẽ lại; chỉ hành động 1 → đạt; chồng sổ count 2 → đạt.

## 2026-10-08: nới tiêu chí chấm: chữ trong ảnh, số lượng đồ vật thành nhóm

- Video 009: AI loại 005, 007 (sổ có chữ viết tay: "chữ Nhật giả, không đúng 消えろ, 臭い") và 018 (chồng sổ "4 quyển thay vì 3").
  Người dùng: chồng sổ lệch số là bình thường; quy tắc chữ phải sửa hẳn.
- `review_guide.md`: quy tắc **"Chữ trong ảnh: KHÔNG chấm"** ở đầu mục Nhân vật và Đồ vật (chữ giả, sai nét, sai nội dung kể cả
  khi mô tả ghi rõ chữ gì: không trừ điểm, không ghi vào problems; chỉ trừ logo thương hiệu / chữ to lạ). Số lượng: chỉ đếm khi
  con số có ý nghĩa trong truyện; đồ vật thành nhóm (chồng sách, xấp giấy, tiền xu, bó hoa) lệch vài cái là bình thường.
- Lượt 2 video 009 AI vẫn loại 018 vì mô tả ghi "three school notebooks" (coi con số là quan trọng). Siết lại quy tắc: chỉ bắt vật đơn lẻ bị nhân đôi và cặp sai số; nhóm từ 3 vật trở lên không đếm kể cả khi mô tả ghi số.
- Thời gian một lượt Kaggle vẽ lại 2 ảnh: ~8 phút (khởi động máy + nạp model ~6 phút, ~1 phút / ảnh).
- `review.py`: nội dung trong 「」 / ngoặc kép bị thay bằng "(chữ, không chấm)" trước khi gửi mô tả cho model chấm.
- Video 009: trả 005, 007, 018 về characters/ trong lúc lượt chấm đang chạy (chưa gửi Kaggle), không vẽ lại.

## 2026-10-08: vẽ lại có sửa prompt (câu sửa của AI, ghi chú người duyệt)

Trước: vẽ lại chỉ đổi seed, giữ nguyên prompt (vẫn có LoRA, vẫn tham chiếu ảnh chuẩn), nên lỗi do prompt (vd đồ vật nhân đôi)
dễ lặp lại.
- `review_guide.md` / `review.py`: khi một tiêu chí bắt buộc trượt, AI trả thêm `fix`: cụm tiếng Anh tả đúng điều cần có
  (vd "holding exactly one grey cap in his right hand, no hat on his head"), lưu ở `review/images.json`.
- Màn duyệt ảnh: ô **ghi chú khi vẽ lại** trong chế độ xem lớn (tiếng Việt được; gõ ghi chú thì tự chọn ảnh), gửi kèm khi bấm
  Vẽ lại / AI kiểm tra, lưu `review/notes.json` (ai ghi, lúc nào); thẻ ảnh có ghi chú hiện dấu ✎.
- `make_jobs.py corrections`: ảnh đang vẽ lại thì ghép `fix` của AI + ghi chú (dịch sang tiếng Anh bằng model AI, lưu bản dịch;
  dịch lỗi thì dùng nguyên văn và lần sau dịch lại) vào prompt, đặt ngay sau từ khóa phong cách (đầu prompt được coi trọng hơn).
  Job ghi thêm trường `fix`; ảnh tải về có `work/kaggle/out/<tên>.json` ghi prompt, seed đã dùng.
- Kiểm tra: make_jobs trên bản sao video thử: ảnh 003 có fix của AI, ảnh 005 có ghi chú tiếng Việt được dịch (server AI giả)
  thành "holding exactly one cap in his right hand, no hat on his head" ở đầu prompt; seed mới 2030 / 2050.

## 2026-10-08: việc của video luôn chạy bằng khóa của chủ video; chữ trong ảnh

- `web/app.py runner_for`: "Chạy tiếp", duyệt ảnh (làm tiếp, AI kiểm tra, vẽ lại, để AI duyệt hết) trên video của người khác
  chạy bằng tài khoản chủ video (khóa Kaggle, HF, AI, giờ GPU), kể cả khi admin bấm; trước đó "Chạy tiếp" dùng khóa người bấm.
  Chủ video thiếu khóa thì báo rõ, không dùng khóa admin. Lịch sử chạy ghi `by` (người bấm), trang Hoạt động hiện "bấm bởi".
  Lần chạy video 010 đang chạy (bấm trước khi sửa) vẫn dùng tài khoản nickytiktok.
- Server khởi động lại đã gắn lại 2 việc đang chạy (009, 010) theo pid: tính năng gắn lại chạy đúng.
- Chấm ảnh với model thật (video 009, gpt-5.6-luna): ảnh 004 trước bị loại vì nền xanh nay đạt 4.3; AI ghi nhận lệch kiểu tóc so
  với ảnh chuẩn. Ảnh 005 (cuốn sổ có chữ) trượt vì chữ Nhật giả: model ảnh không viết được chữ đúng. Thêm quy tắc
  `script_guide.md` (đồ vật có chữ chỉ tả "with handwritten lines", nội dung chữ để lớp chữ / phụ đề) và `review_guide.md`
  (chữ nhỏ trên đồ vật không đọc được không trừ điểm).

## 2026-10-08: cách AI chấm ảnh mới

- Tiêu chí chấm chuyển ra file `config/review_guide.md` (gửi nguyên văn cho model, như `script_guide.md`): 3 mục Nhân vật,
  Đồ vật, Ảnh nền. Sửa tiêu chí không cần sửa code.
- **So với ảnh chuẩn**: ảnh nhân vật được gửi kèm ảnh chuẩn `config/refs/<tên>_front.png` (ảnh 1) trước ảnh cần chấm (ảnh 2),
  để bắt đổi kiểu tóc, đổi màu áo (lỗi video 008). `steps/llm.py chat(images=[...])` gửi nhiều ảnh.
- **Chấm theo tiêu chí**: model trả `checks` 1-5 từng tiêu chí (nhân vật: character, outfit, body, objects, extras, action;
  đồ vật: object, count, extras, shape; nền: place, empty, shape, mood). Code quyết định: tiêu chí bắt buộc (★ trong file)
  ≤ 2 thì vẽ lại; tiêu chí không ★ (hành động, không khí) chỉ ghi chú. Điểm hiện trên web là trung bình; rê chuột vào huy hiệu
  "AI x/5" xem điểm từng tiêu chí và tiêu chí làm trượt.
- Giữ: nền xanh lá là cố ý, không trừ điểm vì màu nền; đồ đạc cố định vẽ kèm, đồ vật nhân đôi là lỗi.
- Kiểm tra với server AI giả: ảnh nhân vật gửi 2 ảnh, ảnh đồ vật / nền 1 ảnh; trang phục 2 điểm → vẽ lại dù trung bình 4,2;
  chỉ hành động 2 điểm → vẫn đạt. Chưa chạy với model thật.

## 2026-10-08: sửa bước AI chấm ảnh (video 009)

- Lỗi dừng quy trình: AI loại ảnh gốc (004.png) thì `reject_image` bỏ luôn 004_alt.png, nhưng danh sách ảnh cần chấm lập từ trước
  nên tới lượt 004_alt.png thì không còn file (FileNotFoundError). Sửa: ảnh không còn thì bỏ qua.
- Lỗi chấm oan (nguyên nhân chính khiến AI duyệt "quá khắt khe" từ trước): câu hỏi chấm ảnh yêu cầu "nền trắng sạch", trong khi
  ảnh cố ý vẽ trên nền xanh lá để tách nền → AI trừ điểm gần như mọi ảnh ("Nền xanh lá thay vì nền trắng"). Sửa `IMAGE_PROMPT`,
  `OBJECT_PROMPT`: nói rõ nền xanh là cố ý, không trừ điểm vì màu nền; phân lỗi nặng (sai nhân vật, cơ thể lỗi, thêm người,
  thiếu / nhân đôi đồ vật, chữ lạ) / vừa (hành động lệch, vẽ kèm đồ đạc cố định) / nhẹ (khung hình hơi khác: trừ tối đa 1 điểm).
- Video 009: trả 003_alt, 004, 004_alt về characters/ để chấm lại bằng câu hỏi mới (không vẽ lại); đủ ảnh, chờ bấm Chạy tiếp.

## 2026-10-08: sửa lỗi "shot phải là một trong full, half, close" (video 010)

- Lỗi: ở cảnh chỉ có đồ vật / cảnh trống model ghi `"shot": null` (và `"object": null`, `"alt_pose": null`...); `make_jobs.py`
  coi null là giá trị sai và dừng. Cùng kiểu lỗi model viết lệch như `"src"` ở video 008.
- `steps/common.py normalize_script`: trường tùy chọn để null coi như bỏ trống (dùng mặc định), `"characters": null` → `[]`,
  `shot` lạ → `full`, giá trị null trong layers bỏ đi, rồi `normalize_layers`. Chạy ở `01_script.py` (trước khi ghi),
  `make_jobs.py` (trước khi kiểm tra) và `build_video.py` (khi đọc), nên kịch bản cũ cũng tự được sửa.
- Video 010: chuẩn hóa script.json (75 chỗ null; bản gốc giữ ở thư mục tạm); make_jobs ra 48 job. Chưa chạy tiếp
  (tốn giờ GPU của chủ video, để người dùng bấm).

## 2026-10-08: thêm tiếng hiệu ứng và tiếng nền theo bối cảnh

- `tools/fetch_sfx.py`: thêm 72 tiếng từ 効果音ラボ (mục 戦闘, 環境, ボタン, 演出・アニメ): đấm, tát, ngã, vung tay, オーラ, ワープ,
  スローモーション, 回復, quiz đúng / sai, tin nhắn, bíp, cảnh báo, đồng hồ, trống dồn, rùng rợn, ファンファーレ, ăn uống...
  Tổng 171 tiếng, 80 nhóm. Nhóm `amb_*` (tiếng nền) giữ dài 40 giây, mờ vào / mờ ra để lặp không giật.
- `build_video.py`: thêm chữ tượng thanh → tiếng (バシッ, パチン, バタン, ブン, ピンポーン, ブブー, ピロン, ゾクッ, モグモグ, ホッ...);
  hiệu ứng `aura` → オーラ, `confetti` → ファンファーレ; anim `spin_in` → ワープ.
- **Tiếng nền theo bối cảnh**: dò từ khóa trong tên bối cảnh theo từng từ (tách `_`), vd `train_car` → tàu chạy, `station` → ga,
  `rain` → mưa, `classroom` → lớp học, `drugstore`/`shop` → cửa hàng, `seaside` → biển, `port` → cảng; trong nhà yên tĩnh
  (`kitchen`, `bedroom`, `office`, `hospital`...) không có; dự phòng theo giờ (`morning` chim sẻ, `dusk` quạ, `night` côn trùng).
  Nối liền qua các cảnh (lấy theo giây của cảnh trong video), âm lượng `[video] ambient_volume = 0.14`, cảnh ghi
  `"ambient": "amb_..."` hoặc `null` để đổi / tắt. Lần đầu dò theo chuỗi con nên `train_car` ra tiếng mưa ("t-rain"),
  `stationery` ra ga tàu: đã sửa.
- Hạ cả đoạn khi giọng + hiệu ứng + nền vượt đỉnh 0.95 (chống méo).
- `script_guide.md`: bảng tiếng mới và từ khóa tiếng nền để model đặt tên bối cảnh có chủ ý.
- Kiểm tra: dò tiếng nền cho mọi bối cảnh đang có, chữ tượng thanh mới, trộn thử một cảnh (đỉnh -0,4 dB). Không dựng lại video
  (người dùng dặn chỉ sửa code); video mới và video dựng lại sẽ có.

## 2026-10-08: tiếng hiệu ứng thật từ 効果音ラボ

Người dùng: "có thư viện nào không, tải về cho nhiều, tạo làm gì".
- `tools/fetch_sfx.py`: tải 99 tiếng chọn lọc từ 効果音ラボ (mục 演出・アニメ, 生活, 機械) vào `library/sfx/lab/<nhóm>/`, 38 nhóm,
  mỗi nhóm nhiều phiên bản (ショック 7, きらーん 7, ドン 6, ポン 6...). Chuyển sang wav 48 kHz mono, cắt đuôi > 3 giây, chuẩn hóa
  đỉnh. Tải chậm (1 giây / file); file mp3 cần Referer của trang (như bấm nút tải). Điều khoản (đọc 2026-10-08): dùng được trong
  video YouTube có kiếm tiền, không cần ghi nguồn; cấm phát tán lại file gốc và dùng học AI → `library/sfx/lab/` vào `.gitignore`.
  OtoLogic chặn truy cập tự động (403) nên chưa dùng.
- `build_video.py`: ưu tiên tiếng thật, chọn luân phiên trong nhóm theo cảnh; gắn thêm theo chữ tượng thanh (ガタンゴトン → tàu,
  プルル → điện thoại, ドキドキ → tim đập, ダッ → chạy, ズキッ → グキッ, シーン → im lặng...), vào hồi tưởng → 回想, sticker
  "!" → 驚く. Tiếng tạo bằng code (`make_sfx.py`) chỉ còn là dự phòng khi chưa tải.
- `script_guide.md` mục 6: bảng chữ tượng thanh → tiếng để model viết có chủ ý.

## 2026-10-08: hiệu ứng âm thanh kiểu gameshow / anime Nhật

Người dùng muốn tiếng hiệu ứng "Nhật bản nhất". `tools/make_sfx.py` viết lại, tạo 15 tiếng bằng code: ドン (taiko), ドドン,
ガーン (hợp âm kèn đổ xuống), チーン (chuông chùa rin), ピコン (quiz show), ポン (gõ gỗ), ボヨン (lò xo), キラーン, シャキーン,
ジャン! (dàn nhạc + taiko), ヒュ〜 (còi trượt), ハテナ, チャンチャン (kết hài), whoosh, swish. File nghe thử
`library/sfx/_nghe_thu.wav` (các tiếng nối nhau theo thứ tự trên).
- `build_video.py`: gắn theo ý nghĩa: sticker theo tên (exclaim → ピコン, question → ハテナ, sweat → ヒュ〜, tear → チーン,
  anger → ドン, gloom/lines → ガーン, heart → キラーン), hiệu ứng (gloom → ガーン, tears/rain → チーン, rays → シャキーン,
  sparkles/hearts/aura → キラーン, flash → ドドン, speed_lines → ドン), anim (hop/jump/bounce → ボヨン, punch → ドン,
  sink → チーン, shiver → ヒュ〜), motion shake/punch_in → ドン, vào twist → ジャン!, cảnh cuối video hài → チャンチャン.
  Tên cũ trong kịch bản (boom, shock, ding, sparkle, pop) tự đổi sang tên mới. Bảng tra trong `script_guide.md` mục 6.
- Video 008 dựng lại: 41/52 cảnh có tiếng (ポン 11, whoosh 9, ドン 7, ボヨン 6, キラーン 6, ガーン 5...). Chưa nghe thử bằng tai.

## 2026-10-08: sửa theo góp ý (video 004, 007, 008)

Đối chiếu file tổng hợp góp ý với video 008 (xem từng khung 2 giây): ghế, tay vịn, cột, khung cửa sổ, quầy vẽ dính vào nhân vật
và lệch với nền; nhân vật đổi màu áo giữa các cảnh; phụ đề ngắt giữa chữ (席を譲らな｜かった); 99 giây quá dài; nhân vật cận
chiếm 2/3 khung; không có hiệu ứng âm thanh.
- **Đồ vật** (`script_guide.md` mục 1, `make_jobs.py`): chỉ vẽ kèm nhân vật thứ cầm nắm được; đồ cố định thuộc ảnh nền; nhân vật
  ngồi dùng khung `half` / `close`; đồ cầm tay ghi số lượng, tay cầm, thứ không có (`no hat on his head`); trạng thái đồ vật liên
  tục giữa các cảnh. Prompt ảnh cảnh thêm "mặc đúng trang phục, màu như ảnh chuẩn" và "chỉ người này và đồ trong tay, không ghế,
  cửa, cửa sổ, tường, cột, tay vịn, quầy".
- **Trang phục** (mục 0b): nhân vật mới tả từng món đồ kèm màu; `action` không nhắc quần áo khác.
- **Nhịp**: giọng đọc nhanh 1,2 lần giữ cao độ (`[voice] tempo`, atempo), nghỉ giữa câu 0,15 → 0,08 giây; kịch bản 30-40 cảnh,
  45-60 giây (mục 0, 8, 9).
- **Cỡ nhân vật**: đọc nhầm góp ý "nhân vật to 2/3 khung hình" thành quá to (đã giảm ~15%); người dùng sửa lại: muốn nhân vật chiếm khoảng 2/3 khung. Nay toàn thân 0.64 đứng sát mép dưới (`at = floor`), nửa người 0.66, cận 0.62, `large` 0.62.
- **Chuyển động**: không tự chọn `motion: none` nữa; quy tắc cao trào (flash + shake / punch_in), đổi biểu cảm = punch_in.
- **Hiệu ứng âm thanh**: `tools/make_sfx.py` tạo 7 tiếng bằng code vào `library/sfx/` (whoosh, swish, pop, boom, shock, ding,
  sparkle; thay được bằng file thật cùng tên). `build_video.py` tự gắn theo chuyển cảnh, rung, hiệu ứng, chữ tượng thanh, sticker,
  hoặc trường `"sfx"` của cảnh; tối đa 3 tiếng một cảnh, âm lượng `[video] sfx_volume`. Lần đầu quá nhỏ (thấp hơn giọng ~6 dB) và thưa: tăng `sfx_volume` 0.55 → 0.95, pop dài 0.16 giây, gắn thêm whoosh khi đổi bối cảnh bằng cắt / mờ, boom khi vào twist, swish khi lớp bay vào (`path`), pop khi anim bật (pop, punch, jump, hop, spin_in, drop). Video 008: 35/52 cảnh có tiếng.
- **Phụ đề**: ngắt dòng bằng quy hoạch động: ít dòng, ưu tiên sau dấu câu, sau trợ từ, chỗ đổi loại chữ; phạt nặng khi cắt giữa
  cụm Hiragana, giữa chữ Hán và đuôi chữ, giữa một từ chữ Hán / Katakana.
- Chưa làm: tắt nhạc nền đúng lúc cao trào (chưa có nhạc nền), chữ phụ đề bật từng cụm.

## 2026-10-08: sửa lỗi KeyError 'image' ở bước Bố cục (video 008)

- Lỗi: model viết lớp ảnh bằng khóa `"src"` (`{"id": "seat_man", "src": "cutouts/001.png"}`, 63 lớp) thay vì `"image"`;
  yêu cầu gửi model chỉ ví dụ đường dẫn, không ghi rõ tên khóa. `build_video.py` gặp KeyError.
- `steps/common.py normalize_layers`: đổi `src`, `file`, `img`, `url`, `sticker`... → `image`; `text`, `sfx` → `word`;
  chuỗi `.png` ghi nhầm vào `path` → `image`; bỏ lớp không có ảnh, chữ, hiệu ứng (in ra). Chạy ở `01_script.py` trước khi ghi
  kịch bản và ở `build_video.py` khi đọc kịch bản (kịch bản cũ vẫn dựng được). `check()` báo rõ lớp thiếu khóa thay vì KeyError.
- `01_script.py`: yêu cầu gửi model ghi rõ 3 dạng lớp (ảnh / chữ / hiệu ứng) kèm ví dụ và tên khóa.
- Video 008: chuẩn hóa script.json (bản gốc giữ ở thư mục tạm), xem trước 52 cảnh, chạy tiếp → output.mp4.

## 2026-10-08: chọn chế độ duyệt ảnh khi tạo video

Người dùng: lúc bận không thể ngồi duyệt bằng mắt.
- Khung Tạo video có lựa chọn **Duyệt ảnh** (nhớ lựa chọn lần trước): 👀 Tôi tự duyệt (mặc định, dừng chờ duyệt) ·
  🤖 AI duyệt tự động (AI chấm mọi ảnh đạt từ 3/5, ảnh trượt vẽ lại tối đa 3 lượt Kaggle, hết lượt thì dùng tạm lần vẽ gần nhất
  và ghi cảnh báo, rồi tự dựng) · ⏩ Không duyệt (dùng luôn ảnh Kaggle). Lưu `review_mode` trong `meta.json`, truyền
  `SHORTS_REVIEW_MODE` cho `tools/auto.py`; cửa sổ video hiện chế độ đã chọn.
- Màn duyệt ảnh có thêm nút **Để AI duyệt hết** (đổi video sang chế độ AI rồi chạy tiếp) cho lúc đang chờ duyệt mà bận.
- `review.py --all`: ảnh đã chấm đạt và chưa đổi thì không chấm lại (đỡ tiền API khi AI tự duyệt nhiều lượt).
- Kiểm tra: chế độ AI chạy auto.py với server AI giả (chấm đủ 10 ảnh, tự duyệt, đi tiếp); chế độ Không duyệt qua web ra output.mp4;
  chụp giao diện máy tính và điện thoại. Chưa thử chế độ AI với model thật.

## 2026-10-08: người duyệt ảnh bằng mắt thay cho AI chấm hết

Người dùng thấy bước AI duyệt ảnh quá khắt khe (video 005: AI loại gần hết, Kaggle phải vẽ lại 65 ảnh, tốn giờ GPU).
- Quy trình mới (`tools/auto.py`): Kaggle vẽ xong → dừng ở bước **Duyệt ảnh** (mã thoát 3, lịch sử chạy ghi "Chờ duyệt ảnh",
  không giữ tài khoản Kaggle). Trên web: lưới ảnh nhân vật / đồ vật (kể cả tư thế 2) và ảnh nền của video, xem lớn
  (← → chuyển, Space chọn), tích chọn rồi:
  - **Ảnh ổn, làm tiếp**: ghi `review/approved.json` (dấu vân tay bộ ảnh), chạy tách nền → bố cục → giọng → dựng.
  - **AI kiểm tra**: AI chỉ chấm ảnh đã chọn (`review.py images --only`), ảnh dưới ngưỡng bị bỏ và vẽ lại, rồi quay lại màn duyệt.
  - **Vẽ lại**: bỏ ngay ảnh đã chọn, vẽ lại bằng seed khác, rồi quay lại màn duyệt.
  Ảnh đổi sau khi duyệt thì phải duyệt lại. Trang Tạo video có mục "Chờ bạn duyệt ảnh"; menu đếm cả video chờ duyệt.
- `review.py`: ngưỡng đạt 3/5 (biến `REVIEW_PASS_SCORE`), chấm được ảnh nền, ghi kết quả theo khóa ảnh kèm mtime để web
  hiện huy hiệu "AI x/5" khi ảnh chưa đổi. Gọi `images` không kèm `--only` / `--all` thì thoát mã 3 (bản auto.py cũ).
- `steps/common.py`: `review_items`, `image_stamp`, `reject_image` (ảnh gốc bị bỏ thì bỏ cả `_alt` và ảnh đã tách nền;
  ảnh nền chuyển sang `library/backgrounds/rejected/`). `make_jobs.py`: ảnh nền bị bỏ thì đổi seed.
- `web/app.py`: lưu pid của từng lần chạy; server khởi động lại thì gắn lại việc còn chạy thay vì đánh dấu "bị ngắt";
  dừng việc theo pid. Phục vụ ảnh `characters/`, `backgrounds/` để duyệt (cần đăng nhập). Vẽ lại dùng tài khoản Kaggle của chủ video.
- Kiểm tra: video thử (bản sao smoke-10s) dừng ở Chờ duyệt với 10 ảnh → chụp màn duyệt, xem lớn → bấm "Ảnh ổn, làm tiếp"
  trên giao diện → dựng ra output.mp4; bỏ ảnh: `_alt` và cutout đi theo, make_jobs tạo job seed mới; bỏ ảnh nền trên bản sao.
  Chưa thử "AI kiểm tra" và "Vẽ lại" với Kaggle, AI thật (tốn GPU, tiền API).
- Video 006 thất bại trước đó vì kernel Kaggle bị hủy (`cancel_requested`); video 005 đã bị người dùng xóa.

## 2026-10-08: sửa lỗi vỡ chữ khi gọi AI qua ShopAIKey

- Lỗi: `steps/llm.py` đọc stream bằng `iter_lines(decode_unicode=True)`; ShopAIKey trả `text/event-stream` không khai charset nên
  `requests` giải mã Latin-1, chữ Nhật và Việt thành ký tự rác (tiêu đề, lời thoại trong script.json, nhận xét duyệt ảnh).
  Sửa: đặt `r.encoding = "utf-8"` trước khi đọc.
- Video 005-hook-3-giay-toi-tung (đang chạy khi phát hiện): khôi phục script.json và review/images.json bằng cách mã hóa lại
  Latin-1 → giải mã UTF-8 (không mất chữ nào, không cần gọi AI lại); bản lỗi giữ ở thư mục tạm. Config không bị ảnh hưởng
  (mô tả nhân vật, bối cảnh là tiếng Anh). Log cũ của lần chạy đó vẫn còn dòng vỡ chữ.
- Thanh tiến trình: tên bước được xuống dòng thay vì chồng lên nhau khi khung hẹp.

## 2026-10-08: cảm xúc kiểu Facebook cho góp ý

- Thay nút "Thích" đơn bằng 6 cảm xúc 👍 Thích, ❤️ Yêu thích, 😆 Haha, 😮 Wow, 😢 Buồn, 😡 Phẫn nộ (`web/src/components/Reactions.jsx`):
  rê chuột (điện thoại: nhấn giữ) hiện thanh chọn; bấm nhanh là 👍 hoặc bỏ cảm xúc đang chọn; nút đổi chữ và màu theo cảm xúc.
  Góc bong bóng hiện top 3 emoji và tổng số, rê chuột xem ai thả gì. Trang Góp ý cũng thả được và xếp theo số cảm xúc.
- Server: `reactions` {người: cảm xúc} thay `likes`; dữ liệu cũ tự chuyển thành 👍; API `/api/feedback/react`; file xuất ghi số từng cảm xúc.
- Kiểm tra: chuyển dữ liệu cũ, thả / đổi / bỏ cảm xúc, cảm xúc sai bị chặn; chụp thanh chọn và phần tổng hợp.

## 2026-10-08: góp ý cho từng video

Người dùng muốn mọi người nhận xét từng video (kiểu bình luận Facebook) rồi tổng hợp lại để cải thiện quy trình.
- Dưới mỗi video đã hoàn thành (cửa sổ video): viết góp ý, chọn hạng mục (kịch bản, hình ảnh nhân vật, ảnh nền, chuyển động,
  giọng đọc, phụ đề, nhạc, khác — khớp các bước quy trình), chấm 1-5 sao, gắn thời điểm đang phát (bấm vào để tua tới đoạn đó);
  Thích, Trả lời (một cấp), Xóa (người viết hoặc admin), admin Đánh dấu đã xử lý. Thẻ video ở Thư viện hiện số góp ý.
- Trang **Góp ý** (mọi người thấy): số góp ý, chưa xử lý, điểm trung bình, người góp ý; số góp ý chưa xử lý theo hạng mục
  (bấm để lọc); lọc theo trạng thái và video; menu hiện số góp ý chưa xử lý.
- **Xuất tổng hợp (.md)**: `/api/feedback/export`, xếp theo hạng mục, góp ý nhiều người đồng ý lên trước, kèm phản hồi, điểm,
  thời điểm; dán cho AI để đề xuất sửa `script_guide.md`, prompt ảnh, thông số dựng.
- Lưu ở `data/feedback.json`; xóa video vẫn giữ góp ý (hiện "đã xóa") để tổng hợp không mất.
- Kiểm tra: API (gửi, trả lời bỏ hạng mục và sao, thích, user không đánh dấu xử lý / không xóa góp ý người khác, video không có,
  quá ngắn, xóa góp ý xóa luôn phản hồi), file xuất Markdown; chụp giao diện máy tính và điện thoại.

## 2026-10-08: video đa dạng hơn (thể loại, nhân vật, bối cảnh, chuyển động)

Người dùng thấy video thiếu đa dạng, nhất là ảnh nền. Nguyên nhân: yêu cầu gửi model ghi "chỉ dùng các tên này" cho nhân vật
và bối cảnh, và thể loại viết cứng trong code (luôn ngôi thứ nhất, luôn twist cảm động). 3 video gần nhất dùng dining_room 35 cảnh, kitchen 30 cảnh.
- `config/script_guide.md`: mục 0 (chọn thể loại theo đề tài: cảm động, hài, bí ẩn, スカッと, tình yêu, công sở, ngụ ngôn; đổi góc kể;
  đề tài dài thì giữ đúng chi tiết người dùng viết), mục 0b (dùng lại hoặc tạo nhân vật, bối cảnh mới; mỗi video ≥4 bối cảnh,
  có ngoài trời, đổi thời gian trong ngày, thời tiết, mùa; gợi ý nơi chốn ít dùng), emotion cụ thể để anim đa dạng, ≥4 loại hiệu ứng,
  nhân vật bước vào/rời khung ≥2 lần, tư thế đa dạng, mục 9 tự kiểm trước khi trả kết quả. Giữ nguyên quy tắc kỹ thuật mục 1-6.
- `steps/01_script.py`: bỏ "chỉ dùng các tên này" và thể loại viết cứng; model khai `new_characters` (ngoại hình, loại giọng, màu)
  và `new_locations` (mô tả), code ghi vào `config/characters.json` / `locations.json` (giọng edge-tts theo loại, khung prompt nền
  Irasutoya tự thêm, tên trùng thì giữ bản cũ, có khóa file khi nhiều người tạo cùng lúc); make_jobs tự sinh ảnh chuẩn và ảnh nền
  cho thứ mới. Gửi kèm "Gần đây đã dùng" (tiêu đề, thể loại, nhân vật, bối cảnh, cảm xúc của 6 video gần nhất) để tránh lặp.
  Kịch bản dùng tên chưa khai thì không ghi (lưu ở work/script_rejected.json), Chạy tiếp sẽ viết lại. script.json có thêm `genre`.
- `variety.py`: thêm từ khóa cảm xúc (sợ, nhẹ nhõm, hào hứng, ngại, ghen, thất vọng, hoài niệm...) để chọn anim hợp thay vì mặc định.
- Kiểm tra: chạy 01_script với server AI giả: yêu cầu không còn "chỉ dùng các tên này", có "Gần đây đã dùng" và mục 0b; thêm đúng
  nhân vật và bối cảnh mới, bỏ qua tên trùng và tên sai dạng; config thật được khôi phục sau khi thử. Chưa thử với model thật.

## 2026-10-08: giao diện responsive

- Màn hình rộng: nội dung căn giữa (tối đa 1320px, từ 1600px là 1440px) thay vì dồn trái để trống nửa phải.
- Laptop nhỏ / tablet ngang (≤1180px): thanh bên hẹp 220px.
- Tablet dọc / điện thoại (≤900px): thanh trên gọn (logo, tên, nút đăng xuất) dính đầu trang; menu chuyển xuống thanh dưới đáy như app; hộp thoại trượt từ dưới lên; gợi ý đề tài xuống dòng; tab người dùng và bộ lọc vuốt ngang; lưới video 2 cột.
- Sửa: khối CSS responsive cũ nằm giữa file nên bị luật phía sau đè; ô tìm kiếm và thanh lọc rộng hơn màn hình; hàng đầu trang bị kéo cao khi nội dung ngắn; đổi `#trang` trên địa chỉ / nút Back không chuyển trang.
- Kiểm tra bằng Playwright + Edge: 5 trang × 6 độ rộng (1920, 1440, 1180, 1024, 768, 390), không trang nào cuộn ngang; chụp ảnh từng cỡ.

## 2026-10-08: gọi AI qua ShopAIKey, chọn model ở trang web

Người dùng không dùng khóa Anthropic trực tiếp mà qua ShopAIKey (cổng nhiều model, endpoint chuẩn OpenAI `https://api.shopaikey.com/v1`).
- `steps/llm.py` (mới): gọi `/v1/chat/completions` dạng stream bằng `requests`, kèm ảnh JPEG dạng data URI; thử lại khi 429/5xx; model OpenAI đời mới từ chối `max_tokens` thì tự đổi sang `max_completion_tokens`; báo lỗi khi câu trả lời bị cắt; `python steps/llm.py models` liệt kê model của cổng.
- `steps/01_script.py`, `review.py`: bỏ SDK `anthropic` (các tham số beta riêng của Anthropic không đi qua được cổng), gọi qua `llm.py`. Model lấy từ `AI_MODEL_SCRIPT` / `AI_MODEL_REVIEW`. Duyệt ảnh: model trả lời không phải JSON thì hỏi lại một lần, vẫn hỏng thì tạm cho qua để không chặn cả video.
- Web: trang **Cài đặt AI** (admin): endpoint, danh sách model hiện ở dropdown (sửa tay hoặc bấm "Lấy từ cổng" để chọn từ `/v1/models`), model mặc định cho viết kịch bản và duyệt ảnh; lưu ở `data/settings.json`. Trang Tạo video có 2 dropdown chọn model, nhớ lựa chọn lần trước; model đã chọn lưu trong `meta.json` của video và hiện trong cửa sổ video. Khóa hồ sơ đổi tên `anthropic_api_key` → `ai_api_key` (tự chuyển khi khởi động).
- Kiểm tra: `llm.py` với server giả chuẩn OpenAI (stream, ảnh, đổi `max_completion_tokens`, bị cắt, sai khóa 401); `/v1/models` thật của ShopAIKey trả 401 khi không có khóa (endpoint đúng); chụp giao diện. Chưa gọi ShopAIKey thật vì chưa có khóa AI trong hồ sơ.

## 2026-10-07 (khuya): thư viện theo người, xóa dễ hơn, tải video về máy người xem

- Thư viện chia theo người tạo: mỗi người một tab có số video (mặc định mở tab của mình), tab "Mọi người" xếp nhóm theo người. Video 001-004 gán cho `nickytiktok` (`meta.json`).
- Nút xóa luôn hiện (không cần rê chuột) trên thẻ ở Thư viện, trong cửa sổ video, và trên thẻ "Chưa xong / lỗi" ở trang Tạo video. Xóa được cả video đang chạy: dừng việc rồi xóa thư mục (thử lại vài lần nếu Windows còn giữ file).
- Tải video: `/videos/<tên>/output.mp4?download=1` trả `Content-Disposition: attachment`, trình duyệt lưu file về máy người đang đăng nhập. Server chạy `--host 0.0.0.0` để máy khác trong LAN vào được.
- Kiểm tra qua IP LAN 192.168.1.2: người tạo đúng, tải về có header attachment (34,9 MB), user không xóa được video người khác, xóa được video của mình. Chưa thử xóa video đang chạy thật.

## 2026-10-07 (tối): đăng nhập, Claude duyệt ảnh trong quy trình tự động, xóa video

- **Đăng nhập** (`web/app.py`): mật khẩu băm PBKDF2, phiên 30 ngày lưu ở `data/sessions.json` (cookie HttpOnly). Mọi API, ảnh, video đều cần đăng nhập. Quyền: admin thêm/xóa/sửa thành viên, đặt quyền và mật khẩu, thao tác mọi video; user chỉ sửa hồ sơ, khóa, mật khẩu của mình (phải nhập mật khẩu cũ) và chạy/dừng/xóa video do mình tạo. Người tạo video ghi ở `videos/<tên>/meta.json`.
  Tài khoản: `nickytiktok` (admin, là hồ sơ `tranhoang1124` cũ, giữ nguyên khóa), `tustruyen`, `phuctran` (user, Kaggle `tus`, `phuc`, chưa có khóa). Mật khẩu ban đầu do người dùng chọn. Tạo / đặt lại mật khẩu từ dòng lệnh: `python web/app.py --add-user <tên> <mật khẩu> [--admin]`.
- **Claude duyệt ảnh** là một bước bắt buộc của `tools/auto.py`, không bỏ qua: mỗi lượt vẽ ảnh còn thiếu trên Kaggle → `review.py images` chấm từng ảnh (đạt từ 4/5) → ảnh hỏng sang `rejected/`, lượt sau vẽ lại với seed khác. Tối đa 3 lượt; hết lượt vẫn chưa đạt thì dùng tạm lần vẽ gần nhất và ghi cảnh báo vào tiến trình.
- `review.py images`: chấm cả cảnh đồ vật (trước chỉ chấm nhân vật), dùng `character_files` cho đúng tên file, không chấm lại ảnh đã đạt và chưa đổi (đỡ tốn API), ảnh gốc bị loại thì loại luôn tư thế thứ hai `_alt`, không lỗi với khung hình lạ.
- **Xóa video**: nút trên thẻ ở Thư viện và trong cửa sổ video; xóa cả thư mục `videos/<tên>` (ảnh, giọng đọc, output.mp4). Không xóa được khi đang chạy.
- Kiểm tra: phân quyền qua API (chưa đăng nhập 401 cả ảnh; sai mật khẩu; user sửa người khác / xóa video người khác / xóa thành viên bị chặn 403; đổi mật khẩu sai mật khẩu cũ bị chặn; admin xóa video được; đăng xuất). Duyệt ảnh thử với câu trả lời giả của Claude: loại đúng ảnh và `_alt` của nó, lần sau không chấm lại ảnh đạt, dùng tạm ảnh khi hết lượt. Chưa gọi Claude thật (tài khoản admin chưa có khóa Anthropic).

## 2026-10-07 (chiều): tự động hoàn toàn, tiến trình và giờ GPU thật, giao diện mới

Người dùng chê giao diện xấu; muốn chỉ nhập đề tài là ra video, theo dõi được tiến trình và giờ GPU chính xác, mọi thứ nhập vào được lưu.
- `tools/auto.py`: một lệnh chạy trọn kịch bản (Claude) → jobs → Kaggle → tách nền → bố cục → giọng đọc → dựng. Thiếu ảnh sau lượt Kaggle đầu thì gửi thêm một lượt. Ghi `videos/<tên>/progress.json` (trạng thái từng bước, lỗi, giờ GPU). Bước nào xong thì bỏ qua, nên "Chạy tiếp" là chạy từ chỗ dừng. Bỏ bước đọc và sửa tay `script.json`.
- Tiến trình Kaggle: `run_kaggle.py` đọc log đang chạy của kernel (`kaggle kernels logs`) mỗi lần hỏi trạng thái, đếm ảnh xong / lỗi / đang vẽ theo dòng log của `worker.py`, ghi `work/kaggle_progress.json`.
- Giờ GPU lấy thẳng từ Kaggle (`kaggle quota`, CLI 2.2.4): đã dùng / còn lại / giờ cấp lại cho từng tài khoản (`tools/kaggle_quota.py`), hỏi lại 5 phút một lần và sau mỗi lần chạy. Giờ GPU của từng video = quota sau − quota trước lượt Kaggle. Không cho tạo video khi tài khoản còn dưới 0,5 giờ.
- Lưu lại: đề tài ở `videos/<tên>/prompt.txt` và trong lịch sử chạy; nháp ô đề tài giữ trong trình duyệt; tên thư mục video tự đặt `<số tiếp theo>-<đề tài không dấu>`.
- `steps/01_script.py`: nhận đề tài từ file `.txt` (đề tài dài, cả câu chuyện).
- Giao diện viết lại: thanh bên, trang Tạo video (ô đề tài + thẻ tiến trình từng bước + thanh ảnh Kaggle), Thư viện (lưới ảnh bìa, lọc, tìm, mở xem video ngay trên trang, tải về), Hoạt động, Thành viên (giờ GPU thật, khóa, đưa LoRA lên). Server phát video có hỗ trợ tua (Range). Dừng một việc thì dừng cả cây tiến trình.
- `web/app.py` đọc lại PATH của Windows khi khởi động: ffmpeg cài qua winget sau khi mở cửa sổ vẫn chạy được.
- Kiểm tra: `auto.py` chạy trọn trên bản sao `_tests/smoke-10s` (đủ ảnh nên bỏ qua Kaggle) ra `output.mp4` 9,2 giây; bộ đếm tiến trình thử với log mẫu; `kaggle quota` trả đúng 25,51/30 giờ của tranhoang1124; chụp giao diện desktop và điện thoại. Chưa chạy: viết kịch bản bằng Claude và lô Kaggle thật qua trang web.

## 2026-10-07: trang web cho nhiều người dùng

Người dùng có thêm 2 tài khoản Kaggle và Hugging Face; muốn dùng chung một source thay vì chép 3 bản, và biết ai đang dùng, bao nhiêu người.
- `web/`: giao diện React (Vite, `web/src`) và server Python thư viện chuẩn (`web/app.py`). Mỗi người dùng một hồ sơ: Kaggle username, Kaggle token, HF token, Anthropic API key. Nút chạy 01 kịch bản, 02 jobs, 03 sinh ảnh / tải lại, 04 dựng, đưa LoRA lên (một lần mỗi tài khoản). Hiện số người dùng, đang mở trang, đang chạy, giờ GPU tuần này của từng tài khoản (tính từ thời gian các lần sinh ảnh), lịch sử chạy và log.
- Dữ liệu ở `data/` (không lên git): `users.json`, `runs.json`, `logs/`. Khóa không gửi về trình duyệt; mỗi lần chạy truyền khóa của người bấm qua biến môi trường. Lần đầu mở, tài khoản trong `config.toml` thành người dùng đầu tiên.
- `tools/run_kaggle.py`: nhận tài khoản từ `SHORTS_KAGGLE_USERNAME`, `SHORTS_KAGGLE_KEY`, `SHORTS_HF_TOKEN` (đè lên `config.toml`); thư mục gửi đi tách theo tài khoản `build/<username>/` để chạy song song không đè nhau. Chạy tay bằng dòng lệnh vẫn như cũ.
- Chặn: hai việc cùng một video, hai lô Kaggle cùng một tài khoản.
- Kiểm tra: build React được; API với người dùng giả (khóa giả không xuất hiện trong /api/state; thiếu khóa Anthropic thì từ chối viết kịch bản; video chưa có script.json bị từ chối; chạy make_jobs qua web xong, có log); `run_kaggle.py --dry-run` với tài khoản qua biến môi trường ra đúng `fakeuser/shorts-gen`. Chưa gửi thật lên Kaggle bằng 2 tài khoản mới.

## 2026-10-08: video 004 theo đề tài của người dùng

Đề tài: "Sống thật hay giữ việc?". Nhân viên phát hiện công ty xả thải lén; tố cáo thì mất việc, im lặng thì sống yên; câu kết "Anh chọn lương, hay chọn ngủ ngon?".
- Video 004 "給料か、眠れる夜か" (`videos/004-kyuryo-ka-yoru-ka`): 49 cảnh, 91,7 giây giọng đọc; 6 toàn thân, 17 nửa người, 16 cận mặt; 7 cảnh đồ vật, 3 cảnh dùng lại ảnh; 13 cảnh hai tư thế; 28 lớp hiệu ứng. Chuyển động và chuyển cảnh để `variety.py` tự chọn, chỉ ghi tay ở chỗ có chủ ý (`shake` khi sốc, `dutch` khi bị ép, `flash` khi quay về quá khứ và ở twist).
- Cấu trúc: móc câu bằng chính lựa chọn cuối (xấp tiền và điện thoại trên bàn) → "3 ngày trước" → phát hiện → áp lực từ quản đốc và đàn anh → lý do để im (con, vợ mang thai, nợ nhà) → twist (con sông con gái chơi là con sông nước đen chảy vào) → vợ "anh chọn gì em cũng theo" → quay về xấp tiền và điện thoại → câu hỏi cho người xem "あなたなら、どっちを選ぶ？" (kết mở để kéo bình luận).
- Lời kể dùng giọng nam của chính nhân vật chính (`worker`, ngôi thứ nhất), không dùng `narrator` giọng nữ.
- Nhân vật mới: `worker`, `boss`, `senpai`, `wife`, `daughter`. Bối cảnh mới: `factory_floor`, `factory_back`, `riverside`, `manager_office`.
- Kiểm tra trước khi gửi Kaggle: không lỗi kịch bản, không cảnh báo lặp, không câu phụ đề bị ngắt giữa từ, không quá 2 cảnh liền cùng khung hình.
- Kaggle: 68 ảnh, 0 lỗi, khoảng 45 phút. Soát ảnh xem trước theo bảng lớn (cảnh 1-25, 26-49), sinh lại 9 ảnh qua 2 lượt:
  - Cảnh 4: ảnh có mảng tường đen vẽ dính đứng giữa khung. Bỏ "along a dark wall" khỏi `action`.
  - Cảnh 26: bụng bầu bị vẽ thành khối tròn nâu (hai lần). Đổi cách thể hiện: vợ cầm đôi tất em bé.
  - Cảnh 39: thanh màu hồng tím dọc người (khung cửa vẽ dính, tách nền lỗi). Bỏ "standing in a doorway".
  - Cảnh 40: bàn tay nâu kỳ lạ ở góc dưới. Ghi rõ "both arms down at her sides".
  - Cảnh 6 và 35 (ống thải có mảng tường bê tông): không sinh lại, đặt `edge_left` để tường dán sát mép trái.
- Bài học (đã có trong `config/script_guide.md`): tả bối cảnh trong `action` (tường, cửa, cột) dễ sinh ảnh có bối cảnh vẽ dính; tả trạng thái cơ thể khó vẽ (bụng bầu) thì đổi sang đồ vật thể hiện cùng ý.
- Dựng: 91,5 giây, 49 cảnh. Soát khung giữa từng cảnh: phụ đề viền màu theo người nói (quản đốc đỏ, đàn anh cam, vợ hồng, con gái vàng), ảnh và hiệu ứng đúng.

## 2026-10-07 (tối): đa dạng chuyển động, chuyển cảnh

Người dùng thấy các video lặp lại: nhân vật đứng giữa, nhún (`bounce`), máy quay zoom vào, cắt thẳng giữa các cảnh.
- **13 anim mới** (`build_video.py`, `animate`): `nod`, `shake_no`, `sway`, `tilt`, `breathe`, `shiver`, `hop`, `sink`, `float`, `punch`, `spin_in`, `lean_in`, `rise`.
- **8 motion mới** (`camera`): `punch_in`, `tilt_up`, `tilt_down`, `dolly_left`, `dolly_right`, `focus`, `drift`, `dutch`.
- **Chuyển cảnh** (trước chỉ có cắt thẳng): `fade`, `push_left`, `push_right`, `push_up`, `whip` (lia có nhòe), `zoom`, `flash`, `wipe`, `iris`. Mỗi cảnh nhận khung cuối của cảnh trước và trộn trong 0,3 giây đầu (`[video] transition`); âm thanh không đổi.
- **Tự đa dạng** (`variety.py`): để trống `anim` của nhân vật chính, `motion`, `transition` thì tự chọn: anim theo `emotion`, motion theo `beat`, chuyển cảnh theo đổi bối cảnh/hồi tưởng/nhịp, không lặp 2 cảnh trước; nhân vật nửa người luân phiên giữa, hơi trái, hơi phải. Kết quả cố định theo kịch bản. Bước dựng cảnh báo khi một kiểu lặp 3 cảnh liền.
- `config/script_guide.md` mục 6 viết lại (để trống là mặc định, bảng từ vựng mới); mục 7 thêm đa dạng hình ảnh (cảnh chèn đồ vật, nhìn từ sau lưng, nhìn nghiêng, hai nhân vật, bước vào/rời khung, cảnh trống chuyển thời gian). `steps/01_script.py` cập nhật danh sách.
- Video 003 dựng lại với chế độ tự chọn (bỏ `bounce`, zoom, lia viết tay; giữ `shake`, `exit_*`, `jump` có chủ ý): 15 kiểu anim, 14 kiểu motion, 10 kiểu chuyển cảnh, không cảnh báo lặp.
- Sửa: chuyển cảnh khi đổi bối cảnh lúc đầu luôn ra `push_left` vì chỉ số xoay vòng chia hết cho số kiểu.

**Ảnh lỗi do người dùng phát hiện ở video 003:**
- Cảnh 6: mặt bố vẽ lệch (một mắt) do "looking away" ở khung cận mặt; đổi thành "facing forward ... both eyes visible behind his glasses". Sinh lại.
- Cảnh 57: ví có cái bàn thừa và ảnh trong ví là người khác; prompt mới "nothing else, no table" và tả tấm ảnh giống hệt cảnh 2. Sinh lại.
- Cảnh 14, 15: ảnh có bối cảnh vẽ dính (góc tòa nhà, cột trụ). Thêm vị trí `edge_left`, `edge_right` (dán sát mép trái/phải và mép dưới); cột ở cảnh 15 sát mép trái, nhân vật đứng yên; cảnh 14 bỏ `alt_pose` vì ảnh thứ hai mất túi xách. `variety.py` không gán chuyển động cho lớp sát mép. Quy tắc ghi vào `config/script_guide.md` mục 3.

## 2026-10-07 (chiều): video 003 (2 phút), quy tắc giữ chân người xem

- `config/script_guide.md` thêm mục 8 "Giữ chân người xem (TikTok)": móc câu trong 2 giây đầu, tiêu đề là móc câu, cứ 15-20 giây một câu hỏi mới, twist giả trước twist thật, cài cắm rồi mở nút, kết thành vòng lặp, nhịp nhanh. `steps/01_script.py` gửi kèm cho Claude như các mục khác.
- Video 003 "父の財布の写真" (`videos/003-chichi-no-saifu`): 58 cảnh, 114,3 giây; 7 toàn thân, 29 nửa người, 17 cận mặt; 15 cảnh hai tư thế; 35 lớp hiệu ứng. Cấu trúc: ảnh bé gái lạ trong ví bố → bố ngoại tình? → chủ nhật bố đi bệnh viện, cười với phụ nữ trẻ → cô y tá nhận ra "tôi" → bé gái trong ảnh là "tôi" năm 5 tuổi → bố đọc truyện cho trẻ nằm viện để cảm ơn → kết vòng về tấm ảnh.
- File dựng kịch bản có thêm `reuse`: cảnh dùng lại ảnh đồ vật của cảnh khác (tấm ảnh ở cảnh 2 xuất hiện lại ở twist và cảnh kết), và cảnh hai nhân vật (`[father, me]`, đứng trái phải).
- Nhân vật mới `nurse`, `me_child_sick`; bối cảnh mới `hospital_entrance`, `hospital_hallway`.
- Trước khi gửi Kaggle: 15 câu phụ đề bị tự ngắt giữa từ được đặt chỗ ngắt thủ công; `alt_pose` giảm từ 24 xuống 15 cảnh (quy tắc khoảng 1/4), lô ảnh từ 86 xuống 77 job.
- Kaggle: 77 ảnh, 0 lỗi, khoảng 47 phút. Soát ảnh xem trước thấy 2 lỗi, sinh lại 5 ảnh (khoảng 10 phút):
  - Tấm ảnh bé gái (cảnh 2, dùng lại ở 39 và 58): model vẽ thẳng bé gái, không thành tấm ảnh. Sửa prompt: tả khung ảnh trước ("a single old instant photograph with a thick white border"), rồi nội dung "inside the photo frame". Thêm quy tắc này vào `config/script_guide.md`.
  - Cảnh 55 (bố và con cùng đi): ra 4 người vì `action` "walking side by side" khiến mỗi ảnh riêng vẽ hai người. Sửa thành "walking forward, smiling"; thêm quy tắc "cảnh hai nhân vật tả hành động của một người" vào `config/script_guide.md`.
- Lòng tấm ảnh chụp bị trong suốt (model vẽ bằng màu nền xanh). Thêm tùy chọn lớp `"fill_holes": "#RRGGBB"` (`build_video.py`): tô các lỗ trong suốt nằm gọn bên trong hình, không tô vùng thông ra mép (khoảng trống quanh quai cốc vẫn trong suốt).
- Dựng: 114,2 giây, 58 cảnh, 5 phút. Soát khung giữa từng cảnh: phụ đề viền màu theo người nói (y tá xanh lá, bố cam, mẹ hồng), hiệu ứng đúng chỗ, tấm ảnh nhất quán ở mở đầu, twist và kết.

## 2026-10-07: phụ đề to, hiệu ứng mới, video 002 (90 giây)

**Phụ đề to gấp đôi** (`subtitle_size` 72 → 144). Ở cỡ này mỗi dòng chỉ vừa khoảng 7 chữ, mà libass không tự ngắt dòng tiếng Nhật (không có dấu cách) nên chữ tràn khung.
- `build_video.py` tự ngắt dòng: chia đều các dòng, ưu tiên ngắt sau dấu câu, dấu câu cuối dòng được tràn ra lề; giữ chỗ ngắt `
` do người viết đặt.
- Phụ đề đặt ngay dưới tiêu đề (`subtitle_top = 330`), lề `subtitle_margin = 30`, viền dày theo cỡ chữ.
- `config/script_guide.md`: tối đa khoảng 12 chữ một câu, tự đặt `
` ở chỗ ngắt tự nhiên, không quá 3 dòng (4 dòng sẽ đè lên đầu nhân vật nửa người).

**Hiệu ứng mới, vẽ bằng code** (`effects.py`): `aura` (hào quang), `rays` (tia sáng xoay), `sparkles` (lấp lánh), `hearts` (tim bay lên), `tears` (nước mắt rơi), `speed_lines` (đường tập trung manga), `flash`, `gloom` (phủ tối), `confetti`, `rain`.
- Lớp `{"effect": ..., "on": <id nhân vật>}`: bám theo vị trí, độ phóng to, vị trí đầu của nhân vật; thứ tự trong `layers` quyết định nằm trước hay sau nhân vật.
- `render_frame` tách hai lượt (tính vị trí mọi lớp rồi mới vẽ) để hiệu ứng nằm sau nhân vật vẫn biết nhân vật ở đâu.
- Sửa lỗi cũ: hai sticker cùng ảnh trong một cảnh trùng tên lớp nên bị vẽ chồng một chỗ.
- `check()` trong `build_video.py` kiểm tra kịch bản trước khi dựng (motion, anim, shot, filter, tên hiệu ứng, `on`, vị trí, điểm neo, id lớp được neo, file ảnh); có lỗi thì dừng và báo đúng cảnh.
- Thử cả 10 hiệu ứng trên ảnh thật (`videos/_tests/fx-test`); hào quang, lấp lánh, nước mắt được làm sáng và to hơn sau lần xem đầu.
- `config/script_guide.md` mục 5: khi nào dùng hiệu ứng nào, đặt trước hay sau nhân vật, khoảng 1/3 số cảnh, tối đa 2 mỗi cảnh.

**Video 002 "母のお弁当ノート"** (`videos/002-haha-no-bento`), viết theo `config/script_guide.md`: 52 cảnh, 93,9 giây giọng đọc; 5 toàn thân, 27 nửa người, 11 cận mặt, 9 cảnh đồ vật, 9 cảnh hai tư thế, 33 lớp hiệu ứng. Kịch bản dựng bằng `build_script.py` trong thư mục video (sửa ở đó rồi chạy lại để ra `script.json`).
- Nhân vật mới `me_teen` (cô gái hồi cấp ba), `mother_patient` (mẹ mặc áo bệnh nhân). Trường mới `"ref"` trong `characters.json`: `mother_patient` dùng chung ảnh chuẩn với `mother` để giữ khuôn mặt.
- Áo len của mẹ đổi từ xanh lá sang tím nhạt, tránh trùng màu nền xanh dùng để tách nền.
- Bối cảnh mới: `bedroom`, `classroom`, `hospital_room`.

**Chạy video 002** (`videos/002-haha-no-bento/output.mp4`, 93,9 giây, 52 cảnh):
- Kaggle: 66 ảnh (2 ảnh chuẩn, 52 ảnh cảnh, 9 tư thế thứ hai, 3 nền), 0 lỗi, khoảng 45 phút; lần tải đầu mất kết nối, tự thử lại thành công.
- Ở máy: 61 ảnh tách theo màu nền; dựng 4 phút 42 giây.
- Kiểm tra: trích một khung giữa mỗi cảnh trong video thật. Phụ đề 2-3 dòng không đè mặt; hiệu ứng hiện đúng chỗ, không lỗi vẽ.
- Sửa sau khi xem: hai câu bị tự ngắt giữa từ ("クラスで笑 / われた", "恥ずかし / いみたい"), thêm `
` thủ công rồi dựng lại.
- Còn lại (do model vẽ, không phải lỗi dựng): bìa sổ cảnh 32 vẽ bánh hamburger thay vì hộp cơm; chữ trên trang sổ (39, 51) là chữ vô nghĩa; hộp cơm gói vải cảnh 10 trông như cục vải. Sửa bằng cách đổi mô tả trong `build_script.py`, xóa ảnh cảnh đó, chạy lại `make_jobs.py`, `run_kaggle.py`, `run_local.py`.
- Đoạn hồi tưởng sepia (34-40) có độ tương phản thấp khi kèm hào quang và tia sáng: đúng như thiết kế, không phải lỗi.

## 2026-10-06 (khuya): nền xanh để tách nền, khung hình, quy tắc kịch bản

**Nền xanh lá khi sinh ảnh, tách nền theo màu.** Áo blouse trắng và bọt bia bị trong suốt trong video smoke test.
- Nguyên nhân: ảnh sinh trên nền trắng, model tách nền (rembg) coi chỗ trắng của nhân vật là nền. Đo độ đục: áo blouse 10-20/255, bọt bia 0/255; gần như không pixel nào đục hoàn toàn.
- Thử 4 model (`isnet-general-use`, `isnet-anime`, `birefnet-general-lite`, `u2net`): không model nào vừa giữ áo trắng, vừa giữ bọt bia, vừa làm lỗ quai cốc trong suốt. Màu không phân biệt được: áo, bọt, nền đều ~254/255.
- Thử sinh trên nền trắng, magenta, xanh lá (`videos/_tests/bg-key-test`): model vẽ đúng nền màu đặc, nhân vật giữ nét. Tách theo màu: áo và bọt bia đục 255, lỗ quai cốc trong suốt 0. Xanh lá phẳng hơn (góc ảnh ~(0, 228, 3)), ít nhuộm lên nhân vật hơn magenta (magenta làm da ngả hồng).
- `steps/04_cutouts.py`: ảnh có viền là màu đặc thì tách theo khoảng cách màu (`key_low`, `key_high`), khử màu nền lem vào viền mềm; ảnh nền trắng cũ vẫn dùng rembg.
- `tools/make_jobs.py`: ảnh cảnh và ảnh đồ vật sinh trên nền theo `key_prompt` (`[cutout]`). Ảnh chuẩn nhân vật vẫn nền trắng.
- Còn lại: nhân vật hơi ngả màu nền (váy xanh navy ngả xanh). Áo len xanh lá của bà mẹ gần màu nền; ngưỡng hiện tại vẫn tách đúng trên lý thuyết, cần kiểm tra khi có ảnh thật.
- Thủy tinh trong suốt (cốc rỗng) bị vẽ ngả xanh vì nền xuyên qua. Thêm bước khử ánh màu nền (`despill`): pixel sáng (`spill_min_bright`) mà kênh xanh vượt không quá `spill_max` thì đưa về trung tính. Kết quả: cốc phủ sương trắng trung tính; bố, cô gái, cốc bia không đổi. Màu xanh lá đậm thật (áo len) không đủ sáng nên giữ nguyên.

**Smoke test** (`videos/_tests/smoke-10s`, 8 ảnh nền xanh, có `shot`): Kaggle 7 phút 43 giây; có token Hugging Face, bước tải và mã hóa prompt 1 phút 33 giây (lần trước 1 phút 55 giây). Cả 8 ảnh tách theo màu. Nửa người, cận mặt to và sát mép dưới; áo trắng, bọt bia đục hoàn toàn. Cốc ở cảnh 1 vẫn ra cốc có bia dù prompt ghi cốc rỗng.

**Khung hình theo cảnh và nhân vật to hơn.**
- Trường mới `shot`: `full` (toàn thân), `half` (nửa người từ thắt lưng), `close` (cận mặt và vai). Câu mô tả chèn vào prompt và cỡ, vị trí mặc định nằm ở `[shots]` trong `settings.toml`.
- Lớp nhân vật chính bỏ trống `size`, `at` thì tự lấy theo `shot`. Vị trí mới `floor`, `floor_left`, `floor_right`: lớp đứng sát mép dưới khung (nửa người, cận mặt như máy quay cắt ngang).
- Cỡ `large` 0.42 → 0.52, `huge` 0.50 → 0.62, `medium` 0.24 → 0.28: smoke test cho thấy nhân vật nhỏ, nền thừa nhiều.

**Quy tắc viết kịch bản tách ra `config/script_guide.md`.** Gồm: đồ vật vẽ trong ảnh, chọn khung hình, bố cục, sticker, chuyển động, độ đa dạng. `steps/01_script.py` gửi nguyên văn file này cho Claude mỗi lần viết kịch bản; `review.py` chấm ảnh theo khung hình yêu cầu.

**Kaggle.**
- Token Hugging Face (`config.toml`, `[keys] hf_token`) gửi kèm dataset job riêng tư; kernel đặt `HF_TOKEN` trước khi tải model, log ghi "Token Hugging Face: có/không".
- Tải kết quả tự thử lại 3 lần khi mạng tới máy chủ tải file của Kaggle quá hạn (đã gặp một lần).

## 2026-10-06 (tối): đồ vật vẽ trong ảnh, sticker tự khớp nhân vật

**Bỏ đạo cụ tách rời.** Trước đây mỗi đồ vật (cốc bia, điện thoại, vali) là một ảnh riêng (`props_raw/`, `props/`), đặt lên tay nhân vật bằng điểm neo `hand_left`. Smoke test cho thấy cốc không khớp tay khi nhân vật giơ tay, và mô tả đồ vật riêng dễ sai (cốc rỗng phủ sương ra thành cốc bia đầy).
- Đồ vật nhân vật cầm giờ ghi vào `action` và được vẽ luôn trong ảnh nhân vật, vd `"holding a glass beer mug full of golden beer"`.
- Cảnh không có nhân vật dùng trường mới `object`: một ảnh cho cả nhóm đồ vật, vd `"two glass beer mugs clinking together"`. Ảnh nằm ở `characters/NNN.png` như ảnh nhân vật; lớp đặt `"id": "objects"`.
- Trường `props` không còn dùng; `tools/make_jobs.py` báo lỗi nếu kịch bản còn trường này.
- Đổi ở: `tools/make_jobs.py` (bỏ job `prop_`, thêm mẫu `OBJECT`), `steps/common.py` (`character_files` trả ảnh đồ vật), `steps/04_cutouts.py`, `run_local.py`, `tools/run_kaggle.py`, `tools/make_placeholders.py`, `review.py`, `steps/01_script.py`.
- Đánh đổi: đồ vật không còn chuyển động riêng (cốc lắc riêng trong tay); người dùng chấp nhận.
- Đã chuyển kịch bản: `videos/_tests/smoke-10s` (3 cảnh), `videos/001-futatsu-no-jokki` (15 cảnh: 11 cảnh nhân vật cầm đồ vật, 4 cảnh `object`).

**Sticker tự khớp nhân vật** (`build_video.py`). Trước đây điểm neo tính theo khung chữ nhật của ảnh với khoảng cách cố định (0.08 khung hình), nên sticker đứng xa nhân vật và bị cắt ở mép khung.
- Điểm neo tính từ hình dáng thật của lớp (vùng không trong suốt, hàm `silhouette`): vị trí và bề rộng của đầu, điểm xa nhất của tay ở dải thân.
- `beside_left`, `beside_right`, `above` đặt sticker sát đầu, có tính cỡ của chính sticker; khoảng hở `sticker_gap` trong `[layout]`.
- Lớp đứng yên bằng `at` luôn nằm trọn trong khung (lề `edge_margin`); sticker cạnh đầu mà tràn mép thì đổi sang bên kia đầu.
- Lớp neo vào lớp khác có cỡ tỉ lệ theo lớp đó (nhân vật nhỏ thì sticker và chữ nhỏ).
- Kiểm tra trên ảnh thật của smoke test: dấu hỏi, giọt mồ hôi, trái tim nằm sát đầu, không còn bị cắt; cốc ở cảnh 1 tự tìm đúng bàn tay đang giơ.

**Smoke test sau thay đổi** (`videos/_tests/smoke-10s`, 3 ảnh sinh lại trên Kaggle, khoảng 10 phút gồm thời gian chờ cấp GPU):
- Cảnh 4: ảnh hai cốc bia chạm nhau sinh trong một ảnh, chữ "カチン" neo phía trên.
- Cảnh 6: hai cốc rỗng phủ sương ra đúng mô tả (bản đạo cụ rời trước đây ra cốc bia đầy).
- Cảnh 1: bố cầm sẵn cốc trong tay, nhưng model vẫn vẽ cốc có bia dù prompt ghi cốc rỗng; cần thử mô tả khác nếu chi tiết này quan trọng.
- Video 9.2 giây dựng lại trong khoảng 35 giây.

**Theo dõi lần chạy Kaggle.**
- Log của kernel có giờ cho từng giai đoạn và từng ảnh (`kaggle_job/kernel_main.py`, `kaggle_job/worker.py`). Kaggle chỉ trả log khi chạy xong; log nằm ở `videos/<tên>/work/kaggle/shorts-gen.log`.
- Thời gian chờ ảnh tham chiếu tối đa `ref_wait = 900` giây (trước là 1 giờ).
- Mỗi lần chạy có giới hạn `run_timeout_minutes = 90` (`config.toml`), quá hạn Kaggle tự dừng.
- Ghi nhận: một lần chạy bị treo hơn 25 phút không rõ lý do (chưa có log), phải xóa kernel để dừng. Lần chạy lại với 10 ảnh mất khoảng 14 phút: 3 phút chờ cấp máy, 47 giây cài thư viện, 2 phút mã hóa prompt, 1 phút nạp model, 6 phút sinh ảnh (55-87 giây mỗi ảnh). Trạng thái `queued` nghĩa là đang chờ Kaggle cấp GPU.

## 2026-10-06 (chiều): hai tư thế luân phiên, kiểu di chuyển mới

- `alt_pose` của cảnh: sinh thêm `characters/<cảnh>_alt.png` sửa từ ảnh gốc của cảnh; khi dựng đổi qua lại mỗi `alt_interval` (0.25 giây). Chỉ đặt cho cảnh cần cử động (đi, nói, vẫy tay).
- Kiểu `anim` mới: `exit_left`, `exit_right`, `approach`, `recede`, `jump`.
- Lớp neo vào lớp khác đi theo chuyển động và độ phóng to của lớp đó (vali đi ra cùng nhân vật).
- `run_kaggle.py`: cho phép chuỗi tham chiếu nhiều tầng (ảnh chuẩn → ảnh cảnh → tư thế thứ hai), vì mỗi worker chạy job theo thứ tự trong `jobs.json`; thêm kiểu tham chiếu `char__<file>` cho ảnh gốc đã có ở `characters/`.
- `make_jobs.py`: ảnh bị `review.py` loại thì đổi seed khi sinh lại.
- Smoke test 10 giây (`videos/_tests/smoke-10s`): chạy trọn workflow, ra video 9.2 giây; nhân vật giống nhau giữa các cảnh, nhép miệng bằng `alt_pose` chạy đúng.

## 2026-10-06 (trưa): tự động hóa và cây thư mục cho nhiều video

- `tools/make_jobs.py`: tạo `jobs.json` từ `script.json` (ảnh chuẩn, ảnh cảnh, ảnh nền), không gọi Claude.
- `tools/run_kaggle.py`: tải kết quả về `work/kaggle/` và tự chép theo tiền tố tên job; thêm `--fetch`.
- Ảnh chuẩn nhân vật (`config/refs/`) và ảnh nền (`library/backgrounds/`) dùng chung mọi video.
- Cây thư mục: mỗi video chỉ chứa đầu vào, ảnh riêng, giọng đọc, `output.mp4`; file tạm vào `work/`. Video thử vào `videos/_tests/`, tài liệu train vào `train/`.
- Xóa bước sinh ảnh ở máy (`steps/02_backgrounds.py`, `steps/03_characters.py`): máy local không đủ RAM.

## 2026-10-06 (sáng): thông số tách riêng, nền LoRA 0.8

- Mọi thông số chỉnh được chuyển vào `config/settings.toml`; `config.toml` chỉ còn tài khoản và khóa.
- Ảnh nền dùng style LoRA cố định 0.8 với prompt nét phẳng, sau khi so 0 / 0.5 / 0.8 / 1.0 (`videos/_tests/000-bg-test/so_sanh_nen.png`).
- Worker trên Kaggle nhận cường độ LoRA theo từng job (`"lora": 0.8`).

## 2026-10-06: chạy trên Kaggle qua API

- Nhận gói bàn giao thứ hai (`HANDOFF.md`): LoRA checkpoint 750, sinh ảnh qua kernel Kaggle.
- `run_kaggle.py`: chọn GPU T4 x2 (`machine_shape: NvidiaTeslaT4`), đăng nhập bằng token mới của Kaggle CLI, chờ đúng lần chạy mới, tải `embeds.pt` không về máy.
- Lô thử 6 ảnh đầu tiên: 6/6 ảnh, hai GPU đều chạy, khoảng 8 phút.

## 2026-10-05: dựng khung dự án

- Gói bàn giao thứ nhất: `build_video.py` (dựng theo lớp), `review.py`.
- Viết `steps/01_script.py`, `04_cutouts.py`, `06_voice.py`, `run_local.py`; kịch bản tiếng Nhật video 001; bộ sticker; giọng đọc edge-tts.
- Chạy thử toàn bộ phần ở máy với ảnh giữ chỗ (`videos/_tests/000-dry-run`): 48 cảnh, 79.7 giây.
- Đổi model tách nền sang `isnet-general-use` (mặc định của rembg mất ~15 giây/ảnh, ~13GB RAM).
