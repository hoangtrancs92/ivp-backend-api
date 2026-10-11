# Lịch sử thay đổi

Mỗi mục: ngày, thay đổi gì, vì sao, và kết quả kiểm tra. Mục mới nhất ở trên.
Quyết định đang có hiệu lực được tóm tắt ở bảng "Quyết định đã chốt" trong `README.md`.

## 2026-10-11: video tối thiểu 61 giây (cảnh cuối giữ thêm)

Người dùng: video 048 dài 57,4 giây, cần lên 60 giây. Video so sánh đọc nhanh (`voice_speed`) và không tự đọc chậm lại nên hụt.
`build_video.py`: trước khi dựng tính tổng giọng + nghỉ; thiếu so với `[video] min_seconds` (61, `settings.toml`) thì cảnh cuối
(câu hỏi cho người xem) giữ thêm phần thiếu (`_hold`), không chèn khoảng nghỉ giữa video. Áp cho mọi video.
Kiểm tra: dựng lại 048: cảnh cuối giữ thêm 3,6 giây, ffprobe 60,97 giây (TikTok làm tròn 61).

## 2026-10-11: nhạc nền video 048 nhỏ lại

Người dùng: nhạc nền video 048 (so sánh, bài comical/retroparty, 14 dB dưới giọng) to quá chút. `build_video.py`: trường
`"music_quieter": N` trong script.json hạ nhạc thêm N dB cho riêng video đó. Video 048 đặt 4 dB, dựng lại: âm lượng nhạc
x0,145 -> x0,091 (57,4 giây, 50 cảnh). Bản cũ: `work/output_nhac_to.mp4`.

## 2026-10-11: ảnh thật từ Wikimedia Commons

Người dùng muốn thêm kho ảnh, chọn Wikimedia Commons và không muốn tự ghi nguồn. Ảnh xe trên Wikimedia hầu hết là CC BY-SA 4.0;
người dùng chọn "lấy cả CC BY-SA, tự lưu nguồn" (đã báo: CC BY / BY-SA đòi ghi tác giả, dùng vài giây cũng vậy).
- `steps/fetch_photos.py`: nguồn Wikimedia (API không cần khóa, có User-Agent), chỉ giấy phép công cộng / CC0 / CC BY / CC BY-SA
  (bỏ NC, ND, không rõ); nhãn = tên file + thể loại + mô tả; ưu tiên ảnh ngang. Thứ tự tìm: Pixabay, Pexels, Wikimedia; từ khóa
  có tên hãng thì Wikimedia trước (Pixabay "toyota prius" ra ảnh khoang máy). Không có khóa nào vẫn tìm được ở Wikimedia.
- Nguồn ảnh Wikimedia: `photos/credits.json` (tác giả, giấy phép, link) và dòng 「写真: tác giả / giấy phép (link)」 trong
  `credits.txt` của video. `06_voice.py` đọc credits.txt theo dòng (trước tách theo khoảng trắng, sẽ làm vỡ dòng nguồn ảnh).
- Trang Cài đặt: ghi rõ Wikimedia luôn được tìm thêm.
Kiểm tra (khóa Pixabay thật): "byd dolphin" ra BYD Dolphin (CC BY-SA), "geely coolray" ra Geely Coolray (CC BY), "toyota prius"
ra Prius đời XW60 (sau khi đổi thứ tự); credits.txt có 2-3 dòng nguồn.

## 2026-10-11: ảnh thật theo tên hãng / mẫu xe

Người dùng chụp màn hình Pixabay có ảnh Hyundai Tucson, muốn dùng ảnh đúng hãng làm ví dụ.
- `steps/01_script.py` (kaigai): được ghi hãng + mẫu (Toyota, Hyundai, BYD...) khi khen hoặc nêu thông tin trung lập / có thật
  (giá, kích thước, năm, đặc điểm); lời chê chung không gắn tên một hãng / mẫu cụ thể; hãng phải đúng nước (Hyundai, Kia là Hàn
  Quốc; BYD, Geely, Chery là Trung Quốc). Từ khóa ảnh được có tên hãng + mẫu trong các cảnh đó.
- `steps/fetch_photos.py`: từ khóa có tên hãng (`BRANDS`) thì ảnh bắt buộc có đúng tên đó trong nhãn, không có thì bỏ trống cảnh
  ảnh (thử "byd electric car" ra Tesla Model 3 trước khi sửa).
Kiểm tra với khóa thật: "hyundai tucson" ra Tucson (đúng ảnh người dùng gửi), "toyota corolla" ra Toyota GR Corolla, "byd electric
car" sau khi sửa: không có ảnh (thay vì Tesla).

## 2026-10-11: khóa Pixabay, chọn ảnh khớp từ khóa hơn

Người dùng gửi khóa Pixabay: lưu ở `data/settings.json` (`pixabay_key`, thư mục data/ nằm trong .gitignore). Gọi API thật lần đầu:
tải được ảnh nhưng lạc đề (ảnh dọc đầu tiên: "old car mountain road" ra xe Tesla trong phố, "used car dealership" ra đuôi xe
Cadillac). `steps/fetch_photos.py: search`: ưu tiên ảnh ngang (khung polaroid ngang 9:7, nhiều kết quả hơn), lấy 40 kết quả và
chọn ảnh có nhãn khớp nhiều từ khóa nhất. Thử lại 3 từ khóa: xe cổ trên đường núi, xưởng sửa xe đúng ý; "used car dealership" vẫn
ra bãi lốp xe (kho Pixabay ít ảnh này) -> người duyệt bỏ ảnh, lần sau lấy ảnh khác.

## 2026-10-11: video so sánh: nhịp nhanh, không khoảng lặng, có tiếng hiệu ứng, nhạc vui cố định, bỏ clip AI

Người dùng xem video 045: không có tiếng hiệu ứng, nhạc phải vui / kịch tính / hài (cố định cũng được), nhịp chậm, có khoảng nghỉ,
không cần clip AI. Đo video 045: 9 cảnh không lời (thẻ so sánh 2,57 giây, clip 3,07 giây) = ~25 giây im trên 71,8 giây (lỗi do
`silent_seconds` thêm sáng nay); nhạc tắt 3 lần cuối video; tiếng tự gắn rất thưa (`SFX_SPARSE_SHARE` 10%), kịch bản không ghi `sfx`.
- `steps/01_script.py` (kaigai): bỏ cảnh clip AI (cảnh minh họa là ghép lớp); MỌI cảnh có lời (thẻ so sánh đọc to kết quả),
  câu 6-16 ký tự, thoại dồn dập; ghi `"sfx"` ở cảnh thẻ / khoe / cứng họng (danh sách tiếng có sẵn). Sau khi AI viết: bỏ
  `full`, `motion_level`, `i2v_prompt`; thẻ so sánh không lời thì tự đặt câu 「耐久性、日本20年、中国8年！」; `bgm` cố định
  `comical/retroparty.mp3`, `voice_speed` 1.35.
- `steps/06_voice.py`: tốc độ VOICEVOX lấy `voice_speed` của kịch bản và không tự đọc chậm lại cho đủ 62 giây; cảnh thẻ không lời
  im 1,2 giây (trước 2,5), bỏ mức 3 giây của cảnh clip.
- `build_video.py`: thẻ so sánh tự có tiếng `jan` lúc bật ra và `correct` / `wrong` / `boyon` theo bên thắng; `bgm` nhận
  "nhóm/file.mp3"; video so sánh (`country`) không tắt nhạc giữa chừng. Nhạc nhóm comical đã to hơn (14 dB dưới giọng).
Áp cho video mới; video 045 không dựng lại. Kiểm tra: đủ 15 tiếng có trong library/sfx/lab; sfx_events thẻ Nhật thắng ra
jan + correct; pick_music ra retroparty; music_breaks rỗng. Chưa nghe bài retroparty, chưa viết kịch bản thật với luật mới.

## 2026-10-11: ảnh thật (Pixabay, Pexels dự phòng) cho video Nhật Bản vs nước khác; sửa dựng cảnh clip AI

**Ảnh thật.** Người dùng muốn ảnh thật cho trực quan, áp cho video mới. Pexels đang tạm ngừng cấp khóa API mới (người dùng
chụp màn hình pexels.com/api/key) nên dùng Pixabay trước, Pexels khi có khóa.
- `steps/fetch_photos.py` (mới): cảnh `"photo": {"query", "caption"}` -> `photos/NNN.jpg` + `credits.json` (nguồn, tác giả,
  link); ảnh dọc trước, không có thì ngang; bỏ ảnh có id trong `rejected_ids.json`. Không khóa / lỗi mạng: cảnh dựng không ảnh.
- `tools/auto.py`: bước "Ảnh thật (Pixabay / Pexels)" ngay trước Duyệt ảnh (lỗi không chặn video).
- `steps/common.py`: ảnh thật hiện trong duyệt ảnh (loại "Ảnh thật"); bỏ ảnh thì ghi id bị bỏ, lần chạy sau lấy ảnh khác.
- `compare.py: photo_card`: khung polaroid (viền trắng, chú thích tiếng Nhật, nghiêng 3°, bóng đổ). `build_video.py`: cảnh
  có ảnh chèn khung như thẻ so sánh (y 0.45, cỡ 0.34), linh vật hai bên, máy đứng yên.
- `steps/01_script.py` (kaigai): 3-5 cảnh ảnh thật, từ khóa tiếng Anh chung (không tên hãng, người nổi tiếng, cờ, bản đồ).
- Trang Cài đặt AI: ô khóa Pixabay và Pexels (admin, không gửi về trình duyệt); server truyền `PIXABAY_API_KEY`,
  `PEXELS_API_KEY`.
Kiểm tra: dựng xem trước một cảnh với ảnh thay thế: khung ảnh giữa, hai linh vật hai bên; `search` Pixabay với dữ liệu giả bỏ
đúng ảnh bị loại. **Chưa gọi API thật** (chưa có khóa).

**Dựng cảnh clip AI** (video 045 dừng ở Dựng video, lần đầu có clip thật): `clip_backgrounds` gọi `ffprobe` / `ffmpeg` qua
`run()` vốn tự thêm `ffmpeg -y` ở đầu, ra lệnh `ffmpeg ffprobe ...`. Gọi thẳng `subprocess.run`. Kiểm tra: đọc được
`clips/025.mp4`, `044.mp4` (121 khung, 576x1024 -> 1080x1920).

## 2026-10-11: chặn lỗi của video 044, 045 từ lúc viết kịch bản cho các video sau

