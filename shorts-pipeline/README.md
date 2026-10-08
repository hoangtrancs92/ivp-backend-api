# Pipeline video truyện ngắn nét Irasutoya

Video dọc 1080x1920 tiếng Nhật: nền và nhân vật nét Irasutoya, mỗi cảnh gồm vài lớp ảnh chuyển động riêng, phụ đề, tiêu đề, giọng đọc, nhạc nền.
Sinh ảnh chạy trên Kaggle (GPU T4 x2) qua API; các bước còn lại chạy ở máy.

Mọi lệnh chạy trong PowerShell, đứng ở thư mục dự án:

```
cd D:\videoprogenai\shorts-pipeline
```

## 1. Làm một video: ba lệnh

```
python tools/make_jobs.py   videos/<tên>     # từ script.json tạo jobs.json: mọi ảnh còn thiếu
python tools/run_kaggle.py  videos/<tên>     # sinh ảnh trên Kaggle, tải về, tự chép vào đúng chỗ
python run_local.py         videos/<tên>     # tách nền -> xem trước bố cục -> giọng đọc -> output.mp4
```

Đầu vào duy nhất là `videos/<tên>/script.json` (mục 5). Không bước nào gọi Claude. Bước nào thấy kết quả đã có thì bỏ qua, nên chạy lại bao nhiêu lần cũng được.

```
script.json
   │  tools/make_jobs.py
   ▼
jobs.json ── ref_<nhân vật>   ảnh chuẩn (chỉ khi config/refs/ chưa có)
          ── ch_<cảnh>        ảnh chủ thể từng cảnh: nhân vật (sinh từ ảnh chuẩn, cầm sẵn đồ vật) hoặc đồ vật
          ── ch_<cảnh>_alt    tư thế thứ hai (cảnh có alt_pose), sửa từ ảnh của cảnh
          ── bg_<bối cảnh>    ảnh nền, LoRA 0.8 (chỉ khi library/ chưa có)
   │  tools/run_kaggle.py
   ▼
config/refs/<nhân vật>_front.png      dùng chung mọi video
library/backgrounds/<bối cảnh>.png    dùng chung mọi video
videos/<tên>/characters/
   │  run_local.py
   ▼
videos/<tên>/output.mp4
```

### Hoặc dùng trang web (nhiều người dùng)

```
cd web; npm install; npm run build; cd ..     # một lần, và mỗi khi sửa giao diện
python web/app.py                             # mở http://127.0.0.1:8000
python web/app.py --host 0.0.0.0              # cho máy khác cùng mạng LAN mở
```

Mỗi người đăng nhập bằng tài khoản riêng (admin tạo thêm ở trang Thành viên, hoặc `python web/app.py --add-user <tên> <mật khẩu> [--admin]`), điền khóa trong "Hồ sơ, khóa API, mật khẩu" (Kaggle username, Kaggle token, HF token, Anthropic API key), nhập đề tài và bấm **Tạo video**: `tools/auto.py` chạy trọn từ kịch bản tới `output.mp4`, trang hiện tiến trình từng bước và số ảnh Kaggle đã vẽ. Claude duyệt từng ảnh sau mỗi lượt Kaggle, ảnh hỏng được vẽ lại (tối đa 3 lượt). Tài khoản Kaggle mới phải bấm "Đưa LoRA lên" (trang Thành viên) một lần trước. Giờ GPU lấy thẳng từ Kaggle (`kaggle quota`).

Chạy tự động không qua web: `python tools/auto.py videos/<tên>` (đề tài trong `videos/<tên>/prompt.txt`).

## 2. Cây thư mục

