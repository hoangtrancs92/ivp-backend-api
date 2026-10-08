"""Chạy TRÊN Kaggle. Sinh ảnh theo jobs.json bằng FLUX.2 klein 4B + style LoRA.

Được kernel_main.py gọi theo ba chế độ:
  python worker.py encode            mã hóa mọi prompt một lần, lưu embeds.pt
  python worker.py worker <i> <n>    worker thứ i trong n worker, mỗi worker một GPU
Tách hai giai đoạn để bộ mã hóa văn bản không nằm cùng lúc với bộ sinh ảnh
(hai tiến trình nạp cả pipeline sẽ vượt 30GB RAM của Kaggle).
"""
import sys
sys.modules["torchao"] = None      # torchao cài sẵn trên Kaggle lệch phiên bản với diffusers mới

import glob, json, os, time
import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

OUT = "/kaggle/working/out"
EMBEDS = "/kaggle/working/embeds.pt"


def find_input(name):
    found = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not found:
        sys.exit(f"Không tìm thấy {name} trong /kaggle/input")
    return found[0]


SPEC = json.load(open(find_input("jobs.json"), encoding="utf-8"))
S, JOBS = SPEC["settings"], SPEC["jobs"]


def encode():
    pipe = Flux2KleinPipeline.from_pretrained(S["model"], transformer=None, vae=None, torch_dtype=torch.bfloat16)
    pipe.text_encoder.to("cuda")
    with torch.no_grad():
        embeds = {j["name"]: pipe.encode_prompt(prompt=j["prompt"], device="cuda")[0].cpu() for j in JOBS}
    torch.save(embeds, EMBEDS)
    print(f"Đã mã hóa {len(embeds)} prompt", flush=True)


def wait_for(path, timeout=3600):
    """Chờ ảnh do worker khác sinh ra. Trả về False nếu ảnh đó hỏng hoặc quá hạn."""
    start = time.time()
    while not os.path.exists(path):
        if os.path.exists(path + ".failed") or time.time() - start > timeout:
            return False
        time.sleep(2)
    time.sleep(1)
    return True


def load_ref(ref):
    """'@ten_job' là ảnh sinh trong lần chạy này; còn lại là file trong dataset đầu vào."""
    if ref.startswith("@"):
        path = f"{OUT}/{ref[1:]}.png"
        if not wait_for(path):
            raise RuntimeError(f"ảnh tham chiếu {ref} không có")
    else:
        path = find_input(ref)
    image = Image.open(path).convert("RGB")
    image.thumbnail((S["ref_size"], S["ref_size"]))      # T4: tham chiếu lớn hơn sẽ hết VRAM
    return image


def run_job(pipe, embeds, job, gpu):
    target = f"{OUT}/{job['name']}.png"
    if os.path.exists(target):
        return
    start = time.time()
    try:
        refs = [load_ref(r) for r in job.get("refs", [])]
        side = S["size_ref"] if refs else S["size_text"]
        seed = job.get("seed", S["seed"])
        kwargs = dict(prompt_embeds=embeds[job["name"]].to("cuda"),
                      width=job.get("width", side), height=job.get("height", side),
                      num_inference_steps=S["steps"], guidance_scale=1.0,
                      generator=torch.Generator("cpu").manual_seed(seed))
        if refs:
            kwargs["image"] = refs
        pipe(**kwargs).images[0].save(target)
        record = dict(job, seed=seed, width=kwargs["width"], height=kwargs["height"],
                      lora=S["lora_file"] if job.get("lora", True) else None,
                      model=S["model"], seconds=round(time.time() - start), gpu=gpu)
        json.dump(record, open(f"{OUT}/{job['name']}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"GPU {gpu} xong: {job['name']} ({record['seconds']}s)", flush=True)
    except Exception as error:
        open(target + ".failed", "w").write(repr(error))
        print(f"GPU {gpu} LỖI ở {job['name']}: {error!r}", flush=True)


def worker(index, count):
    os.makedirs(OUT, exist_ok=True)
    mine = [job for k, job in enumerate(JOBS) if k % count == index]
    pipe = Flux2KleinPipeline.from_pretrained(S["model"], text_encoder=None, tokenizer=None, torch_dtype=torch.bfloat16)
    pipe.to("cuda")
    embeds = torch.load(EMBEDS)
    # Ảnh nhân vật (có LoRA) trước, rồi tháo LoRA để sinh nền
    pipe.load_lora_weights(find_input(S["lora_file"]))
    for job in mine:
        if job.get("lora", True):
            run_job(pipe, embeds, job, index)
    pipe.unload_lora_weights()
    for job in mine:
        if not job.get("lora", True):
            run_job(pipe, embeds, job, index)


if __name__ == "__main__":
    if sys.argv[1] == "encode":
        encode()
    else:
        worker(int(sys.argv[2]), int(sys.argv[3]))
