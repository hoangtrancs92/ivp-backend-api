# Chạy trên Kaggle

Việc cần GPU (train, ảnh mẫu, bước 2 và 3) chạy trên Kaggle. Không chạy hai việc cùng lúc trong một phiên.

Notebook cần: Internet bật, Accelerator **GPU T4 x2**, Persistence **Files only** (để `/kaggle/working` còn lại giữa các phiên).

## Ô chung (chạy đầu mỗi phiên)

```
# 1. kiểm tra máy: cần thấy Tesla T4 và khoảng 30GB RAM
!nvidia-smi --query-gpu=name,memory.total --format=csv
!free -g | head -2
```

```
# 2. cài AI Toolkit và môi trường Python 3.12 (bỏ qua nếu /kaggle/temp/venv còn)
%cd /kaggle/temp
!git clone --depth 1 https://github.com/ostris/ai-toolkit
%cd /kaggle/temp/ai-toolkit
!pip install -q uv
!uv venv --clear --python 3.12 /kaggle/temp/venv
!uv pip install --python /kaggle/temp/venv/bin/python --index-url https://download.pytorch.org/whl/cu130 torch==2.13.0 torchvision==0.28.0 torchaudio==2.11.0
!uv pip install --python /kaggle/temp/venv/bin/python -r requirements.txt
```

```
# 3. chỗ lưu model tải về
import os
os.environ["HF_HOME"] = "/kaggle/temp/hf"
```

## Train

```
# chép dataset; xóa thư mục đích trước để không bị nhân đôi ảnh
!rm -rf /kaggle/temp/dataset/irasutoya_style && mkdir -p /kaggle/temp/dataset /kaggle/working/output
!cp -r /kaggle/input/datasets/tranhoang1124/irasutoya-style /kaggle/temp/dataset/irasutoya_style
!ls /kaggle/temp/dataset/irasutoya_style | wc -l      # phải là 178 (89 ảnh + 89 caption)
```

Tải `style_kaggle.yaml` lên `/kaggle/working/` (hoặc dán vào ô bắt đầu bằng `%%writefile /kaggle/working/style_kaggle.yaml`), rồi:

```
%cd /kaggle/temp/ai-toolkit
!/kaggle/temp/venv/bin/python run.py /kaggle/working/style_kaggle.yaml
```

Chạy lại cùng cấu hình thì trainer tiếp tục từ checkpoint mới nhất trong `/kaggle/working/output/irasutoya_style_v1/`.

## Chọn checkpoint (phiên mới, sau khi train xong hoặc dừng)

Tải `sample_checkpoints.py` lên `/kaggle/working/`, rồi:

```
!/kaggle/temp/venv/bin/python -c "from diffusers import Flux2KleinPipeline" || uv pip install --python /kaggle/temp/venv/bin/python -U git+https://github.com/huggingface/diffusers
!/kaggle/temp/venv/bin/python /kaggle/working/sample_checkpoints.py
```

Mở `/kaggle/working/samples/sheet.jpg`. Chọn mốc **sớm nhất** đã ra đúng nét mà vẫn theo đúng prompt
(phi hành gia vẫn là phi hành gia, con mèo vẫn lái xe). Dấu hiệu train quá tay: prompt khác nhau ra cùng một
nhân vật, hoặc ảnh giống hệt ảnh trong dataset. Tải file `.safetensors` đã chọn về, đổi tên thành
`shorts-pipeline/loras/style.safetensors`.

Lưu ý: nâng diffusers để sinh ảnh có thể làm AI Toolkit lỗi; muốn train tiếp thì chạy lại
`uv pip install ... -r requirements.txt` ở ô 2.

## Sinh nền, nhân vật, đạo cụ cho một video (bước 2 và 3)

Nén `shorts-pipeline/` (chỉ cần `config/`, `loras/`, `steps/`, `library/`, `videos/<tên>/script.json`)
và tải lên thành một Kaggle Dataset, ví dụ `shorts-pipeline`. Rồi:

```
!rm -rf /kaggle/working/sp && cp -r /kaggle/input/shorts-pipeline /kaggle/working/sp
%cd /kaggle/working/sp
!/kaggle/temp/venv/bin/python steps/02_backgrounds.py videos/001-futatsu-no-jokki
!/kaggle/temp/venv/bin/python steps/03_characters.py videos/001-futatsu-no-jokki
```

Tải `videos/<tên>/backgrounds/`, `characters/`, `props_raw/` về máy, chép vào thư mục video, rồi chạy
`python run_local.py videos/<tên>` ở máy local. Có thể chạy `steps/04_cutouts.py` ngay trên Kaggle cho nhanh
(cần `pip install "rembg[gpu]"` trong venv).

Duyệt bằng Claude trên Kaggle (tùy chọn): thêm secret `ANTHROPIC_API_KEY`, `pip install anthropic`, rồi
`cd videos/<tên> && python ../../review.py images`, sau đó chạy lại `03_characters.py` để sinh bù ảnh bị loại.

## Chưa chạy thử

Toàn bộ các ô sinh ảnh ở trên chưa được chạy. Các điểm có thể phải sửa:
- bản diffusers nào có `Flux2KleinPipeline` và có đọc được file LoRA định dạng của AI Toolkit không;
- T4 không có lõi bf16 riêng; nếu chậm hoặc lỗi, thử `KLEIN_DTYPE=float16` (có thể ra ảnh đen vì tràn số);
- thời gian sinh mỗi ảnh trên T4 chưa đo.
