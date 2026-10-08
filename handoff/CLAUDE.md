# Pipeline video truyện ngắn nét Irasutoya

Tài liệu bàn giao từ một cuộc trao đổi trước. Đọc hết file này trước khi làm việc. Trả lời người dùng bằng tiếng Việt; người dùng thích giải pháp gọn, dễ đọc, không dựng quá mức cần thiết.

## Mục tiêu

Làm video dọc 1080x1920 kể truyện ngắn (60-120 giây), giống một video TikTok mẫu của Nhật: nhân vật nét phẳng kiểu Irasutoya đặt trên nền chi tiết kiểu anime, có tiêu đề cố định, phụ đề viền màu theo người nói, giọng đọc, nhạc nền.

Chuyển động trong video mẫu là motion graphics, không phải AI sinh video: mỗi cảnh gồm vài ảnh tĩnh xếp lớp, mỗi lớp di chuyển riêng (nhân vật nhún, cốc bia lắc, đá rơi vào cốc, sticker bật ra, chữ tượng thanh bật ra rồi mờ đi, đoạn hồi tưởng ngả màu nâu). Không có khung hình nào nhân vật đổi tư thế. Vì vậy model image-to-video không nằm trong pipeline chính.

## Kiến trúc

Hai phần. Mọi thành phần trao đổi qua file trong thư mục dự án.

**Phần 1, train (làm một lần):** dataset 89 ảnh + 89 caption `.txt` → AI Toolkit (ostris) train LoRA trên `FLUX.2-klein-base-4B` → chọn checkpoint bằng ảnh mẫu → `loras/style.safetensors`.

**Phần 2, sản xuất (mỗi video):**

| Bước | Việc | Công cụ | Đầu ra |
|---|---|---|---|
| 1 | Viết kịch bản | Claude | `script.json` |
| 2 | Ảnh nền | klein 4B distilled, không LoRA | `backgrounds/<location>.png` |
| 3 | Nhân vật, đạo cụ | klein 4B distilled + style LoRA, nền trắng | `characters/NNN.png`, `props_raw/<tên>.png` |
| 4 | Tách nền | rembg, cắt sát mép | `cutouts/`, `props/` |
| 5 | Bố cục lớp | `build_video.py --preview` | `scenes/NNN.png`, `layers` đã chốt |
| 6 | Giọng đọc | TTS | `audio/NNN.wav` |
| 7 | Dựng | `build_video.py` (Pillow + ffmpeg) | `output.mp4` |
| 8 | Kiểm tra | người xem | |

Bản Base chỉ dùng để train. Sinh ảnh luôn dùng bản distilled `FLUX.2-klein-4B` (4 bước, guidance 1.0); LoRA train trên Base gắn được vào distilled.

Cấu trúc thư mục dự án:

```
shorts-pipeline/
  config/characters.json, locations.json
  loras/style.safetensors
  library/backgrounds/, library/stickers/
  videos/<tên>/script.json, backgrounds/, characters/, props_raw/, cutouts/, props/,
               scenes/, audio/, rejected/, review/, music.mp3, output.mp4
  build_video.py, review.py
```

## Các file trong thư mục bàn giao này

- `build_video.py`: bộ dựng theo lớp. Đã chạy thử với dữ liệu giả (6 cảnh, đủ 9 kiểu `anim`, 6 kiểu `motion`, sepia, lớp neo vào lớp khác, đường đi qua nhiều điểm). Chưa chạy với ảnh và giọng đọc thật. Tốc độ đo được khoảng 3 giây xử lý cho mỗi giây video.
- `review.py`: cho Claude duyệt ảnh (`images`) và bố cục (`layout [--apply]`). Phần khung đã thử với câu trả lời giả. Lời gọi API thật chưa thử; tên model mặc định trong file cần kiểm tra lại với tài liệu API hiện hành.
- `style_kaggle.yaml`: cấu hình train theo trạng thái dự kiến cuối cùng (xem "Trạng thái train").
- `pipeline_video_truyen_ngan.html`: sổ tay đầy đủ (schema, từng bước, phần AWS, chi phí). Là nguồn tham chiếu chi tiết; file này tóm tắt nó.
- `workflow_video_truyen_ngan.png`: sơ đồ quy trình.

