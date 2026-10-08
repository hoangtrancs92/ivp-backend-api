# Bàn giao: pipeline video truyện ngắn nét phẳng

Đọc file này trước. `docs/pipeline_spec.md` là bản thiết kế đầy đủ; chỗ nào hai file khác nhau thì file này đúng, vì nó chứa số đo thật trên Kaggle.

## Mục tiêu của đợt này

Một lệnh chạy từ `videos/<tên>/script.json` ra `videos/<tên>/output.mp4`, với bước sinh ảnh chạy trên Kaggle (hai GPU T4) qua API, các bước còn lại chạy ở máy local. Người dùng không dựng tay được, nên mọi khâu dựng phải tự động.

Ưu tiên theo thứ tự: nhân vật giống nhau giữa các cảnh, rồi mới tới tốc độ và số ảnh. Người dùng thích code ngắn, dễ đọc, không thêm lớp trừu tượng khi chưa cần.

## Đã kiểm chứng trên Kaggle (T4 x2, 30GB RAM)

| Việc | Kết quả |
|---|---|
| Style LoRA | Train bằng ai-toolkit 0.13.23 trên FLUX.2 klein base 4B, rank 16, 178 ảnh, khoảng 512px. Người dùng đã chọn checkpoint 750: `irasutoya_style_v1_000000750.safetensors`. Trigger: `irasutoya_style`. |
| Sinh ảnh | `Flux2KleinPipeline` với `black-forest-labs/FLUX.2-klein-4B`, 4 bước, `guidance_scale=1.0`. `load_lora_weights` nhận thẳng file của ai-toolkit. |
| Cách gọi | Tham số đầu của pipeline là `image`, nên luôn gọi `prompt=...` hoặc `prompt_embeds=...` theo tên. Ảnh tham chiếu và sửa ảnh dùng chung một đường: `image=[PIL.Image, ...]`. |
| torchao | Bản cài sẵn trên Kaggle làm diffusers mới không import được. Đặt `sys.modules["torchao"] = None` trước khi import diffusers. |
| RAM | Một tiến trình nạp cả pipeline dùng khoảng 18GB RAM, nên hai tiến trình như vậy vượt 30GB. Phải mã hóa prompt trước, rồi mỗi worker chỉ nạp phần sinh ảnh. |
| VRAM, sinh từ chữ | 1024x1024 vừa T4, dùng khoảng 12,5GB khi model nằm hẳn trên GPU. |
| VRAM, có ảnh tham chiếu | 1024x1024 kèm tham chiếu thì hết bộ nhớ, kể cả khi tham chiếu thu còn 512px. Cấu hình chạy được: ảnh ra 768x768, một ảnh tham chiếu thu về 512px. |
| Tốc độ | Một GPU với `enable_model_cpu_offload`: khoảng 70 giây mỗi ảnh 1024. Model nằm hẳn trên GPU: khoảng 11 giây mỗi bước ở 1024. Hai GPU song song, 768 có tham chiếu: 31 ảnh trong 18 phút, tức khoảng 35 giây mỗi ảnh. |
| Giới hạn Kaggle | 12 giờ mỗi lần chạy, 30 giờ GPU mỗi tuần. File trong `/kaggle/working` của phiên tương tác mất khi phiên kết thúc. |

Hệ quả cho thiết kế, khác với `pipeline_spec.md`:

- Trên T4 mỗi lần sinh chỉ dùng **một** ảnh tham chiếu (chọn góc hợp với tư thế cần sinh), không dùng cả ba góc cùng lúc.
- Ảnh có tham chiếu ra ở 768px; cảnh cận mặt phóng to khi dựng.
- Một video 2 phút với 250-350 lần sinh mất khoảng 2,5-3,5 giờ trên Kaggle.

## Luồng sinh ảnh qua Kaggle

```
máy local                                   Kaggle
videos/001/jobs.json  --+
config/refs/*.png     --+-- dataset job --> kernel_main.py
kaggle_job/worker.py  --+                     1. cài thư viện
                                              2. worker.py encode      (mã hóa mọi prompt)
dataset LoRA (tạo một lần) ---------------->  3. worker.py worker i n  (mỗi GPU một tiến trình)
videos/001/generated/out/ <-- tải về -------  /kaggle/working/out/*.png + *.json
```

Lệnh: `python tools/run_kaggle.py videos/001` (thêm `--dry-run` để chỉ dựng thư mục gửi đi và in lệnh).

## Các file trong gói

| File | Vai trò | Trạng thái |
|---|---|---|
| `kaggle_job/worker.py` | Chạy trên Kaggle: mã hóa prompt, sinh ảnh, ghi file nguồn gốc cho từng ảnh | Tổng quát hóa từ script đã chạy được trên Kaggle (31 ảnh, hai GPU). Bản tổng quát này chưa chạy trên GPU. |
| `kaggle_job/kernel_main.py` | File mã của kernel: cài thư viện, chạy worker trên mọi GPU có | Chưa chạy trên Kaggle |
| `tools/run_kaggle.py` | Chạy ở local: kiểm tra jobs.json, đẩy dataset và kernel, chờ, tải kết quả | Đã chạy `--dry-run` và phần kiểm tra jobs.json. Các lệnh `kaggle` thật chưa được chạy. |
| `build_video.py` | Dựng video v1 từ ảnh đã ghép và giọng đọc | Đã chạy với 6 cảnh giả |
| `config.example.toml` | Mẫu cấu hình và khóa | |
| `examples/jobs.example.json` | Ví dụ đủ bốn loại job | |
| `docs/pipeline_spec.md` | Thiết kế đầy đủ: cấu trúc cây, chấm điểm, chuyển động, hiệu ứng, AWS | Tham khảo |