Người dùng: áp những sai sót đã gặp để cải thiện các video sau.
- `steps/01_script.py`: quy tắc lớp ảnh chủ thể ghi rõ tên nhân vật đầy đủ (`cutouts/012_mascot_chn.png`, không viết tắt), mỗi
  nhân vật một lớp, `"text"` luôn là chuỗi (cảnh không lời ghi ""). `fix_subject_layers()` chạy ngay sau khi AI viết: đổi tên
  viết tắt về đúng tên file, tách lớp gộp nhiều nhân vật; kịch bản ghi ra đã đúng nên các bước sau (make_jobs, duyệt ảnh, dựng)
  không phải đoán. Thử trên kịch bản 045: sửa 15 chỗ (1 lớp gộp, 14 tên viết tắt).
- `web/app.py`: `state` trả `stale` khi app.py sửa sau giờ server khởi động; trang web hiện dải cảnh báo "khởi động lại
  chay_web.bat" (video 044 chạy bằng server cũ). Có tác dụng từ lần khởi động lại tới.
- Các sửa ở bước dựng (text null, thời lượng cảnh không lời, xếp chỗ hai linh vật, máy quay êm) đã nằm trong code, áp cho mọi video.

## 2026-10-11: video 045 (xe Nhật vs xe Trung Quốc) dừng ở "Bố cục cảnh"; sửa bố cục hai linh vật

Lô Kaggle đầu tiên của kiểu so sánh chạy được: 2 linh vật (中国くん giống ảnh mẫu; 日本くん đầu bản đồ dài mảnh, mặt hơi lạ),
cảnh ghép, 3 tranh minh họa, 2 clip AI (`clips/025.mp4`, `044.mp4`). Bước xem trước lỗi, sửa lần lượt:
- 9 cảnh không lời (thẻ so sánh, clip) có `"text": null` -> `variety.fill` lỗi `TypeError`. `common.normalize_script`: text
  không phải chuỗi thành `""`. `06_voice.py: silent_seconds`: cảnh không lời có thẻ so sánh im 2,5 giây, cảnh clip 3 giây
  (trước 0,5 giây mọi cảnh, quá ngắn để đọc thẻ / xem clip).
- Kịch bản ghi tên viết tắt `cutouts/047_chn.png` (file thật `047_mascot_chn.png`): `repair` tìm theo id lớp / đuôi tên.
- Kịch bản gộp hai linh vật vào một lớp không có thật `cutouts/006_mascot_jpn_mascot_chn.png`: `split_group_layer` tách thành
  một lớp mỗi nhân vật (chỉ khi cảnh có đúng một lớp nhân vật; lần đầu chạy cả khi đủ lớp nên sinh lớp trùng, đã sửa), chạy
  trước bước xếp chỗ thẻ so sánh.
- Hai linh vật che nhau (đầu bản đồ Trung Quốc gần vuông): cảnh có 2 linh vật đứng x 0.27 / 0.73, cảnh có thẻ đứng 0.25 / 0.75;
  cỡ giới hạn để mỗi lớp rộng tối đa nửa khung (`half_width`, đọc được cả tên viết tắt chưa sửa); máy lia / zoom mạnh đổi thành
  `zoom_in`, bỏ `focus`.
Kiểm tra: `build_video.py --preview` video 045 ra đủ 52 khung; xem bằng mắt cảnh 1, 6, 12, 18, 25, 47, 52.

## 2026-10-11: video 044 dừng ở viết kịch bản

