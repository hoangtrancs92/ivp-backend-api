"""Chạy Ở MÁY LOCAL. Gửi một lô sinh ảnh lên Kaggle rồi tải kết quả về.

Dùng:   python tools/run_kaggle.py videos/001 [--dry-run]
Vào:    videos/001/jobs.json  (xem examples/jobs.example.json)
        config/refs/*.png     (ảnh chuẩn; trong jobs.json ghi là "ref__<tên file>")
Ra:     videos/001/generated/out/<name>.png và <name>.json (nguồn gốc từng ảnh)

Cần lệnh `kaggle` (pip install kaggle) và file config.toml ở thư mục gốc dự án.
--dry-run chỉ dựng thư mục gửi đi và in các lệnh, không gọi Kaggle.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "config" / "refs"


def validate(jobs):
    """Tên không trùng; tham chiếu '@x' phải trỏ tới một job đứng trước và job đó không có '@'."""
    seen = {}
    for job in jobs:
        name = job["name"]
        if name in seen:
            sys.exit(f"jobs.json: trùng tên {name}")
        for ref in job.get("refs", []):
            if ref.startswith("@"):
                base = ref[1:]
                if base not in seen:
                    sys.exit(f"jobs.json: {name} tham chiếu {ref} nhưng job đó không đứng trước nó")
                if any(r.startswith("@") for r in seen[base].get("refs", [])):
                    sys.exit(f"jobs.json: {name} tham chiếu {ref}, mà {base} lại là một biến thể")
            elif not (REFS / ref.removeprefix("ref__")).exists():
                sys.exit(f"jobs.json: {name} cần ảnh chuẩn {ref} nhưng không có trong {REFS}")
        seen[name] = job


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry = "--dry-run" in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    video = Path(args[0]).resolve()
    config = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
    kg, gen = config["kaggle"], config["generation"]
    user = kg["username"]
    env = dict(os.environ, KAGGLE_USERNAME=user, KAGGLE_KEY=kg["key"])

    def kaggle(*cmd, check=True):
        print("$ kaggle", *cmd, flush=True)
        if dry:
            return ""
        result = subprocess.run(["kaggle", *map(str, cmd)], env=env, capture_output=True, text=True)
        if check and result.returncode != 0:
            sys.exit(result.stdout + result.stderr)
        return result.stdout + result.stderr

    spec = json.loads((video / "jobs.json").read_text(encoding="utf-8"))
    validate(spec["jobs"])
    spec["settings"] = gen                      # cấu hình sinh ảnh đi theo job; không có khóa nào

    # 1. Dataset job: jobs.json + worker.py + ảnh chuẩn, để phẳng một thư mục
    data = ROOT / "build" / "kaggle_data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    (data / "jobs.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(ROOT / "kaggle_job" / "worker.py", data)
    for ref in {r for j in spec["jobs"] for r in j.get("refs", []) if not r.startswith("@")}:
        shutil.copy(REFS / ref.removeprefix("ref__"), data / ref)
    (data / "dataset-metadata.json").write_text(json.dumps(
        {"title": kg["job_dataset"], "id": f"{user}/{kg['job_dataset']}", "licenses": [{"name": "CC0-1.0"}]}))

    exists = dry or "ready" in kaggle("datasets", "status", f"{user}/{kg['job_dataset']}", check=False)
    if exists:
        kaggle("datasets", "version", "-p", data, "-m", f"job {video.name}")
    else:
        kaggle("datasets", "create", "-p", data)
    while not dry and "ready" not in kaggle("datasets", "status", f"{user}/{kg['job_dataset']}", check=False):
        time.sleep(10)                          # chờ Kaggle xử lý xong phiên bản mới

    # 2. Kernel
    kernel = ROOT / "build" / "kaggle_kernel"
    shutil.rmtree(kernel, ignore_errors=True)
    kernel.mkdir(parents=True)
    shutil.copy(ROOT / "kaggle_job" / "kernel_main.py", kernel)
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{kg['kernel']}", "title": kg["kernel"], "code_file": "kernel_main.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [f"{user}/{kg['lora_dataset']}", f"{user}/{kg['job_dataset']}"],
        "competition_sources": [], "kernel_sources": []}, indent=1))
    kaggle("kernels", "push", "-p", kernel)

    # 3. Chờ và tải về
    while not dry:
        status = kaggle("kernels", "status", f"{user}/{kg['kernel']}", check=False).lower()
        print(time.strftime("%H:%M:%S"), status.strip(), flush=True)
        if "complete" in status:
            break
        if "error" in status or "cancel" in status:
            sys.exit("Kernel thất bại; xem log trên trang Kaggle của kernel.")
        time.sleep(kg.get("poll_seconds", 60))
    out = video / "generated"
    out.mkdir(exist_ok=True)
    kaggle("kernels", "output", f"{user}/{kg['kernel']}", "-p", out)
    if not dry:
        done = len(list(out.rglob("*.png")))
        failed = [p.name for p in out.rglob("*.failed")]
        print(f"Đã tải {done}/{len(spec['jobs'])} ảnh về {out}. Lỗi: {failed or 'không'}")


if __name__ == "__main__":
    main()