## jobs.json

```json
{"jobs": [
  {"name": "001_base", "prompt": "irasutoya_style, ...", "refs": ["ref__repairman_front.png"]},
  {"name": "002_var",  "prompt": "irasutoya_style, change the facial expression to ...", "refs": ["@001_base"]},
  {"name": "bg_street", "prompt": "detailed anime background, ...", "lora": false, "width": 768, "height": 1344}
]}
```

- `name`: tên file ảnh đầu ra, không trùng.
- `refs`: `ref__<tên file>` là ảnh chuẩn lấy từ `config/refs/`; `@<name>` là ảnh do một job khác trong cùng lần chạy sinh ra.
- Job có `@` phải đứng sau job nó tham chiếu, và job được tham chiếu không được có `@`. Đây là cấu trúc cây hai tầng: ảnh chuẩn, ảnh gốc của phân cảnh, khung biến thể. Quy tắc này cũng bảo đảm hai worker không chờ nhau vô hạn. `run_kaggle.py` kiểm tra trước khi gửi.
- `lora: false` cho ảnh nền. Worker sinh hết ảnh có LoRA rồi mới tháo LoRA để sinh nền.
- `width`, `height`, `seed` là tùy chọn. Mặc định: có `refs` thì `size_ref`, không thì `size_text`.
- Mục `settings` do `run_kaggle.py` tự chèn từ `[generation]` trong `config.toml`.

## Cấu hình

Sao chép `config.example.toml` thành `config.toml` (đã có trong `.gitignore`). Mọi khóa nằm ở đó. Chỉ mục `[generation]` được gửi lên Kaggle; không khóa nào rời khỏi máy local. Các script mới đọc khóa từ file này, không ghi cứng trong code.

Chuẩn bị một lần trên Kaggle: tạo dataset riêng tư tên trùng với `lora_dataset`, chứa file LoRA checkpoint 750.

## Việc cần làm, theo thứ tự

| # | Việc | Hoàn thành khi |
|---|---|---|
| 1 | Chạy thật `tools/run_kaggle.py` với `examples/jobs.example.json` và một ảnh chuẩn. Sửa những chỗ lệnh `kaggle` hoặc `kernel_main.py` chưa đúng. Xác nhận kernel nhận hai T4 (dòng "Số GPU: 2" trong log); nếu Kaggle cấp loại GPU khác, tìm tùy chọn chọn T4 x2 của công cụ `kaggle`. | 6 ảnh và 6 file `.json` về tới `videos/<tên>/generated/out/` |
| 2 | Khung dự án, `config/characters.json`, `config/locations.json`, hàm kiểm tra `script.json` theo schema trong `pipeline_spec.md` | Kịch bản mẫu hợp lệ thì qua, kịch bản sai thì báo đúng chỗ |
| 3 | `steps/00_make_cast.py`: tạo ảnh chuẩn cho từng nhân vật qua một job Kaggle, xuất tấm tổng hợp để người dùng duyệt | Có `config/refs/<nhân vật>_front.png` cho nhân vật mẫu |
| 4 | `steps/01_make_jobs.py`: đổi `script.json` thành `jobs.json` theo cấu trúc cây (`based_on`, `alt_pose`), 4-6 ứng viên cho mỗi ảnh gốc bằng các seed khác nhau, cộng các ảnh nền còn thiếu | `jobs.json` sinh ra qua được bước kiểm tra của `run_kaggle.py` |
| 5 | Chọn ảnh: bản đầu là một trang HTML tĩnh hoặc thư mục để người dùng chọn một ứng viên cho mỗi ảnh gốc; khung biến thể chạy ở job Kaggle thứ hai sau khi đã chọn | Mỗi cảnh có đúng một ảnh nhân vật |
| 6 | Giọng đọc, rồi nối với `build_video.py` v1. Ở vòng đầu có thể sinh cả cảnh trong một ảnh để chưa cần tách nền và ghép lớp. | Một lệnh ra `output.mp4` |
| 7 | Sau video đầu tiên: nền cảm xúc và đường tốc độ, `alt_pose`, tách lớp nhân vật và nền, chấm điểm tự động (DINOv2 và danh sách kiểm tra) | Theo `pipeline_spec.md` |

Làm xong việc 1 thì dừng lại báo kết quả trước khi làm tiếp.

## Cạm bẫy đã gặp

- Khung duyệt file của Kaggle hay báo lỗi "You must specify exactly one databundle source"; không liên quan tới code.
- Truyền prompt theo vị trí làm pipeline hiểu nhầm thành ảnh đầu vào.
- Để lại ảnh gốc cũ trong thư mục đầu ra khiến hai worker dùng hai ảnh tham chiếu khác nhau. Mỗi lần chạy trên Kaggle bắt đầu với thư mục trống nên không gặp, nhưng cần nhớ khi chạy lại trong phiên tương tác.
- `kernel_main.py` cài diffusers từ nhánh chính, thay đổi hằng ngày. Khi mọi thứ chạy được, ghim vào một commit cụ thể.

## Chưa làm trong đợt này

Hạ tầng AWS, character LoRA, phân tích video tham khảo, fine-tune model dựng, cảnh image-to-video (T4 không chạy được loại model này).

## Cần người dùng xác nhận

- Điều khoản của Irasutoya về việc dùng tranh để train chưa có câu trả lời rõ.
- Chính sách "inauthentic content" của YouTube và điều khoản sử dụng của Kaggle cho mục đích này chưa được đối chiếu với nguồn chính thức.