```
shorts-pipeline/
├── README.md                 file này
├── HANDOFF.md                trạng thái bàn giao, số đo trên Kaggle
├── docs/CHANGELOG.md         lịch sử thay đổi
├── config.toml               tài khoản Kaggle, khóa API (không lên git; mẫu: config.example.toml)
├── config/                   ── cấu hình của kênh, dùng chung mọi video
│   ├── settings.toml         mọi thông số chỉnh được
│   ├── characters.json       ngoại hình và giọng đọc từng nhân vật
│   ├── locations.json        prompt ảnh nền từng bối cảnh
│   └── refs/                 ảnh chuẩn nhân vật: <nhân vật>_front.png
├── library/                  ── tài nguyên dùng chung mọi video
│   ├── backgrounds/          ảnh nền theo bối cảnh: <bối cảnh>.png
│   └── stickers/             ký hiệu cảm xúc
├── fonts/                    Noto Sans CJK JP Black
├── tools/                    make_jobs.py, run_kaggle.py, make_stickers.py, make_placeholders.py
├── steps/                    01_script.py (Claude, tùy chọn), 04_cutouts.py, 06_voice.py, common.py
├── kaggle_job/               mã chạy trên Kaggle (worker.py, kernel_main.py)
├── build_video.py            dựng video theo lớp, phụ đề, kiểm tra kịch bản
├── effects.py                hiệu ứng vẽ bằng code (hào quang, tia sáng, lấp lánh...)
├── variety.py                tự chọn anim, motion, chuyển cảnh còn trống cho đa dạng
├── run_local.py              chạy phần ở máy
├── review.py                 Claude duyệt ảnh và bố cục (tùy chọn)
├── web/                      trang web nhiều người dùng: app.py (server), src/ (React)
├── data/                     hồ sơ, khóa, lịch sử chạy của trang web (không lên git)
├── train/                    tài liệu train LoRA trên notebook Kaggle (đã train xong)
├── docs/                     thiết kế đầy đủ, bản dựng v1
└── videos/
    ├── 001-futatsu-no-jokki/ ── một video
    │   ├── script.json       ĐẦU VÀO: kịch bản (viết tay hoặc bằng steps/01_script.py)
    │   ├── jobs.json         tự tạo bởi make_jobs.py
    │   ├── characters/       ảnh nhân vật từng cảnh (từ Kaggle)
    │   ├── cutouts/          ảnh đã tách nền
    │   ├── audio/            giọng đọc từng câu
    │   ├── music.mp3         nhạc nền (tự thêm, không bắt buộc)
    │   ├── output.mp4        KẾT QUẢ
    │   └── work/             file tạm, xóa được: kaggle/ (ảnh tải về), preview/ (xem trước bố cục), build/
    └── _tests/               video thử nghiệm (000-dry-run, 000-kaggle-test, 000-bg-test)
```

Quy ước:
- Tên thư mục video: `<số 3 chữ số>-<tên ngắn không dấu>`, ví dụ `002-ojiisan-no-tokei`.
- Thứ dùng lại giữa các video (nhân vật, bối cảnh, sticker) nằm ở `config/` và `library/`; thư mục video chỉ chứa thứ riêng của video đó.
- Git chỉ lưu `script.json` và `jobs.json` của mỗi video; ảnh, âm thanh, video và `work/` sinh lại được.

## 3. Quyết định đã chốt

Lịch sử chi tiết từng thay đổi (lý do, kết quả kiểm tra): `docs/CHANGELOG.md`.

