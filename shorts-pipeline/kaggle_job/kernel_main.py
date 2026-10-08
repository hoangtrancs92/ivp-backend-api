"""File mã của kernel Kaggle. Cài thư viện, rồi chạy worker.py (nằm trong dataset job)
trên mọi GPU có sẵn. Không chứa khóa bí mật nào."""
import glob, json, os, subprocess, sys, time


def log(message):
    print(time.strftime("%H:%M:%S"), message, flush=True)


# Mỗi lô có mã riêng (tools/run_kaggle.py thay __BATCH__ khi gửi). Kaggle đôi khi gắn phiên bản CŨ của dataset job
# (phiên bản mới chưa xử lý xong): khi đó dừng ngay, không vẽ lại cả lô cũ (video 014: gửi 3 ảnh, kernel vẽ 97 ảnh).
EXPECTED = "__BATCH__"
jobs_file = glob.glob("/kaggle/input/**/jobs.json", recursive=True)
found = json.load(open(jobs_file[0], encoding="utf-8")).get("batch") if jobs_file else None
if EXPECTED != "__" + "BATCH__" and found != EXPECTED:
    log(f"STALE_BATCH SAI LÔ: dataset job là lô {found}, cần lô {EXPECTED}. Dừng, máy sẽ gửi lại.")
    sys.exit(0)

log("Cài thư viện")

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "git+https://github.com/huggingface/diffusers", "transformers", "accelerate", "sentencepiece"],
               check=True)

worker = glob.glob("/kaggle/input/**/worker.py", recursive=True)[0]
gpus = int(subprocess.run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.count("\n")) or 1
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
token = glob.glob("/kaggle/input/**/hf_token", recursive=True)
if token:                                       # tải model từ Hugging Face có đăng nhập: nhanh hơn, ít bị giới hạn
    env["HF_TOKEN"] = open(token[0]).read().strip()
log(f"Token Hugging Face: {'có' if token else 'không'}")
log(f"Số GPU: {gpus}")

log("Mã hóa prompt")
subprocess.run([sys.executable, worker, "encode"], check=True, env=dict(env, CUDA_VISIBLE_DEVICES="0"))
log("Sinh ảnh")
procs = [subprocess.Popen([sys.executable, worker, "worker", str(i), str(gpus)],
                          env=dict(env, CUDA_VISIBLE_DEVICES=str(i))) for i in range(gpus)]
codes = [p.wait() for p in procs]

done = len(glob.glob("/kaggle/working/out/*.png"))
failed = len(glob.glob("/kaggle/working/out/*.failed"))
log(f"Xong: {done} ảnh, {failed} lỗi, mã thoát của worker: {codes}")
