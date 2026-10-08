"""File mã của kernel Kaggle. Cài thư viện, rồi chạy worker.py (nằm trong dataset job)
trên mọi GPU có sẵn. Không chứa khóa bí mật nào."""
import glob, os, subprocess, sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-U",
                "git+https://github.com/huggingface/diffusers", "transformers", "accelerate", "sentencepiece"],
               check=True)

worker = glob.glob("/kaggle/input/**/worker.py", recursive=True)[0]
gpus = int(subprocess.run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader"],
                          capture_output=True, text=True).stdout.count("\n")) or 1
env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
print(f"Số GPU: {gpus}", flush=True)

subprocess.run([sys.executable, worker, "encode"], check=True, env=dict(env, CUDA_VISIBLE_DEVICES="0"))
procs = [subprocess.Popen([sys.executable, worker, "worker", str(i), str(gpus)],
                          env=dict(env, CUDA_VISIBLE_DEVICES=str(i))) for i in range(gpus)]
codes = [p.wait() for p in procs]

done = len(glob.glob("/kaggle/working/out/*.png"))
failed = len(glob.glob("/kaggle/working/out/*.failed"))
print(f"Xong: {done} ảnh, {failed} lỗi, mã thoát của worker: {codes}")