| Ngày | Quyết định | Lý do |
|---|---|---|
| 2026-10-05 | Video tiếng Nhật; giọng đọc edge-tts | Giống video mẫu; edge-tts miễn phí, không cần khóa |
| 2026-10-06 | Style LoRA: checkpoint 750 (`irasutoya_style_v1.safetensors` trên Kaggle) | Chọn qua ảnh mẫu |
| 2026-10-06 | Sinh ảnh trên Kaggle, không sinh ở máy | Máy local (GTX 1060 3GB, RAM trống ~12GB) không nạp nổi model |
| 2026-10-06 | **Ảnh nền dùng style LoRA cố định 0.8**, prompt `irasutoya_style, background illustration of ..., flat colors, simple shapes` | Nền "detailed anime" lệch tông với nhân vật. Đã thử 0 / 0.5 / 0.8 / 1.0 (`videos/_tests/000-bg-test/so_sanh_nen.png`); 0.8 sát nét nhân vật nhất, 1.0 bố cục kém hơn |
| 2026-10-06 | Tách nền bằng `isnet-general-use` | Mặc định của rembg (`bria-rmbg`) mất ~15 giây/ảnh và ~13GB RAM |
| 2026-10-06 | Mỗi nhân vật có một ảnh chuẩn trong `config/refs/`; ảnh từng cảnh sinh từ ảnh chuẩn | Giữ nhân vật giống nhau giữa các cảnh (ưu tiên số một trong HANDOFF.md). Ảnh có tham chiếu ra 768px |
| 2026-10-06 | Ảnh nền và ảnh chuẩn dùng chung mọi video (`library/backgrounds/`, `config/refs/`) | Sẽ làm nhiều video; bối cảnh và nhân vật lặp lại không phải sinh lại |
| 2026-10-06 | Mỗi cảnh sinh một ảnh, chưa có bước chọn giữa nhiều ứng viên | Làm sau; ảnh xấu thì xóa và chạy lại |
| 2026-10-06 | Hai tư thế luân phiên (`alt_pose`) chỉ đặt cho cảnh cần cử động: đi, chạy, nói, vẫy tay | Mỗi `alt_pose` tốn thêm một ảnh sinh trên Kaggle. Video 001: 11 cảnh |
| 2026-10-06 | Lớp neo vào lớp khác (`"at": "father.hand_left"`) đi theo chuyển động và độ phóng to của lớp đó | Sticker cạnh đầu, chữ tượng thanh không bị bỏ lại khi nhân vật nhảy, đi ra, tiến lại gần |
| 2026-10-06 | **Không dùng đạo cụ tách rời**: đồ vật nhân vật cầm vẽ luôn trong ảnh (ghi trong `action`); cảnh chỉ có đồ vật dùng `object` | Đạo cụ rời không khớp tay khi nhân vật đổi tư thế, mô tả riêng dễ sai. Đổi lại đồ vật không chuyển động riêng |
| 2026-10-07 | **Chuyển động tự đa dạng** (`variety.py`): anim, motion, chuyển cảnh để trống thì tự chọn theo cảm xúc, nhịp truyện, bối cảnh, không lặp 2 cảnh trước; thêm 13 anim, 8 motion, 10 kiểu chuyển cảnh | Người dùng thấy video lặp một kiểu nhún và zoom |
| 2026-10-07 | Ảnh có bối cảnh vẽ dính (cột, tường) đặt `edge_left`/`edge_right`, đứng yên, không `alt_pose` | Cột trôi theo nhân vật khi nhún; ảnh thứ hai hay lệch |
| 2026-10-07 | **Phụ đề cỡ 144** (gấp đôi), tự ngắt dòng tiếng Nhật, tối đa 3 dòng | Chữ cũ nhỏ khó đọc trên điện thoại |
| 2026-10-07 | **Hiệu ứng vẽ bằng code** (`effects.py`): hào quang, tia sáng, lấp lánh, tim, nước mắt, đường manga, chớp, phủ tối, giấy màu, mưa | Sticker tĩnh còn thô; cần hiệu ứng động cho cảm xúc |
| 2026-10-07 | `build_video.py` kiểm tra kịch bản trước khi dựng, có lỗi thì dừng | Không để ra video lỗi hiệu ứng |
| 2026-10-06 | **Ảnh nhân vật và đồ vật sinh trên nền xanh lá đặc**, tách nền theo màu | Trên nền trắng, mọi model tách nền đều khoét thủng chỗ trắng của nhân vật (áo trắng, bọt bia). Đã thử nền trắng, magenta, xanh lá; xanh lá phẳng nhất, ít nhuộm màu lên nhân vật |
| 2026-10-06 | **Khung hình theo cảnh** (`shot`: `full`, `half`, `close`); nhân vật to hơn (`large` 0.42 → 0.52) | Không phải cảnh nào cũng cần toàn thân; nhân vật nhỏ để lại nhiều nền thừa |
| 2026-10-06 | **Quy tắc viết kịch bản tách ra `config/script_guide.md`**, gửi kèm cho Claude khi viết kịch bản | Sửa quy tắc không cần sửa code; kịch bản đa dạng hơn (khung hình, sticker, chuyển động) |
| 2026-10-06 | Token Hugging Face gửi kèm dataset job riêng tư lên Kaggle | Tải model có đăng nhập, ít bị giới hạn. Token rời khỏi máy nhưng chỉ nằm trong dataset riêng tư |
| 2026-10-06 | **Sticker tự khớp nhân vật**: vị trí theo hình dáng thật (đầu, tay), cỡ theo cỡ nhân vật, luôn nằm trong khung | Điểm neo theo khung chữ nhật làm sticker đứng xa và bị cắt ở mép |

