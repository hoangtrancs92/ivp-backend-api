"""Sinh ảnh mẫu cho từng checkpoint LoRA để chọn mốc. Chạy trên Kaggle, trong phiên KHÔNG train
(RAM đã dùng khoảng 26/30GB khi train):

  /kaggle/temp/venv/bin/python /kaggle/working/sample_checkpoints.py

Mỗi checkpoint dùng cùng bộ prompt và cùng seed, cộng một hàng "no_lora" để so với model gốc.
Ảnh đã sinh thì bỏ qua, nên phiên bị ngắt chỉ cần chạy lại. Kết quả:
  /kaggle/working/samples/<checkpoint>_p<số>.png
  /kaggle/working/samples/sheet.jpg     bảng so sánh: mỗi hàng một checkpoint, mỗi cột một prompt
"""
import glob
import os
import sys

import torch
from PIL import Image, ImageDraw

try:
    from diffusers import Flux2KleinPipeline
except ImportError:
    sys.exit("Bản diffusers trong venv chưa có Flux2KleinPipeline. Cài bản mới:\n"
             "  uv pip install --python /kaggle/temp/venv/bin/python -U git+https://github.com/huggingface/diffusers\n"
             "(muốn train tiếp sau đó thì cài lại requirements.txt của AI Toolkit)")

CKPT_DIR = os.environ.get("CKPT_DIR", "/kaggle/working/output/irasutoya_style_v1")
OUT = os.environ.get("SAMPLES_DIR", "/kaggle/working/samples")
SIZE = (768, 1024)
SEED = 42
PROMPTS = [
    # có trong dataset
    "irasutoya_style, a firefighter holding a hose, serious face, full body, white background",
    "irasutoya_style, an old woman watering flowers, smiling face, full body, white background",
    # không có trong dataset: kiểm tra LoRA có còn theo prompt không
    "irasutoya_style, an astronaut eating ramen, happy face, full body, white background",
    "irasutoya_style, a cat driving a car, surprised face, white background",
    # nhân vật của video đầu tiên
    "irasutoya_style, japanese man in his late fifties, short grey hair, black glasses, brown cardigan over white shirt, "
    "grey trousers, sitting cross-legged, small smile face, full body, white background",
    "irasutoya_style, an empty glass beer mug covered in white frost, single object, no people, white background",
]


def main():
    os.makedirs(OUT, exist_ok=True)
    ckpts = sorted(glob.glob(f"{CKPT_DIR}/*.safetensors"))
    print(f"{len(ckpts)} checkpoint trong {CKPT_DIR}")
    rows = [("no_lora", None)] + [(os.path.basename(c).removesuffix(".safetensors"), c) for c in ckpts]

    pipe = Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-4B", torch_dtype=torch.bfloat16)
    pipe.enable_model_cpu_offload()             # chỉ đưa lên GPU phần đang dùng
    for name, ckpt in rows:
        todo = [i for i in range(len(PROMPTS)) if not os.path.exists(f"{OUT}/{name}_p{i}.png")]
        if not todo:
            continue
        if ckpt:
            pipe.load_lora_weights(ckpt, adapter_name="style")
        for i in todo:
            image = pipe(prompt=PROMPTS[i], width=SIZE[0], height=SIZE[1], num_inference_steps=4,
                         guidance_scale=1.0, generator=torch.Generator("cpu").manual_seed(SEED)).images[0]
            image.save(f"{OUT}/{name}_p{i}.png")
            print(f"{name}_p{i}.png")
        if ckpt:
            pipe.unload_lora_weights()

    # bảng so sánh
    cell_w, cell_h, label = 256, 341, 40
    sheet = Image.new("RGB", (cell_w * len(PROMPTS), (cell_h + label) * len(rows)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, (name, _) in enumerate(rows):
        y = r * (cell_h + label)
        draw.text((8, y + 10), name, fill="black")
        for i in range(len(PROMPTS)):
            path = f"{OUT}/{name}_p{i}.png"
            if os.path.exists(path):
                sheet.paste(Image.open(path).resize((cell_w, cell_h)), (i * cell_w, y + label))
    sheet.save(f"{OUT}/sheet.jpg", quality=85)
    print(f"Bảng so sánh: {OUT}/sheet.jpg")


if __name__ == "__main__":
    main()