Server web vẫn chạy code từ 10/10 9:42 (chưa khởi động lại) nên video 044 lưu `story_mode: auto`, `style: new`, không có `country`:
AI nhận lời dặn bí mật + cú lật cho đề tài so sánh xe, trả lời bằng đoạn giải thích trước JSON và `json_reply` báo hỏng.
- `steps/llm.py: json_reply`: không đọc được khối từ "{" đầu tới "}" cuối thì thử từng "{", lấy đối tượng JSON hợp lệ lớn nhất.
- Sửa `videos/044-so-sanh-xe-hoi-nhat/meta.json` thành kaigai / classic / CHN như người dùng chọn.
Kiểm tra: json_reply với câu trả lời có chữ và ngoặc trước khối ```json. Cần khởi động lại server rồi bấm Chạy tiếp.

## 2026-10-11: Nhật Bản vs nước khác: bỏ tranh tĩnh, ghép lớp có chuyển động + clip AI + thẻ so sánh

Người dùng: video so sánh không nên là tranh tĩnh; chọn "kết hợp cả hai" (ghép lớp có chuyển động và vài clip AI); "Tương phản →
Ngẫu nhiên" giữ tranh tĩnh như ô 2.
- Web: "Nhật Bản vs nước khác" gửi `style: classic` (ghép lớp), các ô khác như cũ.
- `steps/01_script.py` (kaigai): cảnh hai linh vật là ghép lớp thường (anim sôi động, hiệu ứng, chữ tượng thanh); mỗi hiệp một cảnh
  `"compare"`; cảnh kết `"round": "最終結果"`; 3-4 cảnh minh họa `"full": true, "motion_level": "low", "i2v_prompt"` (clip AI
  Wan 2.2 trên Kaggle, hạ tầng từ 10/10), không đặt linh vật vào cảnh clip (dễ méo đầu bản đồ). Ghi `script.json "country"`.
- `compare.py` (mới): thẻ so sánh vẽ bằng code: dải tên hiệp, tên chỉ số, hai cột cờ + tên nước + giá trị, cột thắng tô vàng có
  vương miện, tỉ số dưới cùng. `build_video.py`: cảnh có `"compare"` chèn thẻ (y 0.45, cỡ 0.3, pop), máy đứng yên, hai lớp linh
  vật tự đặt hai bên dưới thẻ (cỡ 0.32); `"country"` lấy từ script.json.
Kiểm tra: vẽ 3 thẻ mẫu (耐久性 Nhật thắng, 価格 Trung Quốc thắng, 最終結果 với Hàn Quốc); dựng xem trước video thử 3 cảnh bằng ảnh giữ
chỗ: thẻ trọn trong khung, hai linh vật hai bên. Benchmark clip 10/10: ~170-220 giây / clip 576x1024 / seed trên T4, mỗi cảnh 2
seed. **Chưa chạy** một video so sánh thật trên Kaggle (linh vật, cảnh ghép, clip).

## 2026-10-11: "Nhật Bản vs nước khác" thành video so sánh đối đầu (không còn là truyện kể)

Người dùng: đề tài so xe Nhật với xe Trung Quốc "không giống kể chuyện". `steps/01_script.py` `STORY_MODES["kaigai"]` viết lại:
日本くん vs 〇〇くん (hai linh vật) đối đầu 4-6 hiệp theo chủ đề người dùng nhập (giá, độ bền, an toàn, bán lại...), mỗi hiệp
có chữ tên hiệp, nước kia khoe, 日本くん đáp bằng chi tiết / con số, nước kia được thắng 1 hiệp nhỏ để còn tranh cãi; kết tỉ số
Nhật thắng áp đảo + câu hỏi cho người xem. Không nêu tên hãng thật để chê; số chỉ lấy từ đề tài hoặc số liệu World Bank khi liên
quan chủ đề (lời dặn số liệu thêm "chỉ khi liên quan"). Gợi ý trên web đổi theo. Kiểm tra: nạp 01_script (kaigai, CHN) có lời
dặn mới; build web. Chưa viết kịch bản thật.

## 2026-10-11: "Tương phản" viết dàn ý trước; linh vật quốc gia (đầu bản đồ + cờ)

1. **Dàn ý trước kịch bản.** Người dùng: tương phản (kể cả ngẫu nhiên) phải dựa trên đề tài nhập vào, chỉnh theo quy tắc móc câu,
   tương phản rồi mới gửi AI viết kịch bản. `steps/01_script.py: brief()`: với `contrast` và `kaigai`, gọi AI một lần viết dàn
   ý 7 mục (hai phe và lý lẽ, câu hỏi tranh cãi, kiểu móc câu + câu cảnh 1-2, các nấc, twist giả / thật, câu kết, tiêu đề) từ
   đề tài + quy tắc (+ số liệu); lưu `work/brief.md` (chạy lại dùng lại); kịch bản viết từ đề tài + dàn ý. `CONTROVERSY` dặn
   giữ đúng đề tài người dùng. Lỗi AI ở bước dàn ý thì viết thẳng từ đề tài.
2. **Linh vật quốc gia** (theo ảnh mẫu người dùng gửi: đầu là bản đồ Trung Quốc tô cờ, thân nhỏ). `tools/country_mascot.py`:
   đầu vẽ bằng code từ đường biên thật (Natural Earth 1:50m, tải một lần vào `library/maps/`) tô cờ thật (flagcdn.com): cờ có
   màu nền chính (Nhật, Trung, Hàn, Việt) đặt hoa văn vào khối chính của bản đồ, cờ sọc (Mỹ, Pháp, Nga, Đức) trải theo hình
   nước; bỏ đảo xa / lãnh thổ hải ngoại. Ra `config/refs/mascot_<nước>_head.png` và mục `characters.json` `mascot_<nước>`
   (`head_ref`). `tools/make_jobs.py`: ảnh chuẩn linh vật sửa từ ảnh đầu đó (`MASCOT_CAST`), giữ nguyên hình bản đồ và cờ, thêm
   mặt, thân. Kiểu kaigai tự thêm `mascot_jpn` và linh vật nước đem so, dặn AI cho hai linh vật dẫn chuyện (mở đầu, so số liệu,
   kết; ít nhất 1/3 số cảnh).
Kiểm tra: ảnh đầu 9 nước (xem bằng mắt); `mascots()` + `brief()` (AI giả) chạy; make_jobs ra `ref_mascot_jpn`, `ref_mascot_chn`
có tham chiếu ảnh đầu, cảnh 2 linh vật tham chiếu cả hai; `run_kaggle.py --dry-run` qua. **Chưa sinh trên Kaggle**: chưa biết
model có giữ đúng hình bản đồ khi thêm thân không.

## 2026-10-11: 3 ô cách dựng; Tương phản: ngẫu nhiên / Nhật Bản vs nước khác có số liệu thật

Người dùng: giao diện rối; muốn 3 ô: (1) Dựng hiện tại, (2) Tĩnh có anime, (3) Tương phản với lựa chọn ngẫu nhiên hoặc Nhật Bản
so với một nước (chọn nước, tìm số liệu rồi tân bốc Nhật).
- Web (`Studio.jsx`, `api.js: BUILD_MODES, CONTRAST_KINDS, COUNTRIES`): 3 thẻ; chọn "Tương phản" thì hiện hàng chip
  🎲 Ngẫu nhiên / 🗾 Nhật Bản vs nước khác + ô chọn nước (13 nước). Gửi `style`, `story_mode`, `country` như cũ:
  1 = classic + auto; 2 = new + twist; 3 = new + contrast (ngẫu nhiên) hoặc kaigai (so nước). Bỏ hàng "Kiểu chuyện" 6 lựa chọn.
- `steps/compare_facts.py` (mới): số liệu World Bank (API miễn phí, không khóa) Nhật vs nước chọn: tuổi thọ, tỉ lệ giết người,
  tử vong giao thông, tử vong trẻ sơ sinh, PM2.5, vệ sinh, nước sạch, thất nghiệp, GDP đầu người, internet; giá trị mới nhất.
- `steps/01_script.py`: `SHORTS_COUNTRY` (meta.json `country`); kiểu kaigai kể qua người nước đó (trước cố định Trung Quốc);
  `facts_note()` đưa các chỉ số Nhật hơn vào lời dặn, chỉ được dùng đúng số này (không bịa). Kiểu mới `contrast` = bí mật +
  cú lật + `CONTROVERSY`. Ô 2 (twist) **không còn** lời dặn gây tranh cãi (trước áp cho mọi kịch bản cách dựng mới).
- `web/app.py`: nhận `contrast`, lưu `country`, truyền `SHORTS_COUNTRY`.
Kiểm tra: nạp 01_script với 4 tổ hợp (kaigai/KOR, contrast, twist, classic) đúng lời dặn; Hàn Quốc ra 6 chỉ số Nhật hơn
(tuổi thọ 84,04 / 83,63, giết người 0,23 / 0,48...). Build web, chụp màn hình 3 ô + chọn nước. Chưa viết kịch bản thật.

## 2026-10-11: gom "Cách dựng" và "Kiểu chuyện" thành một khối

Người dùng: hai hàng thẻ lớn (2 cách dựng + 6 kiểu chuyện) tràn lan, khó chọn. `Studio.jsx`: kiểu chuyện thành hàng chip gọn
(biểu tượng + tên) nằm ngay dưới hai thẻ cách dựng, trong một khung; một dòng giải thích của kiểu đang chọn (cách dựng mới +
AI tự chọn: "bí mật + cú lật, có tranh cãi hai phe"). CSS `.story-picker` (điện thoại: chip xuống dòng).
Kiểm tra: build web, chụp màn hình trang Tạo video ở cả hai cách dựng.

## 2026-10-11: kiểu chuyện "Người nước ngoài khen Nhật" (海外の反応); chọn kiểu chuyện lại trên trang Tạo video

Người dùng muốn video so sánh Trung Quốc với Nhật rồi tôn Nhật, chê nước khác cũng được.
- `steps/01_script.py`: `STORY_MODES["kaigai"]`: người nước ngoài (mặc định Trung Quốc) sang Nhật, mỗi nấc một cú sốc văn hóa
  cụ thể, so với quê nhà; được chê hệ thống, dịch vụ, thói quen, tình trạng xã hội của nước đó; không miệt thị con người theo
  dân tộc, không từ xúc phạm, chính trị, chiến tranh, lịch sử, lãnh thổ, người thật (để video không bị gỡ vì nội dung thù ghét).
  Có nhân vật đồng hương cãi lại để tạo hai phe; kết bằng quyết định ở lại hoặc câu hỏi cho người xem.
- Cách dựng mới dùng kiểu chuyện người dùng chọn ("AI tự chọn" = bí mật + cú lật như trước). Lời dặn gây tranh cãi
  (`CONTROVERSY`) áp cho mọi kiểu trừ 海外の反応 (kiểu này có luật riêng về so sánh nước).
- Web: hàng "Kiểu chuyện" trên trang Tạo video (cạnh "Cách dựng"), gửi `story_mode`; `web/app.py` nhận thêm `kaigai`.
Kiểm tra: nạp `01_script.py` với kaigai ở cả hai cách dựng có lời dặn 海外の反応 và không có `CONTROVERSY`; cách dựng mới mặc
định vẫn twist + tranh cãi. Build web, chụp màn hình trang Tạo video: đủ 6 kiểu chuyện. Cần khởi động lại server để nhận `kaigai`.

## 2026-10-11: móc câu mạnh ở 3 giây đầu

Người dùng: cần hook mạnh cho những giây đầu. Áp cho mọi cách dựng.
- `steps/01_script.py`: lời dặn `HOOK` gửi kèm mọi kịch bản: cảnh 1-2 `"beat": "hook"`; cảnh 1 là câu mạnh nhất video, tối đa
  12 ký tự, không chào / giới thiệu / bối cảnh; chọn một trong 5 kiểu (nhảy tới khoảnh khắc căng nhất rồi 「3日前――」, câu thoại
  sốc giữa trận cãi, sự thật lạ, chi tiết cụ thể gây tò mò, câu hỏi chọn phe); cảnh 2 làm câu hỏi lớn hơn; cảnh 1 cận mặt,
  cảm xúc mạnh. Schema thêm beat `hook`.
- `variety.py`: cảnh đầu chưa ghi `motion` thì `punch_in` (giật zoom vào ngay), kể cả tranh cả cảnh.
- `build_video.py`: cảnh đầu có tiếng nện `dodon` ngay giây 0 (nếu kịch bản không ghi tiếng khác).
Kiểm tra: `variety.fill` cho cảnh đầu `punch_in`; `sfx_events` cảnh đầu ra `dodon` ở 0 giây; `01_script.py` nạp được.
Chưa viết kịch bản thật, chưa dựng video trọn vẹn với thay đổi này.

## 2026-10-11: cách dựng mới: kịch bản tương phản, gây tranh cãi

Người dùng: kịch bản cách dựng mới phải có tương phản, gây tranh cãi để người xem chia hai phe và bình luận.
`steps/01_script.py`: thêm `CONTROVERSY` vào lời dặn của cách dựng mới (`NEW_STYLE`): một câu hỏi đạo đức đời thường
「どっちが悪い？」, hai nhân vật đối lập rõ, mỗi bên có lý và có lỗi, không phản diện thuần túy; cú lật cuối làm đổi phe;
tiêu đề dòng 2 nêu thế giằng co; câu hỏi ngắn cho người xem (「あなたなら、どっちの味方？」). Chỉ chuyện đời thường, không
chính trị, tôn giáo, dân tộc, miệt thị, người thật. Cách dựng cũ không đổi.
Kiểm tra: nạp `01_script.py` với `SHORTS_STYLE=new` thì lời dặn có phần mới; với `classic` thì không. Chưa viết kịch bản thật.

## 2026-10-11: tư thế thứ hai của nhân vật anime

Video 043 dừng ở "Sinh ảnh trên Kaggle" ngay khi kiểm tra jobs.json (chưa gửi Kaggle, không tốn giờ GPU): `ch_002_alt`
(tư thế thứ hai của nhân vật anime `linh_anime`) mặc định LoRA Irasutoya 1.0 trong khi ảnh gốc `ch_002` không LoRA, nên
`run_kaggle.py` báo "cường độ LoRA thấp hơn, sẽ bị sinh sau". `tools/make_jobs.py`: tư thế thứ hai của nhân vật anime dùng
lời vẽ anime và `lora` 0 như ảnh gốc. Kiểm tra: tạo lại jobs.json của 043 (55 job), `run_kaggle.py --dry-run` qua.

## 2026-10-10 (tối): khôi phục mã nguồn bị lùi về 8/10; skit có nhạc nền; nữ anime gợi cảm ở cách dựng mới

**Sự cố.** Khoảng 18:00 ngày 10/10 toàn bộ mã nguồn bị lùi về commit `f2e24af` (8/10 sáng): mất phần tiểu phẩm (`skit/*.py`,
`Skits.jsx`, phần server), cách dựng mới (`phone.py`, tranh cả cảnh), nhân vật anime, clip image-to-video. Trang web vẫn chạy
nhờ bản build cũ, nhưng phiên sửa tối 10/10 build lại web từ mã nguồn thiếu nên phần tiểu phẩm biến mất khỏi giao diện.
**Khôi phục** từ bản sao lưu file của Claude Code (`~/.claude/file-history`, phiên 8-9/10 và sáng 10/10), rồi chạy lại các lệnh
sửa file không có bản sao lưu (lấy nguyên văn trong nhật ký phiên): `effects.py` (ký hiệu cảm xúc, chữ tượng thanh rải quanh đầu),
`run_local.py`, lệnh cuối phiên 9/10 (`patch_cover.py`: dời tranh cả cảnh xuống dưới phụ đề), và phiên clip sáng 10/10
(`kernel_main.py`, `run_kaggle.py`, `make_jobs.py`, `build_video.py`, `[i2v]` trong settings.toml, `tools/i2v_bench.py`).
Bản trước khi khôi phục cất ở thư mục tạm của phiên (`scratchpad/before_restore`).
Kiểm tra: so với file `.pyc` còn sót (dịch từ bản cuối trước sự cố): `skit/build.py`, `skit/jobs.py`, `skit/sounds.py`, `phone.py`,
`effects.py`, `kernel_main.py`, `run_kaggle.py`, `i2v_runner.py`, `i2v_bench.py`, `tools/auto.py`, `fix_scenes.py`... khớp từng lệnh.
Build lại web ra đúng tên file của bản cũ (`index-Dka3NNWG.js`), tức mã giao diện giống hệt. Dựng xem trước video 033 (42 cảnh)
và `_tests/smoke-10s` chạy được.
Chưa kiểm chứng được: file chỉ sửa bằng tay ngoài Claude Code (không có bản sao lưu); `README.md` không có bản sao lưu.

**Skit có nhạc nền.** `skit/add_music.py` trộn nhạc `library/bgm/comical` (đổi bằng `"bgm"` trong skit.json) vào output.mp4,
nhỏ hơn giọng `music_below_voice` dB; `skit/auto.py` gọi sau bước dựng. Bản không nhạc: `work/output_khong_nhac.mp4`;
`work/music_done.txt` ngăn trộn hai lần. Skit 005 đã trộn tay. Chưa chạy trong một lần tạo skit thật.

**Cách dựng mới: nữ trẻ đẹp nét anime gợi cảm.** `steps/01_script.py`: lời dặn cách dựng mới cho phụ nữ trẻ đẹp (mẹ trẻ, người
mẫu, siêu mẫu, idol…) làm nhân vật mới `art: anime`, từ 20 tuổi, trang phục gợi cảm lịch sự; nhân vật anime nữ (`voice` woman /
young_woman) tạo trong cách dựng mới được thêm `GLAM` (đẹp, quyến rũ, kín đáo) vào mô tả cố định. Cách dựng cũ không đổi.

## 2026-10-10: clip image-to-video trên Kaggle (Wan2.2 TI2V-5B Turbo, chưa chạy thật)

Theo tài liệu "Ảnh và clip trên Kaggle cho video いらすとや": cảnh `"motion_level": "low"` (có `"full"`) được sinh clip
4 bước bằng Wan 5B Turbo GGUF qua ComfyUI headless, cùng kernel với sinh ảnh (giai đoạn ảnh xong mới tới giai đoạn clip).
- `kaggle_job/i2v_runner.py` (mới): cài ComfyUI + ComfyUI-GGUF vào /kaggle/temp, tải model theo `[i2v]` (tên file GGUF dò theo
  quant, không đoán), mỗi GPU một server, server thứ hai chỉ bật sau khi server đầu xong một job (RAM). Mỗi cảnh 2 seed, giữ
  clip điểm QA cao hơn (QA thô: độ chuyển động giữa frame, trừ điểm khi frame cuối trôi xa frame đầu). Hết VRAM: thử lại với
  3/4 số frame rồi `failed_oom`; server chết: khởi động lại; còn < 30 phút phiên thì ngừng. Ghi `clips_results.json`.
- `kaggle_job/wan5b_i2v.json` (mới): workflow API, node tìm theo `_meta.title` (IN_IMAGE, IN_PROMPT, IN_LATENT, IN_SAMPLER,
  OUT_FRAMES); upscale bỏ đi khi `upscale_url` trống.
- `make_jobs.py`: mục `clips` trong jobs.json; ảnh đầu là `@full_NNN` (cùng lô) hoặc `full/NNN.png`; số frame theo giọng đọc
  nếu đã có, không thì 4 giây; clip cũ hơn tranh (tranh vẽ lại khi duyệt) thì sinh lại. `"high"` (gửi API) chưa làm.
- `run_kaggle.py`: gửi kèm runner/workflow/ảnh, cộng `minutes_per_clip` vào thời hạn kernel, tải clip về `clips/NNN.mp4`,
  gộp `clips/results.json`. `build_video.py`: cảnh có clip dùng clip làm nền chuyển động (đặt như tranh cả cảnh, clip ngắn
  thì giữ khung cuối). `tools/i2v_bench.py` (mới): benchmark cỡ / quant / 1 hay 2 GPU.
- Lệch tài liệu: cỡ sinh mặc định 576x1024 (= tranh cả cảnh, 9:16) thay vì 704x960 (khung clip của layout ghép trong tài liệu,
  ở đây clip phủ cả màn hình); ComfyUI đặt ở /kaggle/temp thay vì /kaggle/working để không bị tải về; upscale tắt mặc định.

Kiểm tra (máy local, không GPU): make_jobs trên bản sao video 031 ra đúng 3 clip; run_kaggle --dry-run dựng đủ dataset và
thời hạn; dựng workflow, kiểm cỡ/4k+1, ghép mp4, đo QA chạy đúng với frame giả; build_video đọc clip thành khung nền.
**Chưa chạy trên Kaggle**: tên input của các node, shift, chất lượng, tốc độ, RAM đều chưa xác nhận; chạy tools/i2v_bench.py trước.

## 2026-10-09: sửa lô Kaggle bị từ chối khi có nhân vật anime

Video 031 (phuctran) dừng ở "Sinh ảnh trên Kaggle" (người dùng tưởng Kaggle kẹt): run_kaggle.py từ chối lô trước khi gửi vì
`full_003` (LoRA 0,55) tham chiếu `@ref_mama_ageless` (ảnh chuẩn anime, LoRA 0) cùng lô; worker chạy theo LoRA giảm dần nên
tranh sẽ chờ mãi. `make_jobs.py`: tranh cả cảnh cần ảnh chuẩn "@ref" có LoRA thấp hơn thì hoãn sang lượt sau (auto.py chạy tối
đa 3 lượt; lượt sau ảnh chuẩn đã là file). 031: hoãn full_003, 028, 033; chạy thử gửi lô qua được; đã chạy tiếp.

## 2026-10-09: chữ tượng thanh rải quanh đầu; biểu cảm cường điệu + góc mặt

Theo ảnh mẫu (người cười đểu, 「ニヤ」 rải quanh mặt, đầu nghiêng):
- `effects.py`: hiệu ứng `murmur` ({"effect": "murmur", "text": "ニヤ", "on": id}): 5-7 chữ nhỏ màu cam viền trắng, nghiêng ngẫu
  nhiên quanh đầu từ má trái qua đỉnh sang má phải, bật ra lần lượt rồi nhấp nháy; không có "on" (tranh vẽ cả cảnh) thì quanh
  vùng mặt giữa khung. `build_video` truyền `text`; `01_script.py` hướng dẫn (ニヤ, ドキッ, イライラ, ソワソワ, ジー...), ~1/6 cảnh.
- `make_jobs.py: expressive()`: "emotion" khớp từ khóa (smug, angry, shocked, scared, sad, happy, embarrassed, cold, creepy,
  confused, despair) -> mô tả mặt cường điệu kiểu manga; cảnh close / half thêm góc mặt đổi theo cảnh (nghiêng đầu, ba phần tư,
  chồm tới, ngả đầu nhìn xuống). Dùng cho ảnh cắt rời và tranh vẽ cả cảnh.

## 2026-10-09: nhân vật nét anime (art: "anime")

Video mẫu 5 trộn nét: cô mẹ anime (mắt to, tóc bóng, đổ bóng mềm) giữa các nhân vật Irasutoya. `01_script.py`: nhân vật mới có
`art` (mặc định irasutoya; "anime" khi đề tài yêu cầu, tối đa 1 nhân vật / video), ghi vào characters.json. `make_jobs.py`:
ảnh chuẩn anime vẽ không LoRA (`ANIME_CAST`); tranh cả cảnh có nhân vật anime: LoRA 0 nếu chỉ người đó, 0,55 nếu có cả người
Irasutoya, kèm dặn nét từng người; ảnh cắt rời (cách dựng cũ) của nhân vật anime cũng không LoRA. Đã thử lập danh sách ảnh;
chưa vẽ thật trên Kaggle (trộn hai nét trong một tranh chưa chắc model giữ được).

## 2026-10-09: Tạo video: "Cách dựng mới" (theo video mẫu) và cảnh màn hình điện thoại

Người dùng bỏ hàng "Kiểu chuyện", thay bằng lựa chọn "Cách dựng: hiện tại / mới (theo video mẫu スカッと迷言集)".
- Màn hình điện thoại vẽ bằng code (`phone.py`: chat kiểu LINE, cuộc gọi nhỡ, thông báo màn hình khóa, hộp thoại chặn, hồ sơ
  app hẹn hò; chữ Nhật sắc, phông không có ▮ / 📞 nên tự vẽ biểu tượng). Kịch bản cả hai cách dựng được ghi `phone` (~1/10 cảnh).
  `build_video.new_style_layers()`: cảnh phone vẽ ảnh `phone/NNN.png`, đặt giữa khung trên nền mờ, bỏ lớp ảnh cắt rời.
- Cách dựng mới (`SHORTS_STYLE=new` từ meta `style`): `01_script.py` thêm yêu cầu tranh cả cảnh 1-2 người + công thức bí mật
  lộ dần / cú lật, đánh dấu `full` mọi cảnh trừ phone; `make_jobs.py` sinh job `full_NNN` (576x1024, tham chiếu ảnh chuẩn từng
  người, tối đa 2) -> `run_kaggle.py` tiền tố `full` -> `videos/<tên>/full/NNN.png`; `character_files` / `missing_images` /
  `review_items` hiểu cảnh `full`; `build_video.background()` dùng tranh đó, bỏ lớp cutouts, chữ neo vào nhân vật chuyển góc trên
  phải; nhạc nền 13 dB dưới giọng (video mẫu đo 11-14 dB). Thử dựng khung: tranh cả cảnh, điện thoại, cảnh cũ đều đúng.
  Chưa chạy một video thật bằng cách dựng mới.

## 2026-10-09: Tạo video: lựa chọn "Kiểu chuyện"

Từ phân tích 2 video viral kênh 「スカッと迷言集」 (kể ngôi thứ nhất, bí mật lộ dần, câu cuối lật ngược rồi hết, cảnh màn hình điện
thoại). Trang Tạo video thêm hàng "Kiểu chuyện": AI tự chọn (mặc định, như cũ) / Bí mật + cú lật / Sảng khoái trả đũa / Cảm động
/ Hài. Lưu `meta.json` `story_mode` -> env `SHORTS_STORY_MODE` -> `01_script.py: STORY_MODES` đưa công thức vào đề bài (sau
"Kiểu kể"), ghi `script["story_mode"]`.

## 2026-10-09: bỏ tông đen trắng "noir", tông màu chỉ phủ nhẹ

skit-006 bị AI đạo diễn chọn `grade: noir` (sát thủ) -> cả video đen trắng tương phản, mặt lem xám. `write.py` bỏ "noir" khỏi
`GRADES` (guide cũng bỏ); `build.py: grade()` chỉ phủ 40% (`GRADE_MIX`) để giữ màu gốc. skit-006 đặt `grade: none`, dựng lại.
Đen trắng chỉ còn là kỹ xảo một câu (`freeze`).

## 2026-10-09: tiểu phẩm: nhân vật đứng trên sàn trống, bàn ghế vẽ liền người ngồi

Người dùng: skit-008 vẫn nhiều lỗi (hình dạng nhân vật kỳ, nền làm khó). Gốc: bắt nhân vật cắt dán ngồi vào bàn ghế của nền
(nửa người trôi, ngồi xếp bằng lơ lửng; toàn cảnh vẽ cả người thì thừa người, người nhỏ). Như video mẫu: nền là phông sau lưng có
sàn trống, nhân vật đứng; ai cần ngồi thì bàn ghế vẽ liền trong ảnh nhân vật (chỉ huy ngồi sau bàn).
- guide: `sets` có sàn trống phía trước, đồ đạc chỉ phía sau / hai bên; `pose` mặc định đứng + đồ cầm tay; ngồi thì kèm bàn ghế
  của chính họ, nền không có bàn ghế ở đó.
- `jobs.py`: người ngồi dùng `SEATED_BASE` (giữ bàn ghế trong câu tư thế, cả người); người đứng vẫn lọc đồ đạc; nền thêm "open
  empty floor ... no desk, table or chair in the middle"; `MAKE_SCENES = False` (tắt toàn cảnh vẽ cả người). `stage.py`: chân /
  chân ghế chạm sàn trống của nền.
- skit-008: dùng lại bộ ảnh đầu (ngồi có bàn ghế liền người), mô tả nơi thành văn phòng có sàn trống, vẽ lại 1 nền.

## 2026-10-09: tiểu phẩm: toàn cảnh vẽ sẵn có người trong bối cảnh

Người dùng: skit-008 "không hợp lý chút nào": toàn cảnh ghép ảnh cắt lên nền thì người nhỏ, lơ lửng, không ngồi được sau bàn
(ảnh cắt luôn đè lên nền), khác phối cảnh; tranh chèn (Kaggle vẽ cả cảnh) thì luôn ăn khớp. Đổi: câu góc rộng dùng ảnh toàn cảnh
Kaggle vẽ cả người trong bối cảnh. `skit/jobs.py: wide_states()` gom các câu góc rộng theo (nơi, ai có mặt, tư thế từng người),
tối đa 8 ảnh `skit_<tên>_sceneNN` (nền nơi đó làm tham chiếu 1 qua tiền tố mới `bg__` của `run_kaggle.py`, ảnh chuẩn từng vai
2, 3...; tư thế nguyên văn có bàn ghế); câu ghi `scene`. `skit/build.py: scene_frame()` dùng ảnh đó (phóng chậm, chữ phía trên);
cận / nhóm vẫn ghép ảnh cắt (đổi mặt, mấp máy miệng). skit-008: 6 ảnh toàn cảnh cho 11 câu góc rộng.

## 2026-10-09: tiểu phẩm: ảnh nhân vật không kèm bàn ghế

skit-008: ảnh nhân vật ngồi bị Kaggle vẽ kèm bàn, ghế, bàn phím (tư thế AI viết "sitting at desk", "feet up against desk edge",
"hands typing on keyboard") trong khi nền văn phòng đã có bàn. `skit/jobs.py`: `body_pose()` bỏ cụm nơi chốn / đồ đạc khỏi lời
vẽ nhân vật (at / on / behind / around... + desk, chair, sofa, keyboard, monitor, door...), "typing" -> "hands moving as if
typing"; lời vẽ cấm rõ bàn, ghế, sofa, bàn phím, máy tính, sàn; người ngồi vẽ nửa người trên cắt ngang eo; tư thế phụ của người
đang ngồi vẫn là ngồi (`seated_pose`). `guide.md`: pose chỉ tả cơ thể + đồ cầm tay, đồ đạc ghi ở `place`. `stage.py`: ảnh nửa
người đặt đáy (eo) ngay mặt bàn / ghế / sofa của nền để trông như ngồi sau bàn của nền. Ảnh skit-008 đã vẽ vẫn còn bàn ghế.

## 2026-10-09: sửa lỗi Bố cục cảnh khi neo vào tên nhân vật (video 028)

Video 028 (tustruyen) dừng ở "Bố cục cảnh": kịch bản ghi ảnh `cutouts/025_best_friend.png` và chữ neo `best_friend.beside_right`;
ảnh không có nên `repair()` đổi sang `025.png` (lớp mang tên "025") nhưng neo vẫn trỏ "best_friend" -> check() báo lỗi. Đồng thời
repair() chỉ tính lớp ảnh có "id" riêng nên tưởng cảnh không có lớp ảnh và bỏ hiệu ứng (rays, sweat, tears, aura, hearts).
`build_video.repair()`: id lớp ảnh = "id" hoặc tên file (như check()); neo vào lớp không có thì chuyển sang lớp ảnh vừa đổi tên
hoặc lớp ảnh chủ thể của cảnh; hiệu ứng bám vào lớp đó; hiệu ứng ghi "on" trỏ vào lớp không có (vd "me") cũng chuyển về lớp đó (từng KeyError trong effect_box). Thử 028: bố cục xuất đủ 40 ảnh. Đã chạy tiếp 028.

## 2026-10-09: ô "Đã đăng TikTok"; cổng AI: thử lại luồng rỗng, model dự phòng

- Đã đăng TikTok: `app.py` `/api/posted` (chủ video / admin, chỉ video đã dựng xong) ghi `meta.json` `posted: {by, at}`;
  `video_info` / `skit_info` trả `posted`. `PostedToggle` (common.jsx) ở ô Thư viện (truyện kể + tiểu phẩm), thẻ và cửa sổ chi
  tiết trang Tiểu phẩm; Thư viện thêm lọc "Chưa đăng" (video xong chưa đăng) / "Đã đăng".
- skit-008, 009 kẹt ở bước viết: ShopAIKey trả luồng rỗng rồi 503 "No available channel for model claude-sonnet-5-5 under group
  cheap" (Sonnet 5 / Opus 5.5 / Opus 5 vẫn chạy). `steps/llm.py`: luồng rỗng không lý do kết thúc (`EmptyReply`) và đứt luồng
  được thử lại; 503 hết đường chạy thì đổi sang model dự phòng (`FALLBACK`: sonnet-5-5 -> sonnet-5, opus-5-5 -> opus-5).
  Đã dừng và chạy lại skit-008, 009.

## 2026-10-09: tiểu phẩm: giữ chân người xem video ngắn

`guide.md` thêm mục "Giữ chân người xem": câu 1-2 là móc câu (xung đột / vô lý, không chào hỏi), tiêu đề 2 dòng ≤ 12 chữ tạo
tò mò không lộ chốt, mỗi 10-15 giây một nhịp mới, cú chốt ở 3-5 câu cuối, nối về câu đầu để lặp, 60-80 giây; khuôn `story`
hết "mở đầu bình thường"; đạo diễn dựng mạnh câu 1 và cú chốt. `write.py`: ước > 84 giây thì viết lại ngắn hơn (skit-005, 007
đọc thật ~101 giây), giữ bản gần 72 giây nhất trong các lần viết.

## 2026-10-09: tiểu phẩm: khung cận riêng, tỉ lệ thật, dàn cảnh theo nền

Góp ý skit-007: mọi nhân vật luôn chung một khung, mèo / chó cao bằng người, nhân vật không liên quan tới nền.
- `skit/build.py`: `View` thay `Stage`. Cận (`close:`) / nhóm (`group:`) giờ dựng khung riêng chỉ có người được nhắc (tối đa 3),
  vẽ từ ảnh gốc (nét, không phóng to cả hàng), nền phóng gần chỗ họ đứng + mờ nhẹ; đổi khung = cắt + lia nhòe. Chiều cao theo
  `height` của vai (đoán theo mô tả nếu thiếu: cat 0.32, dog 0.45, retriever 0.55, child 0.7...).
- Bước mới "Dàn cảnh" (`skit/stage.py`, sau Tách nền): AI đọc ảnh nền có lưới tọa độ, đặt từng vai đúng chỗ (sofa, cửa, ổ chó)
  với cỡ theo phối cảnh, rồi xem ảnh ghép thử và tự sửa; ghi `blocking`, ảnh `work/blocking_<nơi>.jpg`. Lỗi thì xếp hàng.
  Thử skit-007: người ở cửa (cao 0,30), chó cạnh ổ (0,21), mèo trên sofa (0,10).
- Nền skit-007 hỏng (tranh nhỏ giữa khung + chữ nhảm) vì mô tả nơi lẫn lời dặn "9:16 composition, subtitle space, BGM...".
  `jobs.py: place_prompt` bỏ câu kỹ thuật / chữ trong 「」, tối đa ~300 ký tự, thêm "full-bleed scene filling the whole frame";
  guide: `sets` chỉ tả nơi chốn, thêm `height`, `place` cho vai.

## 2026-10-09: tiếng hiệu ứng: nghĩ tự do trước, tra kho sau

Người dùng thấy tiếng của skit-004 (đạo diễn tả tự do, trước khi có danh mục) chuẩn; chép tên từ kho thì dễ bị danh sách dẫn
dắt. Đạo diễn giờ: 1) tự nghĩ khoảnh khắc cần tiếng gì, 2) tra kho, có tên khớp thì chép đúng tên, không thì giữ mô tả tự do
cho `sounds.py` tìm (đường cũ). skit-004 đưa vào guide làm mẫu tốt.

## 2026-10-09: tiểu phẩm nhiều tiếng hiệu ứng hơn

Người dùng: 7 tiếng / video ít quá, cần sống động hơn. `guide.md`: 3-8 -> 12-18 tiếng, thêm chỗ được dùng tiếng
(vào / ra cảnh chèn, đổi tư thế mạnh, biểu cảm sốc, câu hét, lia máy, bigword); vẫn không cho câu thường, không hai tiếng liền,
không lấy tiếng gần nghĩa. Áp dụng cho tiểu phẩm qua lượt đạo diễn sau thay đổi.

## 2026-10-09: Thư viện có cả tiểu phẩm

`Library.jsx`: bộ chuyển Tất cả / 🎬 Truyện kể / 🎭 Tiểu phẩm (nhớ lựa chọn), danh sách gộp xếp theo thời gian cập nhật, số
đếm theo người tạo tính theo loại đang chọn; ô tiểu phẩm (ảnh bìa hoặc ảnh vai, số câu, giây, tải, xóa) mở cửa sổ chi tiết
tiểu phẩm; khi xem "Tất cả" mỗi ô có nhãn loại. `Skits.jsx` tách `SkitModal`, `deleteSkit`, `resumeSkit`, `skitThumb` dùng chung.

## 2026-10-09: thêm 23 giọng VOICEVOX (18 -> 41)

Người dùng muốn giọng đa dạng hơn. VOICEVOX 0.25.2 trên máy có 43 nhân vật / 127 kiểu giọng, cấu hình mới dùng 18.
Đọc điều khoản từng giọng (`/speaker_info`): thêm 23 giọng dùng thương mại được khi ghi nguồn (後鬼, Voidoll: cá nhân được,
công ty / pháp nhân phải hỏi); BỎ ユーレイちゃん (chỉ phi thương mại) và ぞん子 (thương mại phải hỏi trước). Giới tính, tuổi
theo cao độ đo bằng audio_query (nam: 離途 114 Hz, 紅桜 155, 黒沢冴白 157, 栗田まろん 162). Trường `credit` cho giọng ghi
nguồn đặc biệt (Voidoll(CV:丹下桜), 里石ユカ（つぼみ）), `06_voice.py` và `skit/voice.py` ghi đúng chuỗi đó vào credits.txt.
Bảng tone thêm các kiểu giọng mới (おどおど, こわがり, 絶望と敗北, 呆れ, シリアス...). File cấu hình dùng chung: AI viết kịch bản
truyện kể cũng thấy 41 giọng.

## 2026-10-08: AI đạo diễn chọn tiếng hiệu ứng từ kho

Người dùng: AI nên dựa vào kho tiếng để viết cho chuẩn. Trước: đạo diễn tả tiếng tự do rồi `sounds.py` đi tìm (có lúc kho không
có, vd 消防車のサイレン). Giờ `write.py --direct` gửi kèm danh mục gọn (`sounds.compact()`: 1.520 tên sau khi gộp bản đánh số
và bỏ tiếng bị loại, ~13.000 ký tự) và bắt `sfx` là tên chép đúng trong kho hoặc null. `sounds.py` khớp đúng tên thì tải luôn
(không gọi AI; nhiều bản đánh số thì chọn theo tên tiểu phẩm), tên không khớp mới chạy đường tìm cũ. Chưa chạy thử lượt đạo
diễn thật (khóa AI hết tiền); đã thử phần khớp tên: カークラッシュ, ショック -> ショック2, チーン -> チーン2, ショック3 đúng.

## 2026-10-08: tiểu phẩm: tiếng hiệu ứng ít và nhỏ, nhạc nền rất nhỏ

Người dùng: tiếng hiệu ứng chỉ khi thật sự hợp, không quá to; nhạc nền có cũng được nhưng nhỏ hơn giọng nhiều.
`guide.md`: `sfx` chỉ khi tiếng làm câu buồn cười / rõ hơn (vật có tiếng thật, cú chốt, im lặng ngượng), không cho câu thường,
không hai tiếng liền nhau, thường 3-8 tiếng cả video. `skit/build.py`: mỗi tiếng chỉnh theo độ to giọng (RMS, bỏ đoạn lặng) để
nhỏ hơn giọng 9 dB (`SFX_BELOW`), đỉnh tối đa 0,6; nhạc nền nhỏ hơn giọng 27 dB (`MUSIC_BELOW`; truyện kể 21, nhạc hài 14).

## 2026-10-08: tiểu phẩm nhiều biểu cảm, tư thế hơn

Người dùng muốn đa dạng hơn. Giới hạn mỗi vai: biểu cảm 4 -> 6 (thêm embarrassed, thinking, disgusted, sleepy), tư thế khác
2 -> 4, bản sao 5 -> 6; guide dặn vai chính 5-6 biểu cảm, 2-4 tư thế, đổi tư thế theo hành động ~4-8 câu một lần. Sân khấu đến
10 người. Ước GPU: lô thật 22 ảnh mất 19 phút (kể cả nạp model) -> ~0,7 phút / ảnh; 3 vai đầy đủ + 8 tranh chèn ~50 ảnh ~40 phút.

## 2026-10-08: sửa lỗi tiểu phẩm kẹt ở bước Giọng đọc

skit-003 đọc lại 32 lần không dừng: tổng 61,9 giây < ngưỡng 62, tốc độ mới `round(1.17 * 61.9 / 62, 2)` vẫn = 1.17.
`skit/voice.py`: ngưỡng >= 60 giây (yêu cầu người dùng), khi đọc chậm lại nhắm 61,5 giây và mỗi lượt chậm hơn ít nhất 0,02,
tối đa 6 lượt. Đã dừng lần chạy kẹt và chạy tiếp skit-003.

## 2026-10-08: tiểu phẩm thêm khuôn, người dùng chọn được khuôn

3 tiểu phẩm đầu đều `loop` (kể cả ý tưởng một câu chuyện tuyến tính 「遅刻した理由」) vì guide đặt loop đầu tiên, ví dụ dài nhất.
`guide.md`: thêm `story`, `misunderstanding`, `interview`, `reaction`; dặn chọn khuôn hợp ý tưởng, không mặc định loop.
Trang Tiểu phẩm có hàng chọn khuôn (mặc định "AI tự chọn"); lựa chọn lưu `meta.json` -> env `SKIT_FORMAT` -> `write.py` ghi
"Khuôn bắt buộc" vào đề bài và ép `format`. Khuôn `free`: đề tài lạ không hợp khuôn nào thì AI tự thiết kế 3-6 nhịp
(`structure`, hiện ở cửa sổ chi tiết) rồi viết theo; model đặt khuôn lạ cũng được coi là `free`. Sidebar: số ở "Tạo video" không đếm việc tiểu phẩm nữa.

## 2026-10-08: tắt miệng bằng Gemini; giao diện trang Tiểu phẩm mới

- `[faces] talk = false` (settings.toml, đọc trong `tools/make_faces.py`): không gọi model ảnh vẽ miệng mở (tốn tiền
  ShopAIKey); chớp mắt vẽ bằng code vẫn chạy. Bật lại: `talk = true`.
- Trang Tiểu phẩm (`Skits.jsx`, CSS `.sk-*`): khung nhập có gợi ý dạng thẻ + cột quy trình 6 bước; lưới thẻ 9:13 có ảnh bìa
  (`work/poster.jpg`, `skit/build.py` cắt từ video, bỏ dải tiêu đề), nhãn trạng thái, thời lượng, nút phát / chạy tiếp / xóa khi
  rê chuột; lọc Tất cả / Đang chạy / Xong / Lỗi; cửa sổ chi tiết hai cột (video, thông tin, ảnh vai, tiến trình / nhật ký).
  `app.py: skit_info` thêm `poster`, `faces`, `step`, `steps_done/total`, `grade`, `directed`.

## 2026-10-08: loại tiếng 「ジャン！」 (jan/jean1.wav)

Người dùng: tiếng ở giây 37-38 video 025 (cảnh 29, chữ 「ジャーン」 -> nhóm `jan`) "rõ ràng không hợp, không dùng nữa".
File chuyển sang `library/sfx/_banned/jan_jean1.wav`; danh sách loại `library/sfx/banned.txt` (tên file không đuôi) được
`build_video.sfx_file`, `tools/fetch_sfx.py` (không tải lại) và `skit/sounds.py` (bỏ khỏi danh mục) cùng đọc. Nhóm `jan` còn
ジャジャーン, 運命1, 運命2. Video đã dựng (025) vẫn còn tiếng cũ cho tới khi dựng lại.

## 2026-10-08: chức năng mới "Tiểu phẩm" (skit/, skits/, trang web Tiểu phẩm)

Theo 5 video mẫu tiểu phẩm hài lồng tiếng (ぶつかりおじさん, 焼肉の反応集, 励ましてくれる先輩, 銃持つ向き逆のスナイパー,
飲み会ミッション). Tách hẳn khỏi pipeline truyện kể: code ở `skit/`, dữ liệu ở `skits/<skit-NNN-...>/`; chỉ gọi lại
`tools/run_kaggle.py`, `steps/04_cutouts.py`, hàm VOICEVOX của `06_voice.py`, `build_video.music_gain`, không sửa chúng.
- `skit/guide.md`: một sân khấu chính (tối đa 2 nơi cắt qua lại khi gọi điện), khuôn loop / list / incident, 40-55 câu ngắn,
  góc máy wide / close / group, cỡ chữ small..shout, từ nhấn, `stack`; thêm từ 2 video sau: `insert` (tranh chèn minh họa,
  chữ chồng giữa khung), `silent` (chỉ dẫn 「（過呼吸）」 không đọc), `mark` (gloom / sweat / anger / sparkle / shock vẽ bằng code),
  `glow`. Mục "Sáng tạo": mẫu chỉ để học nhịp, ý tưởng + cú chốt phải riêng, gài chi tiết đầu để nổ ở cuối.
- `write.py` (AI viết, ước ≥64 giây, `--extend` viết thêm), `voice.py` (VOICEVOX 1.3, mốc chữ hiện dần theo cụm từ; ngắn hơn
  62 giây thì đọc chậm lại, vẫn ngắn thì thoát mã 5 để viết thêm), `jobs.py` (ảnh gốc mỗi nhân vật + mỗi biểu cảm vẽ từ ảnh gốc,
  nền từng nơi, tranh chèn), `build.py` (sân khấu, máy quay, chữ, dấu cảm xúc, nhạc comical), `auto.py` (điều phối, progress.json).
- Chuyển động kiểu "rối giấy" (xem video mẫu ở 8 khung/giây: ảnh tĩnh đổi qua lại, không vẽ từng khung): mỗi ảnh nhân vật
  có bản miệng mở `_talk` (Kaggle vẽ từ chính ảnh đó), người nói mấp máy theo độ to giọng (3 khung / nhịp); `poses` (0-2 tư thế
  khác mỗi nhân vật, đổi bằng `pose` theo câu); lắc lư quanh chân (người nói ±2°, người nghe ±0,7°), nhún theo tiếng, nảy lên khi
  đổi biểu cảm / tư thế, rung mạnh khi hét. Ảnh chuẩn lưu riêng từng tiểu phẩm (`config/refs/<tiểu phẩm>_<vai>_front.png`).
- Tiếng hiệu ứng (chỉ tiểu phẩm), theo yêu cầu "tìm tiếng mới, đừng dùng lại tiếng cũ không khớp": `sfx` từng câu là mô tả
  tiếng Nhật; `skit/sounds.py` quét danh mục 効果音ラボ (2.215 tiếng, `library/sfx/lab_catalog.json`, làm mới sau 30 ngày),
  AI nghĩ từ khóa đồng nghĩa -> lọc ~40 ứng viên -> AI chọn đúng một hoặc "không có" (câu đó im), tải về
  `library/sfx/lab/_skit/`. Thử 8 mô tả: 7 khớp (お茶を吹き出す -> 飲み物をブーッと噴き出す, 車がぶつかる -> カークラッシュ...),
  消防車のサイレン: kho không có -> im. OtoLogic chặn tải tự động (403), chưa thêm nguồn thứ hai.
- Dựng sáng tạo (chỉ tiểu phẩm): `grade` cả video (noir / retro có hạt phim / warm / cool / night), `fx` từng câu (zoom_punch,
  shake, flash, invert, focus_lines 集中線, gloom_lines, sparkle_bg, speed_lines, spotlight, freeze, blackout, split chia đôi hai
  nơi), `bigword` chữ tượng thanh khổng lồ bật ra. Lượt AI "đạo diễn" riêng (`write.py --direct`, bước "Kế hoạch dựng") đọc
  kịch bản xong mới chọn kỹ xảo / chữ / tiếng / tông màu, không đổi lời thoại. Kiểm tra bằng ảnh tạm: các kỹ xảo ra đúng.
- Web: action `skit`, `/api/skit/generate|resume|delete`, `state.skits`, phục vụ `/skits/...`; trang `Skits.jsx`.
- Kiểm tra: AI viết tiểu phẩm thử 55 câu (có gài 「毎年新築」 nổ ở cuối, 8 tranh chèn, 3 câu im lặng); VOICEVOX 64,0 giây;
  dựng khung hình bằng ảnh tạm: cận / rộng / tranh chèn / chữ tím phát sáng / dấu cảm xúc đúng chỗ. Chạy Kaggle thật: đang chạy.

## 2026-10-08: hết nhấp nháy do tư thế thứ hai

Nhân vật hay nhấp nháy: tư thế 2 (`alt_pose`) đổi qua lại mỗi 0,25 giây ở mọi cảnh có nó; hai ảnh vẽ riêng luôn lệch nét,
có cặp khác hẳn bề ngang (024: ảnh 008 rộng 290 / 398 px); 024 có 20/48 cảnh dùng (do lời dặn ~1/2 cảnh). `build_video.py`:
mặc định đổi MỘT lần ở giữa câu (`ALT_SWITCH`); chỉ khi mô tả tư thế 2 là động tác lặp lại (walking, waving, typing, eating,
shaking, sobbing... `LOOP_WORDS`) mới luân phiên, chậm hơn (0,4 giây). Thử 024: 8 cảnh luân phiên (đi, lắc đầu, run vai), 12 đổi
một lần. `script_guide.md`, `01_script.py`: alt_pose ~1/4 cảnh có nhân vật, chỉ khi cần; tư thế 2 chỉ đổi tay / chân.

## 2026-10-08: tiếng hiệu ứng chỉ khi thật cần; cảnh nhiều nhân vật chỉ khi hợp lý

Góp ý video 024 (gia đình, nghiêm túc): 36 tiếng / 48 cảnh, nhiều tiếng sai nghĩa (tiếng ăn ở 「また学校に電話したってよ」,
gõ phím, bước chân, ドドン ở cảnh khóc); cảnh nhiều nhân vật bị lặp người (con trai hai lần, bố hai lần), chen chúc, cắt mép.
- Tiếng (`build_video.py: sfx_events` viết lại): không gắn theo chuyển cảnh, hiệu ứng, sticker, động tác, cảm xúc, không
  đoán theo action tiếng Anh. Chỉ: `sfx` ghi rõ, chữ tượng thanh trên hình, lời thoại nhắc sự việc có tiếng thật (`SFX_REAL`:
  điện thoại, tin nhắn, gõ / mở cửa, chuông, chụp ảnh, ngã, tát, tàu, chúc mừng, đúng / sai, ツッコミ), câu chốt, vào twist,
  vào hồi tưởng, kết hài; tự gắn ~10% số cảnh, mỗi tiếng tối đa 2 lần, 1 tiếng / cảnh. Thử: 024 36 -> 11 tiếng, 022 -> 7,
  015 (hài) -> 19 (phần lớn theo chữ tượng thanh). `script_guide.md`: chữ tượng thanh ~1/8 cảnh, truyện nghiêm túc rất ít.
- Lặp người: nguyên nhân là action "facing right toward the waiter / handing ... to the girl" làm model vẽ luôn người kia
  vào ảnh riêng. `make_jobs.py: alone()`: cảnh nhiều nhân vật bỏ cụm nhắc NGƯỜI (giữ đồ vật: "looking at the clock"), thêm
  "alone, the only person in the image, nobody else".
- Chen chúc: `build_video.py MULTI_SCALE`: 2 người mỗi người x0.8, 3 người x0.7 (vd half 0.70 -> 0.56).
- `script_guide.md`: nhiều nhân vật chỉ khi cùng chỗ, cùng lúc, làm gì đó với nhau trong câu (~1/4 cảnh có nhân vật, không
  ép; câu kể, tự nghĩ, nói về người vắng mặt thì một người), action mỗi người không nhắc người kia.
Video 024 hiện vẫn là bản cũ: ảnh lặp người đã vẽ sẵn, cần vẽ lại các cảnh đó mới hết.

## 2026-10-08: action theo từng nhân vật

Video 026 dừng ở bước lên danh sách ảnh: cảnh nhiều nhân vật ghi `"action": {nhân vật: hành động}` (17/44 cảnh), `make_jobs.py` đưa nguyên bảng vào câu lệnh vẽ và `key_for` lỗi (TypeError: expected str, dict found). `per_character()`: mỗi ảnh nhân vật lấy đúng action / emotion của nhân vật đó (chuỗi thì dùng cho mọi nhân vật). Kiểm tra: 026 ra 86 job, ảnh mỗi nhân vật có đúng hành động của mình.

## 2026-10-08: VOICEVOX tốc độ 1.2; video luôn trên 1 phút

Video 023 đọc 9,2 ký tự/giây (giọng No.7 / WhiteCUL ở speedScale 1.35) nên chỉ 57 giây và nghe quá nhanh. `voicevox_speed`
1.35 -> 1.2 (người dùng chọn). `steps/06_voice.py`: đọc xong, tổng giọng + nghỉ (`pad`) dưới `[voice] min_video_seconds = 62`
thì đọc lại các câu VOICEVOX với tốc độ chậm hơn vừa đủ (không dưới 1.0). Đọc lại 023 ở 1.2: 64,3 giây (giọng nhanh cũ ở
work/audio_nhanh/, video cũ work/output_truoc_sua.mp4).

## 2026-10-08: trang Hoạt động chia nhóm, lọc, thao tác tại chỗ

`web/src/components/Activity.jsx` viết lại (trước là một bảng dài): 4 ô tổng quan (đang chạy, chờ duyệt, lỗi hôm nay, xong
hôm nay; bấm để lọc); lọc theo trạng thái, người dùng, loại việc (🎬 tạo video, ✨ sửa cảnh, 🛠 áp dụng, ☁️ LoRA), ô tìm;
"Đang chạy" ghim trên cùng; còn lại chia theo ngày (Hôm nay, Hôm qua, thứ / ngày). Mỗi dòng: tên video thật (bấm mở video),
trạng thái, người chạy / người bấm hộ, giờ, thời gian chạy; nút Dừng (đang chạy), Chạy tiếp (tạo video bị lỗi / dừng / ngắt),
Log mở ngay dưới dòng. Chỉ chủ việc hoặc admin thấy nút Dừng / Chạy tiếp.

## 2026-10-08: 7 góp ý: khói, tiếng hiệu ứng, tương tác, hai cú máy, nhân vật to, tiêu đề, nhạc

1. Khói: bỏ khỏi cấu hình hiệu ứng; `FX_BANNED = {"smoke"}` không bao giờ dùng dù file có trong thư viện. (Lỡ bỏ cả magic, gold, glitter; người dùng chỉ muốn bỏ khói: đã tải lại 3 nhóm này.)
2. Tiếng hiệu ứng (`build_video.py`): bỏ tiếng vút mỗi lần cắt sang bối cảnh khác (chỉ chuyển cảnh có chuyển động mới kêu);
   nhân vật đi vào khung kêu bước chân (đồ vật: vút); `SFX_TEXT`: tiếng theo nội dung câu (lời tiếng Nhật / action tiếng Anh:
   điện thoại, tin nhắn, gõ cửa, mở cửa, chuông trường, chạy, đi, ăn, chụp ảnh, tiền, tàu, bàn phím, tim đập, đồng hồ, ngã,
   tát, đúng / sai, chúc mừng, ツッコミ, nước mắt, rợn, nhẹ nhõm, ý tưởng), ưu tiên như tiếng ghi tay nhưng mỗi tiếng tối đa 2
   lần / video và không lặp 3 cảnh liền. Thử 022 / 003 / 015: 16-19 loại tiếng, mỗi loại tối đa 4 lần.
3. Tương tác: `script_guide.md`: ~1/2 cảnh có nhân vật là cảnh 2-3 nhân vật tương tác (trước 1/3; 022 chỉ 3/46, 003 chỉ
   1/58), câu thoại hai người để cả hai trong khung, action tả động tác với người kia. `variety.add_interaction`: mọi nhân vật
   trong cảnh đều cử động, người nói (nod / lean_in / sway / hop) khác người nghe (tilt / nod / breathe / jelly).
4. Hai cú máy trong một cảnh: `"focus": {"on": "<id>" | "<id>.hand_right" | [x, y], "at": 0.45, "zoom": 1.45}`: nửa đầu
   toàn cảnh (nhích rất chậm), tới `at` đẩy nhanh (0,35 giây) vào mặt / đồ trên tay / điểm đó rồi giữ; thay chuyển động máy
   quay thường. AI ghi khi lời nhắc tới thứ trong khung (~1/6 cảnh); cảnh hai người nói chuyện không ghi thì cách một cảnh tự
   đẩy vào người nói. Dựng thử 015 cảnh 4: giữ cả hai rồi đẩy vào friend_papa đang nói.
5. Nhân vật to hơn ~10%: shots full 0.64 -> 0.70, half 0.66 -> 0.73, close 0.62 -> 0.69; sizes large 0.62 -> 0.68, huge -> 0.74.
6. Tiêu đề (điện thoại che mép trên): `title_size` 190 -> 160, `TITLE_SIDE` 40 -> 100 px, `TITLE_TOP` 70 px (đẩy xuống).
7. Nhạc nền nhỏ hơn ~3 dB: `music_below_voice` 18 -> 21; hài 11 -> 14, ấm áp 15 -> 18.

## 2026-10-08: bỏ mọi hiệu ứng kiểu 3D / quay thật

Người dùng: đảm bảo không còn hiệu ứng như khói 3D. Bỏ hẳn khỏi `library/fx/` và `tools/fetch_fx.py` các nhóm smoke, magic
(hạt 3D), gold (kim tuyến 3D), glitter (giấy kim loại quay cận); còn 4 nhóm ánh sáng mềm kiểu ống kính: sparkle, bokeh,
light_leak, dust. `variety.py`: bảng tự gắn chỉ dùng 4 nhóm này (vui / đắc ý / ăn mừng / ý tưởng -> sparkle);
`drop_unknown_fx()` bỏ lớp `fx_` mà thư viện không có (kịch bản lỡ ghi khói...) thay vì báo lỗi dừng dựng.
`script_guide.md`: chỉ 4 nhóm; cấm khói, sương, lửa, nổ, tia lửa, hạt 3D, kim tuyến, giấy màu kim loại (cả trong `action`,
bối cảnh); không khí u ám dùng hiệu ứng vẽ phẳng (gloom, shock_lines, rain, nền mood_dark_swirl / mood_rain_sad).
`steps/common.py`: `"path": "off_left"` (chuỗi một điểm, kịch bản 022 cảnh 2) đổi thành [off_left, chỗ đứng].
Kiểm tra: chèn `fx_smoke`, `fx_glitter` vào kịch bản 022 -> bị bỏ; `check()` của mọi video đạt (020 chỉ thiếu ảnh chưa vẽ).

## 2026-10-08: không tự gắn khói; không chồng hiệu ứng video lên cảnh đã có hiệu ứng mạnh

Video 022 cảnh 39-41 (nền mood_dark_swirl, cảm xúc sợ): video khói thật trên nét vẽ phẳng trông như vết bẩn, cảnh 41 khói
chồng lên tia sáng. `variety.py`: bỏ `smoke` khỏi bảng tự gắn (cảm xúc và mood_dark_swirl; kịch bản ghi `fx_smoke` vẫn dùng);
cảnh có `rays`, `speed_lines`, `flash`, `gloom`, `aura`, `shock_lines` thì không thêm hiệu ứng video.

## 2026-10-08: VOICEVOX đọc nhanh hơn; sửa video 022

- Video 022 (VOICEVOX, giọng kể No.7 読み聞かせ) dài 98,6 giây, chỉ 5,7 ký tự/giây (edge-tts ~8). `steps/06_voice.py`: đặt
  `speedScale` trong audio_query theo `[voice] voicevox_speed = 1.35` (cộng tempo 1.2 như cũ). Đọc lại 022: 7,6 ký tự/giây,
  giọng 70,7 giây (ước video ~75 giây, trên 1 phút). Giọng cũ cất ở work/audio_cham/.
- 022 cảnh 2: ảnh chính thiếu một mắt (kịch bản: cô bé bước vào, tò mò, không phải nháy mắt) -> AI sửa đủ hai mắt, dùng.
  Ảnh tư thế 2 vẽ sai nội dung (ngồi trước bàn có màn hình máy tính); bản AI sửa thành dáng đứng nghiêng hẳn, khác hướng
  ảnh chính nên luân phiên sẽ giật -> bỏ, tắt `alt_pose` cảnh 2 (kịch bản cũ: work/script_truoc_sua.json).

## 2026-10-08: cài VOICEVOX; khung Tạo video mới

- Cài VOICEVOX 0.25.2 bản CPU bằng winget (HiroshibaKazuyuki.VOICEVOX.CPU). Engine: `vv-engine/run.exe` trong thư mục gói
  winget (`[voice] voicevox_engine`). `steps/06_voice.py` tự bật engine (chạy nền) khi chưa chạy; `chay_web.bat` bật luôn.
- Kiểm tra: cả 18 giọng trong `voicevox_voices.json` có đúng tên trong VOICEVOX (43 giọng); đọc thử 8 câu theo tone
  (build/voice_samples/, kèm 1 câu edge-tts để so).
- Khung Tạo video: "Kiểu kể" và "Duyệt ảnh" thành thẻ lựa chọn (biểu tượng, tên, mô tả ngắn trong thẻ); model gom vào mục
  "⚙ Tùy chọn model" thu gọn; dòng tóm tắt lựa chọn cạnh nút Tạo video. Mặc định duyệt ảnh: "Không duyệt" (cả server).
  Bỏ 3 nút gợi ý đề tài.

## 2026-10-08: chọn kiểu kể; AI chọn giọng VOICEVOX cho từng nhân vật

Người dùng chỉ chọn kiểu kể khi tạo video; AI tự chọn giọng cho từng nhân vật khi viết kịch bản.
- Trang Tạo video: "Kiểu kể" 🎙 Một giọng kể chính (`narration`, mặc định) / 🎭 Nhân vật nói chuyện (`dialogue`); lưu ở
  meta.json (`voice_mode`), truyền SHORTS_VOICE_MODE. Cửa sổ video hiện kiểu kể và ô "Ghi ở mô tả khi đăng" (credits.txt).
- `config/voicevox_voices.json`: 18 giọng VOICEVOX (giới tính, tuổi, chất giọng) và bảng `tones` -> tên kiểu giọng.
- `steps/01_script.py`: lời dặn theo kiểu kể (~2/3 lời kể hoặc ~2/3 thoại), danh sách giọng; kịch bản thêm `voices`
  {speaker: tên giọng} và `tone` mỗi cảnh (normal, happy, excited, sad, crying, angry, whisper, scared, calm, narration);
  ghi `voice_mode` vào kịch bản. (Đổi tên biến thành VOICEVOX_VOICES: `VOICES` đã là bảng giọng edge-tts.)
- `steps/06_voice.py`: kịch bản có `voices` và VOICEVOX đang mở (`[voice] engine = "voicevox"`): lấy /speakers, chọn kiểu
  giọng theo `tone` (không có thì ノーマル), giọng không có trong VOICEVOX thì dùng giọng cùng giới tính; ghi credits.txt
  "VOICEVOX:<tên>". VOICEVOX chưa mở: cảnh báo, đọc bằng edge-tts như cũ.
Kiểm tra: câu lệnh gửi AI hiện đúng danh sách giọng và lời dặn kiểu kể; ghép tone -> kiểu giọng với danh sách giả lập
(sad -> かなしみ, excited -> 熱血, narration -> 読み聞かせ, angry -> ツンツン, giọng thiếu -> cùng giới tính).
Chưa đọc thử bằng VOICEVOX thật (máy chưa cài VOICEVOX).

## 2026-10-08: video 70-80 giây, nhân vật cử động nhiều hơn

Người dùng: 70-80 giây là đủ, tăng mật độ hình động (hành động nhân vật). Video đo thật: 70 cảnh ra 105 giây.
- `script_guide.md`: 44-52 cảnh, 450-560 ký tự lời, 3 nấc; `alt_pose` (hai tư thế luân phiên) cho ~1/2 cảnh có nhân vật
  (trước 1/4), ưu tiên cảnh nói (khoa tay, gật đầu), hành động, phản ứng mạnh; tư thế 2 khác rõ tư thế 1. Số ảnh gần như
  không đổi vì ít cảnh hơn.
- `steps/01_script.py`: khoảng 68-86 giây (ước 8 ký tự/giây + 0,35 giây/cảnh), tối thiểu 40 cảnh; ngắn thì nhờ viết dài thêm,
  dài thì nhờ viết gọn lại (`SHORTER`), tối đa 2 lần, giữ bản sát khoảng nhất (`fit`).

## 2026-10-08: hiệu ứng ánh sáng bằng video thật (Mixkit)

Hiệu ứng tự vẽ (effects.py) phẳng; video mẫu dùng video hiệu ứng thật (bokeh, lấp lánh...).
- `tools/fetch_fx.py`: tải 14 video nền đen từ Mixkit (dùng thương mại miễn phí, không ghi nguồn, cấm phát tán lại file gốc;
  `library/fx/` trong .gitignore), đổi sẵn sang khung dọc 540x960, 30 fps, ≤10 giây. Đã xem từng file, bỏ 5 file (nền tím /
  hồng, trắng xóa, vàng phủ kín, gần như đen). 8 nhóm: sparkle, gold, bokeh, light_leak, dust, magic, glitter, smoke.
- `build_video.py`: hiệu ứng `fx_<nhóm>` chọn file và điểm bắt đầu theo cảnh, phóng lên 1080x1920, chồng kiểu screen (phần
  đen biến mất), mờ vào / ra 0,3 giây, độ mạnh `FX_OPACITY` và tăng sáng `FX_GAIN` theo nhóm (nền Irasutoya sáng nên phải
  tăng sáng mới thấy). Tiếng: sparkle / glitter / magic キラン, gold シャキーン.
- `variety.py: add_overlay`: tự gắn theo `emotion`, cảnh `sepia` (vệt sáng), nền cảm xúc `mood_*`; tối đa ~30% số cảnh,
  không lặp nhóm hai cảnh liền; kịch bản đã đặt `fx_` thì giữ. `script_guide.md`: bảng nhóm `fx_`.
Kiểm tra: 015 / 012 / 003 nhận 21 / 11 / 14 hiệu ứng, `check()` đạt; dựng thử cảnh 1, 3, 4, 12, 20 của 015 (khói, vệt sáng,
lấp lánh, bokeh, kỳ diệu): thấy rõ sau khi tăng sáng, nhân vật không bị che.

## 2026-10-08: chớp mắt, mấp máy miệng, máy quay nhích khi nhân vật cất lời

Theo góp ý "nâng tầm chuyển động" (camera 2 nhịp, phản ứng khi nói, cú chốt, chuyển động nhỏ). Cú chốt (`punchline`:
`build` → cắt → `impact` + ドドン) đã có từ trước; thêm:
- `tools/make_faces.py` (bước mới "Mắt, miệng" trong tools/auto.py, sau Tách nền; lỗi thì bỏ qua, video vẫn dựng):
  cảnh close / half, mỗi ảnh nhân vật (kể cả tư thế 2, nhiều nhân vật) -> `cutouts/faces/<ảnh>_blink.png`, `_talk.png`.
  Chớp mắt vẽ bằng code (tìm chấm mắt trong vùng da mặt, tô màu da, vẽ nét cong; không thấy mắt dạng chấm thì bỏ), không
  tốn API, khớp tuyệt đối. Miệng mở nhờ model ảnh, chỉ lấy thay đổi trong dải miệng của mặt và dán lên ảnh gốc (model hay
  đổi luôn mắt, mũi -> bỏ phần đó), căn lệch ±8 px. Chỉ nhân vật đang nói câu thoại mới cần ảnh miệng (~25 ảnh / video).
  Cấu hình `[faces]` trong settings.toml.
- `build_video.py`: chớp mắt ngẫu nhiên mỗi 2,2-4,2 giây (0,13 giây); miệng mở theo âm lượng giọng của câu, nhịp 3 khung.
  Máy quay `talk_in`: nhích vào ~108% trong 0,18 giây rồi trôi chậm.
- `variety.py`: `main_voice()` / `is_dialogue()`: câu thoại = không phải giọng kể chính (kể cả nhân vật chính tự kể), hoặc có
  「」. Câu thoại: cách một câu một lần `talk_in`, tối đa ~15% số cảnh; chỉ câu thoại mới mấp máy miệng.
- `tools/fix_scenes.py --apply`: ảnh được thay thì xóa ảnh mắt / miệng cũ của nó và tạo lại.
Kiểm tra: video 015 cảnh 2, 4, 7, 17: chớp mắt đúng cả mặt đang nháy một mắt, mặt nhăn; ảnh miệng chỉ đổi miệng; dựng thử
cảnh 4 (friend_papa nói): miệng mấp máy theo giọng, máy quay nhích vào; `check()` đạt với 015, 012.

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