Đổi một quyết định: sửa giá trị trong `config/settings.toml` và ghi thêm một dòng vào bảng này.

## 4. File cấu hình

| File | Chứa gì | Lên git |
|---|---|---|
| **`config/settings.toml`** | **Mọi thông số chỉnh được** (bảng dưới) | Có |
| `config.toml` | Tài khoản Kaggle, tên dataset và kernel, giới hạn thời gian chạy, khóa API. `hf_token` được gửi kèm dataset job riêng tư lên Kaggle; các khóa khác không rời máy. Mẫu: `config.example.toml` | Không |
| `C:\Users\Tran Hoang\.kaggle\access_token` | Token Kaggle `KGAT_...`; Kaggle CLI tự đọc | Không |
| `config/characters.json` | Ngoại hình (tiếng Anh, dùng trong prompt) và giọng đọc của từng nhân vật; `"ref": "<nhân vật khác>"` để dùng chung ảnh chuẩn (vd mẹ mặc áo bệnh nhân dùng ảnh chuẩn của mẹ) | Có |
| `config/script_guide.md` | Quy tắc viết kịch bản: đồ vật, khung hình, bố cục, sticker, chuyển động, độ đa dạng. `steps/01_script.py` gửi nguyên văn cho Claude | Có |
| `config/locations.json` | Prompt ảnh nền của từng bối cảnh | Có |

Các mục trong `config/settings.toml`:

| Mục | Dùng ở | Thông số chính |
|---|---|---|
| `[generation]` | Kaggle (gửi lên kèm `jobs.json`) | model, file LoRA, cỡ ảnh (`size_text` 1024, `size_ref` 768), số bước, seed, `ref_wait` |
| `[background]` | `tools/make_jobs.py` | `lora = 0.8`, `width = 768`, `height = 1344` |
| `[cutout]` | `tools/make_jobs.py`, `steps/04_cutouts.py` | `key_prompt` (nền xanh lá khi sinh ảnh), `key_low`/`key_high` (ngưỡng tách theo màu), `spill_min_bright`/`spill_max` (khử ánh xanh trên thủy tinh, bọt), `model` (rembg, chỉ cho ảnh nền trắng cũ) |
| `[shots]` | `tools/make_jobs.py`, `build_video.py` | Mỗi khung hình `full`/`half`/`close`: câu chèn vào prompt, cỡ và vị trí mặc định của lớp nhân vật |
| `[voice]` | `steps/06_voice.py` | ngưỡng cắt khoảng lặng |
| `[video]` | `build_video.py` | nghỉ sau mỗi câu, âm lượng nhạc, cỡ chữ tiêu đề và phụ đề (`subtitle_size` 144, `subtitle_margin`, `subtitle_top`), `alt_interval` (giây giữa hai lần đổi tư thế, 0.25) |
| `[layout]` | `build_video.py` | tọa độ các vị trí có tên (`center`, `left`...), chiều cao các cỡ (`tiny`...`huge`), `sticker_gap` (khoảng hở sticker và đầu), `edge_margin` (lề tới mép khung) |