## Schema `script.json` (phần dựng)

Lớp được đặt bằng tên, không dùng tọa độ. Script đổi tên thành tọa độ theo kích thước thật của ảnh.

```json
{
  "title": ["Dòng 1", "Dòng 2"],
  "font": "Noto Sans CJK JP", "font_file": "../../fonts/...otf",
  "speakers": { "narrator": "#4FC3F7" },
  "scenes": [{
    "id": 1, "text": "...", "speaker": "narrator",
    "characters": ["father"], "action": "...", "emotion": "...",
    "props": { "beer": "a glass mug of beer with foam" },
    "location": "dining_room", "motion": "zoom_in", "filter": "none",
    "layers": [
      { "id": "father", "image": "cutouts/001.png", "size": "large", "at": "center", "anim": "bounce" },
      { "id": "beer", "image": "props/beer.png", "size": "medium", "at": "father.hand_left", "anim": "wobble" },
      { "image": "props/ice.png", "size": "tiny", "path": ["off_left", "father.above", "beer.top"], "over": 1.0 },
      { "word": "キンキンで", "at": "father.beside_right", "vertical": true, "anim": "pop_fade", "start": 0.4, "duration": 0.9 }
    ]
  }]
}
```

- `at` / `path`: tên trong `SLOTS` (`center`, `left`, `right`, `top`, `top_left`, `top_right`, `bottom`, `off_left`, `off_right`, `off_top`, `off_bottom`), hoặc `<id>.<điểm neo>` (`center`, `top`, `bottom`, `left`, `right`, `above`, `head`, `beside_left`, `beside_right`, `hand_left`, `hand_right`), hoặc `[x, y]` theo tỉ lệ khung hình.
- `size`: `tiny`, `small`, `medium`, `large`, `huge`, hoặc số.
- `anim`: `none`, `bounce`, `wobble`, `pulse`, `pop`, `pop_fade`, `drop`, `slide_left`, `slide_right`. Với `path`, `anim` chạy sau khi lớp tới nơi.
- `motion` (cả khung): `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `shake`, `none`. `filter`: `none`, `sepia`.
- Thứ tự trong `layers` là thứ tự vẽ.

Giới hạn đã biết: điểm neo tính từ khung bao của ảnh, script không nhìn nội dung ảnh. `hand_left` / `hand_right` chỉ là ước lượng cho nhân vật đứng thẳng. Các giá trị trong `SLOTS`, `SIZES` và biên độ trong `animate()` ước lượng bằng mắt từ video mẫu, cần tinh chỉnh khi có ảnh thật.

## Trạng thái train (tại thời điểm bàn giao)

Người dùng không có máy local đủ mạnh. Kết quả thực tế:

- **Colab free: không dùng được.** Phiên sập ở `Loading transformer` khi RAM hệ thống chạm 12,7GB.
- **Kaggle (GPU T4 x2, 30GB RAM): chạy được.** Model nạp xong, cache xong, bước train chạy.
- Tốc độ đo được ở độ phân giải `[512, 768]`: khoảng 21 giây mỗi bước (2000 bước ≈ 11,5 giờ, sát giới hạn 12 giờ mỗi phiên).
- Tắt `low_vram` không nhanh hơn và gây cảnh báo hết bộ nhớ GPU, nên giữ `low_vram: true`.
- Đề xuất cuối cùng đã đưa cho người dùng: đổi sang `resolution: [512]` để nhanh gấp đôi. **Chưa xác nhận người dùng đã áp dụng và tốc độ thật là bao nhiêu. Hãy hỏi trước khi giả định.**

Những điều phải nhớ khi dựng lại môi trường trên Kaggle:

- Notebook cần bật Internet, Accelerator GPU T4 x2, và Persistence "Files only" (tài khoản phải xác minh số điện thoại). Chưa xác nhận người dùng đã bật Persistence.
- Dataset nằm ở `/kaggle/input/datasets/tranhoang1124/irasutoya-style` (chỉ đọc). Chép sang `/kaggle/temp/dataset/irasutoya_style`, và `rm -rf` thư mục đích trước khi chép: lần trước chép hai lần nên trainer thấy 178 ảnh thay vì 89 (vô hại nhưng gây hiểu nhầm).
- Cài AI Toolkit vào `/kaggle/temp` với môi trường Python 3.12 (`uv venv --clear --python 3.12`). Phiên bản torch phải theo README của AI Toolkit: `torch==2.13.0 torchvision==0.28.0 torchaudio==2.11.0` từ `https://download.pytorch.org/whl/cu130`. Không ghi phiên bản thì `torchaudio` không cài được và trainer báo `No module named 'torchaudio'`.
- Cấu hình bắt buộc có `train.noise_scheduler: "flowmatch"`; thiếu thì lỗi `mu must be passed when use_dynamic_shifting is set`. Nên có `train.dtype: "bf16"`.
- Model klein 4B tải được không cần token Hugging Face. Đặt `HF_HOME=/kaggle/temp/hf`.
- Checkpoint ghi vào `/kaggle/working/output/irasutoya_style_v1/` (giới hạn khoảng 20GB). Chạy lại cùng cấu hình thì trainer tiếp tục từ checkpoint mới nhất.
- Hạn mức Kaggle: khoảng 30 giờ GPU mỗi tuần, 12 giờ mỗi phiên.

