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
EMBEDS = "/kaggle/temp/embeds.pt"     # ngoài /kaggle/working để không bị tải về (khoảng 8MB mỗi prompt)


def find_input(name):
    found = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not found:
        sys.exit(f"Không tìm thấy {name} trong /kaggle/input")
    return found[0]


SPEC = json.load(open(find_input("jobs.json"), encoding="utf-8"))
S, JOBS = SPEC["settings"], SPEC["jobs"]


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def encode():
    pipe = Flux2KleinPipeline.from_pretrained(S["model"], transformer=None, vae=None, torch_dtype=torch.bfloat16)
    pipe.text_encoder.to("cuda")
    with torch.no_grad():
        embeds = {j["name"]: pipe.encode_prompt(prompt=j["prompt"], device="cuda")[0].cpu() for j in JOBS}
    os.makedirs(os.path.dirname(EMBEDS), exist_ok=True)
    torch.save(embeds, EMBEDS)
    log(f"Đã mã hóa {len(embeds)} prompt")


def wait_for(path, timeout=None):
    """Chờ ảnh do worker khác sinh ra. Trả về False nếu ảnh đó hỏng hoặc quá hạn."""
    start, timeout = time.time(), timeout or S.get("ref_wait", 900)
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
    log(f"GPU {gpu} bắt đầu: {job['name']}")
    try:
        refs = [load_ref(r) for r in job.get("refs", [])]
        if refs:
            log(f"GPU {gpu} có ảnh tham chiếu cho {job['name']} sau {time.time() - start:.0f}s")
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
                      lora=S["lora_file"] if lora_scale(job) else None, lora_scale=lora_scale(job),
                      model=S["model"], seconds=round(time.time() - start), gpu=gpu)
        json.dump(record, open(f"{OUT}/{job['name']}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        log(f"GPU {gpu} xong: {job['name']} ({record['seconds']}s)")
    except Exception as error:
        open(target + ".failed", "w").write(repr(error))
        log(f"GPU {gpu} LỖI ở {job['name']}: {error!r}")


def worker(index, count):
    os.makedirs(OUT, exist_ok=True)
    mine = [job for k, job in enumerate(JOBS) if k % count == index]
    pipe = Flux2KleinPipeline.from_pretrained(S["model"], text_encoder=None, tokenizer=None, torch_dtype=torch.bfloat16)
    pipe.to("cuda")
    embeds = torch.load(EMBEDS)
    log(f"GPU {index} nạp model xong, {len(mine)} job")
    # "lora": true = cường độ 1, false = không LoRA, số = cường độ (vd 0.5 cho nền phẳng).
    # Chạy theo cường độ giảm dần: ảnh nhân vật trước, rồi hạ cường độ, cuối cùng tháo LoRA để sinh nền.
    pipe.load_lora_weights(find_input(S["lora_file"]), adapter_name="style")
    for scale in sorted({lora_scale(j) for j in mine}, reverse=True):
        if scale:
            pipe.set_adapters(["style"], adapter_weights=[scale])
        else:
            pipe.unload_lora_weights()
        for job in mine:
            if lora_scale(job) == scale:
                run_job(pipe, embeds, job, index)


def lora_scale(job):
    value = job.get("lora", True)
    return 1.0 if value is True else float(value or 0)


if __name__ == "__main__":
    if sys.argv[1] == "encode":
        encode()
    else:
        worker(int(sys.argv[2]), int(sys.argv[3]))