Mẫu prompt ảnh chuẩn, ảnh cảnh, ảnh đồ vật và tư thế thứ hai nằm ở đầu `tools/make_jobs.py` (`CAST`, `SCENE`, `OBJECT`, `ALT`).

## 5. Viết `script.json`

Quy tắc viết kịch bản (đồ vật, khung hình, bố cục, sticker, chuyển động, độ đa dạng) nằm ở **`config/script_guide.md`**; bảng dưới chỉ là các trường kỹ thuật.

Ví dụ đầy đủ: `videos/001-futatsu-no-jokki/script.json`. Mỗi cảnh:

```json
{"id": 3, "text": "無口で、怖い人だった。", "speaker": "narrator",
 "characters": ["father"], "action": "sitting, holding a glass beer mug full of golden beer", "emotion": "stern",
 "location": "dining_room", "motion": "zoom_in", "filter": "none",
 "layers": [
   {"id": "father", "image": "cutouts/003.png", "size": "large", "at": "center", "anim": "pulse"},
   {"image": "stickers/anger.png", "size": "tiny", "at": "father.beside_left", "anim": "pop", "start": 0.3}
 ]}
```

| Trường | Ghi chú |
|---|---|
| `characters` | Tên trong `config/characters.json`. Một nhân vật: ảnh `cutouts/003.png`; nhiều nhân vật: `cutouts/003_father.png`, `cutouts/003_me.png` |
| `action`, `emotion` | Tiếng Anh, đi thẳng vào prompt. Đồ vật nhân vật cầm ghi luôn ở đây, vd `holding a white smartphone to her ear`; nó được vẽ trong ảnh nhân vật |
| `object` | Cảnh không có nhân vật (`"characters": []`): mô tả tiếng Anh cả nhóm đồ vật trong một ảnh, vd `"two glass beer mugs full of beer clinking together"`. Ảnh `cutouts/NNN.png`, đặt lớp `"id": "objects"` để sticker và chữ neo vào. (Trường `props` cũ không còn dùng) |
| `shot` | `full` (toàn thân), `half` (nửa người từ thắt lưng), `close` (cận mặt và vai). Bỏ trống = `full`. Chọn theo `config/script_guide.md`. Lớp nhân vật chính bỏ trống `size`, `at` thì tự lấy theo `[shots]`; `half`, `close` đứng sát mép dưới khung (`floor`) |
| `location` | Tên trong `config/locations.json` |
| `at`, `path` | `center`, `left`, `right`, `top`, `top_left`, `top_right`, `bottom`, `floor`, `floor_left`, `floor_right` (sát mép dưới), `edge_left`, `edge_right` (sát mép trái/phải và mép dưới, cho ảnh có cột, tường vẽ dính), `off_left`, `off_right`, `off_top`, `off_bottom`; hoặc `<id>.<điểm neo>` với `center`, `top`, `bottom`, `left`, `right`, `above`, `head`, `beside_left`, `beside_right`, `hand_left`, `hand_right`; hoặc `[x, y]` |
| `size` | `tiny`, `small`, `medium`, `large`, `huge`, hoặc số. Lớp neo vào lớp khác thì cỡ tỉ lệ theo lớp đó (sticker của nhân vật nhỏ cũng nhỏ) |
| Điểm neo tự khớp | `beside_left`, `beside_right`, `above`, `head`, `hand_left`, `hand_right` tính từ hình dáng thật của lớp cha (vị trí và bề rộng của đầu, điểm xa nhất của tay), không phải khung chữ nhật. Lớp đứng yên bằng `at` luôn nằm trọn trong khung; sticker cạnh đầu mà tràn mép thì tự đổi sang bên kia |
| `anim` (lớp) | **Để trống thì tự chọn** theo `emotion`, khác 2 cảnh trước (`variety.py`). Có: `nod`, `shake_no`, `sway`, `tilt`, `breathe`, `shiver`, `hop`, `sink`, `float`, `punch`, `spin_in`, `lean_in`, `rise`, `bounce`, `jump`, `pulse`, `wobble`, `pop`, `pop_fade`, `drop`, `slide_left`, `slide_right`, `exit_left`, `exit_right`, `approach`, `recede`, `none` |
| `effect` (lớp) | Hiệu ứng vẽ bằng code: `{"effect": "aura", "on": "father", "start": 0.2, "duration": 1.2, "colour": "#FFB3D1"}`. Có: `aura`, `rays`, `sparkles`, `hearts`, `tears` (bám nhân vật, cần `on`), `speed_lines`, `flash`, `gloom`, `confetti`, `rain` (phủ cả khung). Đặt trước lớp nhân vật để nằm sau. Khi nào dùng: `config/script_guide.md` mục 5 |
| `text` | Phụ đề cỡ 144, khoảng 7 chữ một dòng, tự ngắt; tối đa khoảng 12 chữ, tự đặt `
` ở chỗ ngắt tự nhiên, không quá 3 dòng |
| `fill_holes` (lớp ảnh) | `"#RRGGBB"`: tô kín lỗ trong suốt nằm gọn bên trong hình (lòng tấm ảnh chụp, khung tranh); vùng thông ra mép không bị tô |
| `alt_pose` (của cảnh) | Hai tư thế luân phiên. Mô tả tiếng Anh tư thế thứ hai, vd `"the other leg stepping forward"` (đi), `"mouth open while talking"` (nói), `"the waving hand moved to the other side"` (vẫy tay). Một chuỗi áp cho mọi nhân vật trong cảnh, hoặc `{"father": "...", "me": null}` cho từng người. `make_jobs.py` sinh thêm `characters/<cảnh>_alt.png` sửa từ ảnh gốc của cảnh; khi dựng, mọi lớp có bản `_alt` đổi qua lại mỗi `alt_interval` giây. **Chỉ đặt cho cảnh cần cử động**, cảnh khác để `null` hoặc bỏ trống |
| `motion` (cả cảnh) | **Để trống thì tự chọn** theo `beat`, khác 2 cảnh trước. Có: `punch_in`, `focus`, `dutch`, `drift`, `dolly_left`, `dolly_right`, `tilt_up`, `tilt_down`, `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `shake`, `none` |
| `transition` (cả cảnh) | Chuyển cảnh trong 0,3 giây đầu (`[video] transition`). **Để trống thì tự chọn**: đổi bối cảnh thì đẩy, lia, quét, vòng tròn...; vào hoặc ra hồi tưởng thì `fade`; vào twist thì `flash`; cùng chỗ phần lớn `cut`. Có: `cut`, `fade`, `push_left`, `push_right`, `push_up`, `whip`, `zoom`, `flash`, `wipe`, `iris` |
| `filter` | `none`, `sepia` (hồi tưởng) |

Thêm nhân vật mới: thêm vào `config/characters.json`. Lần chạy đầu `make_jobs.py` tự tạo ảnh chuẩn cho nhân vật đó.
Thêm bối cảnh mới: thêm vào `config/locations.json`.

## 6. Chi tiết từng lệnh

### `tools/make_jobs.py videos/<tên>`

Ghi lại toàn bộ `jobs.json` từ `script.json`, chỉ gồm ảnh còn thiếu. Muốn sinh lại một ảnh: xóa file ảnh đó (vd `characters/012.png`, `config/refs/father_front.png`, `library/backgrounds/kitchen.png`) rồi chạy lại.

### `tools/run_kaggle.py videos/<tên>`

```
python tools/run_kaggle.py videos/<tên> --dry-run    # kiểm tra jobs.json, in lệnh, không gửi
python tools/run_kaggle.py videos/<tên>              # gửi, chờ, tải về, chép vào đúng chỗ
python tools/run_kaggle.py videos/<tên> --fetch      # chỉ tải lại kết quả lần chạy gần nhất, không gửi
```

- Ảnh về `videos/<tên>/work/kaggle/out/<name>.png`, kèm `<name>.json` ghi prompt, seed, cường độ LoRA, GPU, số giây.
- Chép theo tiền tố tên: `bg_x` → `library/backgrounds/x.png`, `ref_x` → `config/refs/x_front.png`, `ch_x` → `characters/x.png`. Ảnh đã có thì giữ.
- Log trên Kaggle: https://www.kaggle.com/code/tranhoang1124/shorts-gen
- Số đo thật: lô 6-7 ảnh hết khoảng 8 phút, mỗi ảnh 53-79 giây trên hai GPU. Video 001 (65 ảnh) ước khoảng 35 phút. Hạn mức Kaggle 30 giờ GPU mỗi tuần, 12 giờ mỗi lần chạy.
- Đổi checkpoint LoRA (một lần): `python tools/run_kaggle.py <file .safetensors> --upload-lora`, rồi sửa `lora_file` trong `[generation]`.

### `run_local.py videos/<tên>`

Kiểm tra đủ ảnh (thiếu thì liệt kê và dừng), rồi chạy: tách nền (`cutouts/`), xem trước bố cục (`work/preview/`), giọng đọc (`audio/`), dựng `output.mp4`.

Chạy từng bước:

```
python steps/04_cutouts.py videos/<tên>
cd videos/<tên>; python ../../build_video.py --preview; cd ../..
python steps/06_voice.py videos/<tên>
cd videos/<tên>; python ../../build_video.py; cd ../..
```

Sửa bố cục: đổi `at`, `size`, `anim` trong `script.json`, chạy lại `--preview`, xem `work/preview/`. Đổi cho mọi cảnh: sửa `[layout]` trong `config/settings.toml`.

## 7. Cài đặt (làm một lần)

```
pip install kaggle pillow "rembg[cpu]" edge-tts anthropic
```

Cần `ffmpeg` (đã cài bằng winget; nếu không tìm thấy thì mở cửa sổ PowerShell mới).
Kiểm tra đăng nhập Kaggle, phải thấy `tranhoang1124/irasutoya-style-lora`:

```
kaggle datasets list --mine
```

## 8. Tùy chọn: Claude viết kịch bản và duyệt ảnh

Cần credit API Claude và `setx ANTHROPIC_API_KEY "sk-ant-..."` (mở PowerShell mới sau lệnh này).

```
python steps/01_script.py videos/<tên> "chủ đề truyện"   # viết script.json
cd videos/<tên>
python ../../review.py images                            # chấm ảnh nhân vật, ảnh hỏng chuyển sang rejected/
python ../../review.py layout                            # góp ý bố cục (xem work/preview/) vào review/layout.json
```

Ước tính 1,5-2,5 USD mỗi video nếu dùng cả ba (chưa đo).

## 9. Lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| `Authentication required to call the Kaggle API` | Tạo token mới ở kaggle.com/settings/api, lưu vào `~/.kaggle/access_token` |
| `UnicodeEncodeError: 'charmap' codec` | Chạy `$env:PYTHONUTF8 = "1"` trước lệnh |
| `ffmpeg` không tìm thấy | Mở cửa sổ PowerShell mới |
| `Thiếu ... ảnh, cần sinh trên Kaggle trước` | Chạy `make_jobs.py` rồi `run_kaggle.py` |
| `jobs.json: ... không đứng trước nó` | Job có `@x` phải nằm sau job `x` (make_jobs.py đã xếp đúng) |
| Kernel thất bại | Mở trang kernel trên Kaggle, xem tab Logs; sửa xong chạy lại, ảnh đã có không sinh lại |
| Ảnh nhân vật lệch so với ảnh chuẩn (vd mất kính) | Ghi rõ chi tiết trong `config/characters.json`, xóa ảnh hỏng, chạy lại |