Lệnh train:

```
cd /kaggle/temp/ai-toolkit
/kaggle/temp/venv/bin/python run.py /kaggle/working/style_kaggle.yaml
```

## Việc tiếp theo, theo thứ tự

1. Hỏi người dùng trạng thái lần train: bước hiện tại, tốc độ, đã có checkpoint nào chưa.
2. Viết script sinh ảnh mẫu cho từng checkpoint trên Kaggle (klein distilled + từng `.safetensors`, cùng prompt, cùng seed) để chọn mốc. Sổ tay có bản nháp viết cho Colab, chưa chạy thử; cần đổi đường dẫn sang Kaggle, chạy bằng Python của môi trường `/kaggle/temp/venv`, và đối chiếu lớp pipeline của diffusers với model card.
3. Viết các script còn thiếu, hiện mới có mô tả trong sổ tay: `01_script.py`, `02_backgrounds.py`, `03_characters.py` (kèm sinh đạo cụ từ trường `props`), `04_cutouts.py`, `06_voice.py`, và `run_local.py` điều phối. Nguyên tắc: bước nào thấy kết quả đã có thì bỏ qua, để chạy lại chỉ làm phần thiếu.
4. Việc người dùng có thể làm ngay trong lúc chờ train, không cần GPU: `characters.json`, `locations.json`, kịch bản video đầu tiên (60-75 giây), giọng đọc, bộ sticker, font, nhạc nền, dựng thử `build_video.py` ở máy local.
5. Làm trọn một video ngắn bằng tay qua cả 8 bước, rồi tinh chỉnh `SLOTS`, `SIZES`, `animate()` và các tiêu chí trong `review.py` theo kết quả thật.

## Lưu ý khi làm việc

- Nói rõ cái gì đã chạy thử, cái gì chưa. Nhiều con số trong sổ tay là ước lượng (thời gian sinh ảnh trên T4, chi phí API, chi phí AWS).
- AI Toolkit đổi tên khóa cấu hình và phiên bản thư viện thường xuyên. Khi gặp lỗi, đọc README và mã nguồn hiện tại của repo trước khi đoán.
- Sinh ảnh cũng cần GPU, nên cũng chạy trên Kaggle; không chạy song song với train trong cùng phiên vì RAM đã dùng khoảng 26 trên 30GB.
- Nét vẽ Irasutoya thuộc về tác giả của nó và có điều khoản sử dụng riêng. Nếu người dùng định kiếm tiền từ video, nhắc họ tự kiểm tra điều khoản đó.
