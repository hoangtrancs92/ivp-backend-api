"""Chạy TRÊN Kaggle, sau giai đoạn sinh ảnh (kernel_main.py gọi). Sinh clip image-to-video bằng Wan2.2 TI2V-5B Turbo
(GGUF) qua ComfyUI headless: mỗi GPU một server ComfyUI, script gửi job qua HTTP API.

Vào:  jobs.json, mục "clips" (tools/make_jobs.py tạo) và "i2v" (mục [i2v] của config/settings.toml)
        {"name": "clip_003", "image": "@full_003" | "full__003.png", "prompt": "...", "frames": 97, "seed": 30}
      "@x" là ảnh vừa sinh ở giai đoạn ảnh (/kaggle/working/out/x.png), còn lại là file trong dataset job.
Ra:   /kaggle/working/out/<name>.mp4 và /kaggle/working/out/clips_results.json (seed, điểm, thời gian, lỗi).
ComfyUI, model và frame PNG nằm ở /kaggle/temp để `kaggle kernels output` không tải về.
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

OUT = Path("/kaggle/working/out")
TEMP = Path("/kaggle/temp")
COMFY = TEMP / "ComfyUI"
RESULTS = OUT / "clips_results.json"
START = float(os.environ.get("KERNEL_START", time.time()))
lock = threading.Lock()


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


def find_input(name):
    found = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not found:
        raise FileNotFoundError(f"Không tìm thấy {name} trong /kaggle/input")
    return found[0]


SPEC = json.load(open(find_input("jobs.json"), encoding="utf-8"))
S, CLIPS = SPEC["i2v"], SPEC.get("clips", [])
TEMPLATE = json.load(open(find_input("wan5b_i2v.json"), encoding="utf-8"))


class OutOfMemory(Exception):
    pass


class ServerDead(Exception):
    pass


# ---------- cài đặt ----------

def sh(*cmd, cwd=None):
    subprocess.run([str(c) for c in cmd], check=True, cwd=cwd)


def clone(url, path, commit):
    if not path.exists():
        sh("git", "clone", "-q", url, path)
    if commit:                                  # pin commit để bản mới của repo không làm vỡ lần chạy sau
        sh("git", "checkout", "-q", commit, cwd=path)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True).stdout.strip()
    log(f"{path.name} ở commit {head}")


def install():
    clone("https://github.com/comfyanonymous/ComfyUI", COMFY, S.get("comfyui_commit"))
    gguf = COMFY / "custom_nodes" / "ComfyUI-GGUF"
    clone("https://github.com/city96/ComfyUI-GGUF", gguf, S.get("gguf_commit"))
    # không -U: giữ torch cài sẵn của Kaggle
    sh(sys.executable, "-m", "pip", "install", "-q", "-r", COMFY / "requirements.txt", "-r", gguf / "requirements.txt")
    if not shutil.which("ffmpeg"):
        sh(sys.executable, "-m", "pip", "install", "-q", "imageio-ffmpeg")


def ffmpeg_exe():
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def pick(repo, quant):
    """Tên file GGUF trong repo theo mức quant (vd Q8_0), không đoán tên file."""
    from huggingface_hub import list_repo_files
    files = [f for f in list_repo_files(repo) if f.endswith(".gguf") and quant.lower() in f.lower()]
    if not files:
        sys.exit(f"Repo {repo} không có file .gguf nào khớp {quant}")
    return min(files, key=len)


def fetch_model(repo, filename, folder):
    """Có sẵn trong dataset cache (vd wan5b-models) thì dùng luôn, không thì tải từ Hugging Face. Trả về tên file."""
    from huggingface_hub import hf_hub_download
    target = COMFY / "models" / folder / Path(filename).name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        cached = glob.glob(f"/kaggle/input/**/{target.name}", recursive=True)
        source = cached[0] if cached else hf_hub_download(repo, filename, cache_dir=str(TEMP / "hf"))
        target.symlink_to(source)
        log(f"Model {target.name}: {'dataset cache' if cached else 'tải từ ' + repo}")
    return target.name


def models():
    names = {"unet": fetch_model(S["unet_repo"], pick(S["unet_repo"], S["quant"]), "unet"),
             "clip": fetch_model(S["text_encoder_repo"], pick(S["text_encoder_repo"], S["text_encoder_quant"]),
                                 "text_encoders"),
             "vae": fetch_model(S["vae_repo"], S["vae_file"], "vae")}
    if S.get("upscale_url"):
        target = COMFY / "models" / "upscale_models" / Path(S["upscale_url"]).name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            urllib.request.urlretrieve(S["upscale_url"], target)
        names["upscale"] = target.name
    return names


# ---------- server ComfyUI ----------

class Server:
    def __init__(self, gpu):
        self.gpu, self.port, self.proc = gpu, 8188 + gpu, None
        self.outdir = TEMP / f"out{gpu}"
        self.url = f"http://127.0.0.1:{self.port}"

    def start(self):
        self.outdir.mkdir(parents=True, exist_ok=True)
        logfile = open(TEMP / f"comfy{self.gpu}.log", "a")
        self.proc = subprocess.Popen(
            [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", str(self.port),
             "--output-directory", str(self.outdir), "--disable-auto-launch"],
            cwd=COMFY, env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(self.gpu)), stdout=logfile, stderr=subprocess.STDOUT)
        for _ in range(300):
            if self.alive():
                break
            if self.proc.poll() is not None:
                sys.exit(f"ComfyUI GPU {self.gpu} thoát ngay khi khởi động, xem {logfile.name}:\n"
                         + Path(logfile.name).read_text()[-3000:])
            time.sleep(2)
        else:
            sys.exit(f"ComfyUI GPU {self.gpu} không lên sau 10 phút")
        # T4 không tính bf16/fp8: xem ComfyUI chọn dtype nào
        for line in Path(logfile.name).read_text(errors="replace").splitlines():
            if "dtype" in line.lower() or "vram" in line.lower() or "device" in line.lower():
                log(f"ComfyUI GPU {self.gpu}: {line.strip()}")
        log(f"ComfyUI GPU {self.gpu} sẵn sàng ở cổng {self.port}")

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(30)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def restart(self):
        log(f"ComfyUI GPU {self.gpu} không phản hồi: khởi động lại")
        self.stop()
        self.start()

    def alive(self):
        import requests
        try:
            return requests.get(self.url + "/system_stats", timeout=10).status_code == 200
        except requests.RequestException:
            return False

    def request(self, method, path, **kw):
        import requests
        try:
            return requests.request(method, self.url + path, timeout=60, **kw)
        except requests.RequestException as error:
            raise ServerDead(repr(error))


# ---------- một clip ----------

def by_title(workflow):
    return {node["_meta"]["title"]: (key, node) for key, node in workflow.items()}


def build_workflow(job, image_name, size, frames, seed, prefix, names):
    workflow = json.loads(json.dumps(TEMPLATE))
    nodes = by_title(workflow)
    nodes["MODEL"][1]["inputs"]["unet_name"] = names["unet"]
    nodes["TEXT_ENCODER"][1]["inputs"]["clip_name"] = names["clip"]
    nodes["VAE"][1]["inputs"]["vae_name"] = names["vae"]
    nodes["SHIFT"][1]["inputs"]["shift"] = S["shift"]
    nodes["IN_IMAGE"][1]["inputs"]["image"] = image_name
    nodes["IN_PROMPT"][1]["inputs"]["text"] = f"{job['prompt']}, {S['style_suffix']}"
    nodes["IN_LATENT"][1]["inputs"].update(width=size[0], height=size[1], length=frames)
    nodes["IN_SAMPLER"][1]["inputs"].update(seed=seed, steps=S["steps"], cfg=S["cfg"],
                                            sampler_name=S["sampler"], scheduler=S["scheduler"])
    out = nodes["OUT_FRAMES"][1]["inputs"]
    out["filename_prefix"] = prefix
    if "upscale" in names:
        nodes["UPSCALE_LOADER"][1]["inputs"]["model_name"] = names["upscale"]
    else:                                       # không upscale: lưu thẳng frame từ VAEDecode
        out["images"] = [nodes["DECODE"][0], 0]
        del workflow[nodes["UPSCALE"][0]], workflow[nodes["UPSCALE_LOADER"][0]]
    return workflow, nodes["OUT_FRAMES"][0]


def check_size(size, frames):
    if size[0] % 32 or size[1] % 32:
        raise ValueError(f"cỡ {size} phải là bội của 32")
    if (frames - 1) % 4 or not 5 <= frames <= S["max_frames"]:
        raise ValueError(f"số frame {frames} phải dạng 4k+1, tối đa {S['max_frames']}")


def source_image(job, size):
    from PIL import Image, ImageOps
    ref = job["image"]
    path = OUT / f"{ref[1:]}.png" if ref.startswith("@") else Path(find_input(ref))
    if not path.exists():
        raise FileNotFoundError(f"ảnh {ref} không có (giai đoạn ảnh lỗi?)")
    target = TEMP / "i2v_in" / f"{job['name']}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    # resize + crop đúng cỡ sinh trước khi upload để model không tự cắt
    ImageOps.fit(Image.open(path).convert("RGB"), size, Image.LANCZOS).save(target)
    return target


def render(server, job, size, frames, seed, names):
    """Sinh một clip. Trả về (đường dẫn mp4 tạm, số đo QA)."""
    check_size(size, frames)
    image = source_image(job, size)
    with open(image, "rb") as f:
        uploaded = server.request("POST", "/upload/image", files={"image": (image.name, f, "image/png")},
                                  data={"overwrite": "true"})
    if uploaded.status_code != 200:
        raise RuntimeError(f"upload ảnh lỗi: {uploaded.text[:500]}")
    prefix = f"{job['name']}_s{seed}"
    workflow, out_id = build_workflow(job, uploaded.json()["name"], size, frames, seed, prefix, names)
    sent = server.request("POST", "/prompt", json={"prompt": workflow})
    if sent.status_code != 200:
        raise RuntimeError(f"ComfyUI từ chối workflow: {sent.text[:1500]}")
    prompt_id = sent.json()["prompt_id"]
    deadline = time.time() + S["job_timeout"]
    while True:
        time.sleep(5)
        if not server.alive():
            raise ServerDead("không phản hồi /system_stats")
        entry = server.request("GET", f"/history/{prompt_id}").json().get(prompt_id)
        if entry and (entry.get("status", {}).get("completed") or entry.get("status", {}).get("status_str") == "error"):
            break
        if time.time() > deadline:
            server.request("POST", "/interrupt")
            raise TimeoutError(f"quá {S['job_timeout']} giây")
    status = entry.get("status", {})
    if status.get("status_str") == "error":
        text = json.dumps(status.get("messages", []), ensure_ascii=False)[-2000:]
        if "out of memory" in text.lower() or "outofmemory" in text.lower():
            raise OutOfMemory(text)
        raise RuntimeError(text)
    images = entry["outputs"][out_id]["images"]
    files = [server.outdir / i.get("subfolder", "") / i["filename"] for i in images]
    # đổi tên frame thành dãy số (không phụ thuộc mẫu tên của SaveImage), đo QA, ghép mp4, xóa frame cho khỏi đầy ổ
    seq = TEMP / "seq" / prefix
    shutil.rmtree(seq, ignore_errors=True)
    seq.mkdir(parents=True)
    for k, f in enumerate(files):
        shutil.move(str(f), seq / f"{k:05d}.png")
    try:
        return encode(seq, prefix), measure(seq)
    finally:
        shutil.rmtree(seq, ignore_errors=True)


def encode(seq, prefix):
    target = TEMP / "clips" / f"{prefix}.mp4"
    target.parent.mkdir(parents=True, exist_ok=True)
    scale = ["-vf", "scale={}:{}:flags=lanczos".format(*S["out_size"])] if S.get("out_size") else []
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-framerate", str(S["fps"]), "-i", str(seq / "%05d.png"),
                    *scale, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(target)], check=True)
    return target


def measure(seq):
    """QA thô bằng số: motion = chênh lệch trung bình giữa hai frame liền nhau (clip đứng yên ~0),
    drift = chênh lệch frame cuối so với frame đầu (cao = cảnh/nét vẽ trôi đi). Điểm 0-1, chỉ để so hai seed."""
    import numpy as np
    from PIL import Image
    frames = sorted(seq.glob("*.png"))
    grey = [np.asarray(Image.open(f).convert("L").resize((128, 128)), dtype=np.float32) for f in frames[::2]]
    motion = float(np.mean([np.abs(a - b).mean() for a, b in zip(grey, grey[1:])])) if len(grey) > 1 else 0.0
    drift = float(np.abs(grey[-1] - grey[0]).mean()) if grey else 0.0
    score = min(motion / S["qa_motion_good"], 1.0) - max(0.0, drift - S["qa_drift_max"]) / S["qa_drift_max"]
    return {"score": round(score, 3), "motion": round(motion, 2), "drift": round(drift, 2), "frames": len(frames)}


def shorter(frames):
    """Còn khoảng 3/4, vẫn dạng 4k+1."""
    return max(((frames - 1) * 3 // 4) // 4 * 4 + 1, 5)


# ---------- điều phối ----------

def load_results():
    try:
        return json.loads(RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


RESULT = load_results()


def save(name, record):
    with lock:
        RESULT[name] = record
        RESULTS.write_text(json.dumps(RESULT, ensure_ascii=False, indent=1), encoding="utf-8")


def process(server, job, names):
    size = (job.get("width", S["width"]), job.get("height", S["height"]))
    frames = min(job.get("frames", S["fps"] * S["seconds"] + 1), S["max_frames"])
    tries, best = [], None
    log(f"GPU {server.gpu} bắt đầu: {job['name']} ({size[0]}x{size[1]}, {frames} frame)")
    for k in range(S["seeds"]):
        seed = job.get("seed", 0) + 1000 * k
        for attempt in range(2):
            start = time.time()
            try:
                mp4, qa = render(server, job, size, frames, seed, names)
            except OutOfMemory as error:
                tries.append({"seed": seed, "frames": frames, "error": "oom", "detail": str(error)[-300:]})
                if attempt == 0:
                    frames = shorter(frames)
                    log(f"GPU {server.gpu} hết VRAM ở {job['name']}: thử lại với {frames} frame")
                    continue
                save(job["name"], {"status": "failed_oom", "tries": tries, "gpu": server.gpu})
                log(f"GPU {server.gpu} LỖI ở {job['name']}: failed_oom")
                return
            except ServerDead as error:
                tries.append({"seed": seed, "frames": frames, "error": "server_dead", "detail": str(error)})
                server.restart()
                if attempt == 0:
                    continue
                break
            except Exception as error:
                tries.append({"seed": seed, "frames": frames, "error": repr(error)[-1500:]})
                break
            record = {"seed": seed, "frames": frames, "size": list(size), "seconds": round(time.time() - start), **qa}
            tries.append(record)
            log(f"GPU {server.gpu} {job['name']} seed {seed}: {record['seconds']}s, điểm {qa['score']} "
                f"(motion {qa['motion']}, drift {qa['drift']})")
            if best is None or qa["score"] > best[1]["score"]:
                best = (mp4, record)
            break
    if best is None:
        save(job["name"], {"status": "failed", "tries": tries, "gpu": server.gpu})
        log(f"GPU {server.gpu} LỖI ở {job['name']}: {tries[-1].get('error') if tries else '?'}")
        return
    shutil.move(str(best[0]), OUT / f"{job['name']}.mp4")
    save(job["name"], {"status": "done", **best[1], "tries": tries, "gpu": server.gpu})
    log(f"GPU {server.gpu} xong: {job['name']} (seed {best[1]['seed']})")


def out_of_time():
    return time.time() - START > (S["session_minutes"] - 30) * 60   # còn dưới 30 phút: ngừng nhận job mới


def work(server, queue, names, first_done=None):
    while queue:
        if out_of_time():
            for job in queue:
                save(job["name"], {"status": "skipped_time"})
            log(f"GPU {server.gpu}: sắp hết giờ phiên Kaggle, bỏ {len(queue)} clip còn lại")
            break
        process(server, queue.pop(0), names)
        if first_done:
            first_done.set()
    if first_done:
        first_done.set()


def peaks(state, stop):
    """Đo VRAM đỉnh từng GPU và RAM hệ thống đỉnh (số cho benchmark)."""
    while not stop.is_set():
        try:
            used = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True).stdout.split()
            for i, mb in enumerate(used):
                state[f"vram_gpu{i}_mb"] = max(state.get(f"vram_gpu{i}_mb", 0), int(mb))
            info = dict(line.split(":", 1) for line in open("/proc/meminfo"))
            ram = (int(info["MemTotal"].split()[0]) - int(info["MemAvailable"].split()[0])) // 1024
            state["ram_mb"] = max(state.get("ram_mb", 0), ram)
        except (OSError, ValueError, KeyError):
            pass
        stop.wait(2)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [j for j in CLIPS if not (RESULT.get(j["name"], {}).get("status") == "done" and (OUT / f"{j['name']}.mp4").exists())]
    if not todo:
        log("Không có clip nào cần sinh")
        return
    log(f"Clip: {len(todo)} job")
    start = time.time()
    install()
    names = models()
    log(f"Cài ComfyUI và tải model: {time.time() - start:.0f}s")
    gpus = int(subprocess.run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                              capture_output=True, text=True).stdout.count("\n")) or 1
    gpus = min(gpus, S.get("gpus") or gpus)    # benchmark: "gpus": 1 để đo trên một GPU
    queues = [todo[i::gpus] for i in range(gpus)]
    servers = [Server(i) for i in range(gpus) if queues[i]]
    state, stop = {}, threading.Event()
    threading.Thread(target=peaks, args=(state, stop), daemon=True).start()
    first_done = threading.Event()

    def later(server, queue):
        # server thứ hai chỉ khởi động khi server đầu đã nạp model và chạy xong một job: hai server cùng nạp dễ vượt RAM
        first_done.wait()
        server.start()
        work(server, queue, names)

    servers[0].start()
    threads = [threading.Thread(target=work, args=(servers[0], queues[0], names, first_done))]
    threads += [threading.Thread(target=later, args=(s, queues[s.gpu])) for s in servers[1:]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    stop.set()
    for s in servers:
        s.stop()
    save("_peaks", state)
    done = sum(1 for k, r in RESULT.items() if not k.startswith("_") and r.get("status") == "done")
    log(f"Xong clip: {done}/{len(CLIPS)}, đỉnh: {state}")


if __name__ == "__main__":
    main()
