"""Chạy Ở MÁY LOCAL. Gửi một lô sinh ảnh lên Kaggle rồi tải kết quả về.

Dùng:   python tools/run_kaggle.py videos/001 [--dry-run]
        python tools/run_kaggle.py videos/001 --fetch     chỉ tải lại kết quả lần chạy gần nhất, không gửi
        python tools/run_kaggle.py <file LoRA .safetensors> --upload-lora    (một lần, tạo dataset lora_dataset)
Vào:    videos/001/jobs.json  (tạo bằng tools/make_jobs.py)
        config/refs/*.png     (ảnh chuẩn; trong jobs.json ghi là "ref__<tên file>")
Ra:     videos/001/work/kaggle/out/<name>.png và <name>.json (nguồn gốc từng ảnh), rồi chép theo tiền tố tên:
        bg_x -> library/backgrounds/x.png, ref_x -> config/refs/x_front.png,
        ch_x -> videos/001/characters/x.png  (ảnh đã có thì giữ)
        clip_x -> videos/001/clips/x.mp4 (mục "clips" của jobs.json, kaggle_job/i2v_runner.py; clip mới luôn ghi đè),
        kết quả từng clip (seed, điểm QA, lỗi) gộp vào videos/001/clips/results.json

Cần lệnh `kaggle` (pip install kaggle), config.toml (tài khoản) và config/settings.toml (mục [generation]).
--dry-run chỉ dựng thư mục gửi đi và in các lệnh, không gọi Kaggle.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "config" / "refs"
DEFAULTS = {"machine_shape": "NvidiaTeslaT4", "lora_dataset": "irasutoya-style-lora", "job_dataset": "shorts-job",
            "kernel": "shorts-gen", "poll_seconds": 60, "run_timeout_minutes": 90}


def lora_scale(job):
    value = job.get("lora", True)                # giống worker.py
    return 1.0 if value is True else float(value or 0)


def ref_source(video, ref):
    """File trên máy của một tham chiếu không phải '@': ref__x = ảnh chuẩn, char__x = ảnh gốc trong characters/,
    bg__x = ảnh nền library/backgrounds/x (tiểu phẩm: vẽ toàn cảnh có người trong đúng căn phòng của nền)."""
    if ref.startswith("char__"):
        filename = ref.removeprefix("char__")
        original = video / "characters" / filename
        return original if original.is_file() else video / "cutouts" / filename
    if ref.startswith("bg__"):
        return ROOT / "library" / "backgrounds" / ref.removeprefix("bg__")
    if ref.startswith("full__"):                # ảnh đầu của clip: tranh cả cảnh đã có
        return video / "full" / ref.removeprefix("full__")
    return REFS / ref.removeprefix("ref__")


def validate(jobs, video):
    """Tên không trùng; tham chiếu '@x' phải trỏ tới một job đứng trước, cùng hoặc cao hơn cường độ LoRA.
    Mỗi worker chạy job theo đúng thứ tự trong jobs.json (nhóm theo cường độ LoRA giảm dần), nên job sớm nhất
    chưa xong luôn có mọi tham chiếu đã xong: các worker không thể chờ nhau mãi, kể cả chuỗi nhiều tầng
    (ảnh chuẩn -> ảnh cảnh -> tư thế thứ hai)."""
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
                if lora_scale(seen[base]) < lora_scale(job):
                    sys.exit(f"jobs.json: {name} tham chiếu {ref} có cường độ LoRA thấp hơn, sẽ bị sinh sau")
            elif not ref_source(video, ref).exists():
                sys.exit(f"jobs.json: {name} cần {ref} nhưng không có {ref_source(video, ref)}")
        seen[name] = job


def validate_clips(clips, jobs, video):
    names = {j["name"] for j in jobs}
    for clip in clips:
        image = clip["image"]
        if image.startswith("@") and image[1:] not in names:
            sys.exit(f"jobs.json: {clip['name']} cần ảnh {image} nhưng lô này không sinh ảnh đó")
        if not image.startswith("@") and not ref_source(video, image).exists():
            sys.exit(f"jobs.json: {clip['name']} cần {ref_source(video, image)}")


def main():
    args = [a for a in sys.argv[1:] if a not in ("--dry-run", "--upload-lora", "--fetch")]
    dry = "--dry-run" in sys.argv
    upload_lora = "--upload-lora" in sys.argv     # khi đó tham số là đường dẫn file .safetensors
    if len(args) != 1:
        sys.exit(__doc__)
    video = Path(args[0]).resolve()
    path = ROOT / "config.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    kg = {**DEFAULTS, **config.get("kaggle", {})}
    hf_token = config.get("keys", {}).get("hf_token", "")
    # web/app.py chạy lệnh này thay từng người dùng: tài khoản lấy từ biến môi trường, đè lên config.toml
    if os.environ.get("SHORTS_KAGGLE_USERNAME"):
        kg.update(username=os.environ["SHORTS_KAGGLE_USERNAME"], key=os.environ.get("SHORTS_KAGGLE_KEY", ""))
        hf_token = os.environ.get("SHORTS_HF_TOKEN", "")
    settings = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))
    gen = settings["generation"]
    user = kg["username"]
    env = dict(os.environ)
    key = kg.get("key", "")
    if key.startswith("KGAT_"):                 # token mới ở kaggle.com/settings/api
        env["KAGGLE_API_TOKEN"] = key
    elif key:                                   # khóa kiểu cũ trong kaggle.json
        env.update(KAGGLE_USERNAME=user, KAGGLE_KEY=key)
    # để trống: dùng phiên đăng nhập đã lưu bởi `kaggle auth login`

    def kaggle(*cmd, check=True):
        print("$ kaggle", *cmd, flush=True)
        if dry:
            return ""
        result = subprocess.run(["kaggle", *map(str, cmd)], env=dict(env, PYTHONUTF8="1"), capture_output=True,
                                text=True, encoding="utf-8", errors="replace")
        if check and result.returncode != 0:
            sys.exit(result.stdout + result.stderr)
        return result.stdout + result.stderr

    kaggle.env = dict(env, PYTHONUTF8="1")      # report() đọc log trực tiếp bằng đúng tài khoản này

    def send_lora(source):                      # đưa file LoRA lên thành dataset riêng tư của tài khoản này
        lora = ROOT / "build" / user / "lora_data"
        shutil.rmtree(lora, ignore_errors=True)
        lora.mkdir(parents=True)
        shutil.copy(source, lora / gen["lora_file"])
        (lora / "dataset-metadata.json").write_text(json.dumps(
            {"title": kg["lora_dataset"], "id": f"{user}/{kg['lora_dataset']}", "licenses": [{"name": "CC0-1.0"}]}))
        print(kaggle("datasets", "create", "-p", lora))

    if upload_lora:                             # làm một lần (nút "Đưa LoRA lên Kaggle")
        return send_lora(video)

    if "--fetch" in sys.argv:                   # chỉ tải lại kết quả lần chạy gần nhất, không gửi gì
        return fetch(video, kaggle, f"{user}/{kg['kernel']}", dry)

    # tài khoản Kaggle mới chưa có dataset LoRA: tự đưa lên (lần đầu ~vài phút), không thì kernel chạy không có LoRA
    lora_id = f"{user}/{kg['lora_dataset']}"
    if not dry and "ready" not in kaggle("datasets", "status", lora_id, check=False):
        local = ROOT / "loras" / "style.safetensors"
        if not local.exists():
            sys.exit(f"Tài khoản {user} chưa có dataset {lora_id} và máy không có {local} để đưa lên.")
        print(f"Tài khoản {user} chưa có LoRA trên Kaggle: đưa {local.name} lên (một lần)...", flush=True)
        send_lora(local)
        for _ in range(90):                     # chờ Kaggle xử lý xong file (tối đa ~15 phút)
            if "ready" in kaggle("datasets", "status", lora_id, check=False):
                break
            time.sleep(10)
        else:
            sys.exit(f"Dataset {lora_id} chưa sẵn sàng sau 15 phút. Bấm Chạy tiếp sau ít phút.")

    spec = json.loads((video / "jobs.json").read_text(encoding="utf-8"))
    validate(spec["jobs"], video)
    clips = spec.get("clips", [])
    validate_clips(clips, spec["jobs"], video)
    if not spec["jobs"] and not clips:
        return print("jobs.json không có ảnh hay clip nào cần sinh")
    spec["settings"] = gen                      # cấu hình sinh ảnh đi theo job; không có khóa nào
    if clips:
        # giai đoạn clip chạy sau giai đoạn ảnh, cùng kernel; "i2v_override" (tools/i2v_bench.py) đè vài thông số
        spec["i2v"] = {**settings["i2v"], **spec.pop("i2v_override", {})}
    # mã lô: kernel chỉ chạy khi dataset job đúng là lô này (Kaggle đôi khi gắn phiên bản cũ, xem kernel_main.py)
    batch = time.strftime("%Y%m%d%H%M%S") + "-" + video.name[:3]
    spec["batch"] = batch
    kernel_id = f"{user}/{kg['kernel']}"
    marker = ROOT / "build" / user / "last_run.json"    # lần gửi gần nhất của tài khoản: video nào, đã tải về chưa
    names = [j["name"] for j in spec["jobs"]] + [c["name"] for c in clips]
    if not dry and resume(video, kaggle, kernel_id, names, marker, kg.get("poll_seconds", 60)):
        return

    # 1. Dataset job: jobs.json + worker.py + ảnh chuẩn, để phẳng một thư mục
    data = ROOT / "build" / user / "kaggle_data"
    shutil.rmtree(data, ignore_errors=True)
    data.mkdir(parents=True)
    (data / "jobs.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy(ROOT / "kaggle_job" / "worker.py", data)
    if clips:
        shutil.copy(ROOT / "kaggle_job" / "i2v_runner.py", data)
        shutil.copy(ROOT / "kaggle_job" / "wan5b_i2v.json", data)
    if hf_token:                                # dataset job là riêng tư; kernel đọc file này để tải model có đăng nhập
        (data / "hf_token").write_text(hf_token, encoding="utf-8")
    for ref in {r for j in spec["jobs"] for r in j.get("refs", []) if not r.startswith("@")} | \
            {c["image"] for c in clips if not c["image"].startswith("@")}:
        shutil.copy(ref_source(video, ref), data / ref)
    (data / f"batch_{batch}.txt").write_text(batch)  # tên file riêng của lô: thấy file này là phiên bản mới đã xong
    (data / "dataset-metadata.json").write_text(json.dumps(
        {"title": kg["job_dataset"], "id": f"{user}/{kg['job_dataset']}", "licenses": [{"name": "CC0-1.0"}]}))

    exists = dry or "ready" in kaggle("datasets", "status", f"{user}/{kg['job_dataset']}", check=False)
    if exists:
        kaggle("datasets", "version", "-p", data, "-m", f"job {video.name}")
    else:
        kaggle("datasets", "create", "-p", data)
    # Chờ Kaggle xử lý xong phiên bản MỚI. "ready" ngay sau khi tải lên có thể là của phiên bản cũ (video 014: kernel
    # gắn bản cũ 97 ảnh thay vì 3 ảnh), nên chờ tới khi danh sách file có đúng file mã lô này.
    for _ in range(0 if dry else 90):
        files = kaggle("datasets", "files", f"{user}/{kg['job_dataset']}", "--page-size", "200", check=False)
        if f"batch_{batch}.txt" in files and "ready" in kaggle("datasets", "status", f"{user}/{kg['job_dataset']}", check=False):
            break
        time.sleep(10)
    else:
        if not dry:
            sys.exit("Phiên bản mới của dataset job chưa sẵn sàng sau 15 phút. Bấm Chạy tiếp sau ít phút.")

    # 2. Kernel
    kernel = ROOT / "build" / user / "kaggle_kernel"
    shutil.rmtree(kernel, ignore_errors=True)
    kernel.mkdir(parents=True)
    (kernel / "kernel_main.py").write_text((ROOT / "kaggle_job" / "kernel_main.py").read_text(encoding="utf-8")
                                          .replace('EXPECTED = "__BATCH__"', f'EXPECTED = "{batch}"'), encoding="utf-8")
    (kernel / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/{kg['kernel']}", "title": kg["kernel"], "code_file": "kernel_main.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": True, "enable_internet": True,
        "machine_shape": kg.get("machine_shape", "NvidiaTeslaT4"),     # NvidiaTeslaT4 = GPU T4 x2
        "dataset_sources": [f"{user}/{kg['lora_dataset']}", f"{user}/{kg['job_dataset']}"]
        + ([f"{user}/{spec['i2v']['models_dataset']}"] if clips and spec["i2v"].get("models_dataset") else []),
        "competition_sources": [], "kernel_sources": []}, indent=1))
    # kernel quá hạn thì Kaggle tự dừng, không treo mãi; mỗi clip cộng thêm thời gian, tối đa 12 giờ một phiên
    minutes = int(kg.get("run_timeout_minutes", 90)) + len(clips) * settings["i2v"].get("minutes_per_clip", 6)
    timeout = min(minutes, 720) * 60

    def push():
        pushed = kaggle("kernels", "push", "-p", kernel, "-t", timeout)
        print(pushed.strip())
        if not dry:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({"video": video.name, "names": names, "time": time.time(), "fetched": False}))
        if "error" in pushed.lower():
            sys.exit("Đẩy kernel thất bại.")
        if "not valid dataset sources" in pushed:   # kernel chạy thiếu LoRA / job sẽ ra 0 ảnh: báo ngay, không chờ
            sys.exit("Kernel thiếu dataset (LoRA hoặc job) trên tài khoản Kaggle này. "
                     "Kaggle CLI không hủy được kernel; vào kaggle.com dừng tay nếu cần, rồi bấm Chạy tiếp.")

    push()
    # 3. Chờ và tải về. Ngay sau khi đẩy, trạng thái có thể vẫn là "complete" của lần chạy trước,
    # nên chỉ coi là xong khi đã thấy lần chạy mới vào hàng đợi hoặc đang chạy.
    started, retries, stale = False, 0, 0
    while not dry:
        status = kaggle("kernels", "status", f"{user}/{kg['kernel']}", check=False).lower()
        print(time.strftime("%H:%M:%S"), status.strip(), flush=True)
        started = started or "running" in status or "queued" in status
        if started and "running" in status and os.environ.get("SHORTS_PROGRESS"):
            report(kaggle, f"{user}/{kg['kernel']}", names, os.environ["SHORTS_PROGRESS"])
        if "complete" in status and started:
            if "STALE_BATCH" in kaggle("kernels", "logs", f"{user}/{kg['kernel']}", check=False) and stale < 3:
                stale += 1                      # kernel gắn phải dataset cũ và đã tự dừng: chờ rồi gửi lại
                print(f"Kernel gắn phải phiên bản cũ của dataset job, gửi lại lần {stale}/3 sau 60 giây", flush=True)
                time.sleep(60)
                push()
                started = False
                continue
            break
        if "error" in status and started and retries < START_RETRIES and kernel_never_ran(kaggle, f"{user}/{kg['kernel']}"):
            # log trống: Kaggle không khởi động được phiên máy (hết máy T4 rảnh, phiên hỏng), code chưa chạy dòng nào.
            # Thường thử lại là được (video 010-tao-mot-video-ke-chuyen, 2026-10-07).
            retries += 1
            print(f"Kaggle không khởi động được kernel (log trống), gửi lại lần {retries}/{START_RETRIES} sau 30 giây", flush=True)
            time.sleep(30)
            push()
            started = False
            continue
        if "error" in status or "cancel" in status:
            sys.exit("Kernel thất bại; xem log trên trang Kaggle của kernel.")
        time.sleep(kg.get("poll_seconds", 60))
    fetch(video, kaggle, f"{user}/{kg['kernel']}", dry)
    if not dry:
        mark_fetched(marker)


START_RETRIES = 2
RESUME_SHARE = 0.8      # không có dấu lần gửi: kết quả trên Kaggle phải có >= 80% ảnh cần sinh mới coi là của video này


def mark_fetched(marker):
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    marker.write_text(json.dumps({**data, "fetched": True}))


def resume(video, kaggle, kernel_id, names, marker, poll):
    """Trước khi gửi lô mới: lần chạy trước bị ngắt (tắt server, bấm dừng, mất mạng) mà kernel trên Kaggle vẫn chạy
    hoặc đã vẽ xong thì chờ / tải ảnh về, không vẽ lại. Trả về True khi đã tải về (không cần gửi lô mới)."""
    try:
        last = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        last = {}
    if last.get("fetched"):                    # kết quả lần trước đã lấy rồi: ảnh còn thiếu là ảnh lỗi / bị loại, vẽ mới
        return False
    ours = last.get("video") == video.name
    status = kaggle("kernels", "status", kernel_id, check=False).lower()
    if "running" in status or "queued" in status:
        if last and not ours:
            sys.exit(f"Kernel Kaggle của tài khoản này đang chạy cho video {last['video']}. Chờ xong rồi bấm Chạy tiếp.")
        print("Kernel lần trước vẫn đang chạy trên Kaggle: chờ xong rồi tải về, không gửi lại.", flush=True)
        while "running" in status or "queued" in status:
            if os.environ.get("SHORTS_PROGRESS"):
                report(kaggle, kernel_id, names, os.environ["SHORTS_PROGRESS"])
            time.sleep(poll)
            status = kaggle("kernels", "status", kernel_id, check=False).lower()
            print(time.strftime("%H:%M:%S"), status.strip(), flush=True)
    if "complete" not in status:               # lỗi, bị hủy, chưa từng chạy: gửi lô mới
        return False
    have, token = set(), None                  # danh sách file kết quả, tối đa 200 dòng một trang (ảnh + .json)
    for _ in range(20):
        files = kaggle("kernels", "files", kernel_id, "--page-size", "200", *(["--page-token", token] if token else []),
                       check=False)
        have |= {Path(line.split()[0]).stem for line in files.splitlines() if line.split() and line.split()[0].endswith((".png", ".mp4"))}
        found = re.search(r"Next Page Token = (\S+)", files)
        token = found.group(1) if found else None
        if not token:
            break
    match = len(have & set(names))
    if not match or (not ours and match < RESUME_SHARE * len(names)):
        return False
    print(f"Kaggle đã có {match}/{len(names)} ảnh của video này từ lần chạy trước: tải về, không vẽ lại.", flush=True)
    fetch(video, kaggle, kernel_id, False)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"video": video.name, "names": names, "time": time.time(), "fetched": True}))
    return True


def kernel_never_ran(kaggle, kernel):
    """True khi log của lần chạy vừa rồi trống: kernel lỗi trước khi code kịp in dòng nào."""
    text = kaggle("kernels", "logs", kernel, check=False)
    try:
        events = json.loads(text[text.index("["):])
        return not any((e.get("data") or "").strip() for e in events)
    except ValueError:
        return not text.strip()


def report(kaggle, kernel, names, path):
    """Đọc log đang chạy của kernel, đếm ảnh xong / lỗi / đang sinh, ghi ra file JSON cho trang web (tools/auto.py).
    `kaggle kernels logs` chỉ có log khi kernel đã xong, nên đọc luồng log trực tiếp (tools/kaggle_live.py)."""
    try:
        text = subprocess.run([sys.executable, str(ROOT / "tools" / "kaggle_live.py"), kernel, "8"],
                              env=kaggle.env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=90).stdout
    except (OSError, subprocess.TimeoutExpired):
        text = ""
    wanted = set(names)
    done = {n for n in re.findall(r"GPU \d+ xong: (\S+)", text) if n in wanted}
    failed = {n for n in re.findall(r"GPU \d+ LỖI ở (\S+?):", text) if n in wanted}
    begun = {n for n in re.findall(r"GPU \d+ bắt đầu: (\S+)", text) if n in wanted}
    Path(path).write_text(json.dumps({"total": len(names), "done": len(done), "failed": len(failed),
                                      "current": sorted(begun - done - failed), "loading": not begun,
                                      "time": time.time()}), encoding="utf-8")
    print(f"  tiến trình: {len(done)}/{len(names)} ảnh xong, {len(failed)} lỗi", flush=True)


def png_error(path):
    """Kaggle có thể lưu trang lỗi HTTP 502 dưới tên .png dù lệnh tải báo thành công."""
    try:
        with Image.open(path) as img:
            if img.format != "PNG":
                return "không phải PNG"
            img.verify()
        with Image.open(path) as img:
            img.load()
    except (OSError, ValueError, SyntaxError) as error:
        return str(error)
    return None


def fetch(video, kaggle, kernel, dry):
    """Tải kết quả lần chạy gần nhất của kernel về work/kaggle/, rồi chép từng ảnh về đúng chỗ."""
    out = video / "work" / "kaggle"
    shutil.rmtree(out, ignore_errors=True)       # chỉ giữ kết quả của lần chạy này
    out.mkdir(parents=True)
    bad = []
    for attempt in range(3):                   # kiểm tra nội dung ảnh, không chỉ thông báo của CLI
        retry = ["--file-pattern", "(?:" + "|".join(re.escape(p.name) for p in bad) + ")$"] if bad else []
        result = kaggle("kernels", "output", kernel, "-p", out, "-o", *retry, check=False)
        if dry:
            break
        bad = [p for p in out.rglob("*.png") if png_error(p)]
        if not bad and "Max retries exceeded" not in result and "Error" not in result:
            break
        if bad:
            print("  ảnh tải về không hợp lệ: " + ", ".join(p.name for p in bad), flush=True)
        if attempt == 2:
            break
        print(f"Tải về lỗi, thử lại lần {attempt + 2}...", flush=True)
        time.sleep(10)
    if dry:
        return
    failed = [p.name for p in out.rglob("*.failed")]
    print(f"Đã tải {len(list(out.rglob('*.png')))} ảnh về {out}. Lỗi: {failed or 'không'}")
    for png in sorted(out.rglob("*.png")):
        if png in bad:
            continue
        target = destination(video, png.stem)
        if target is None:
            continue
        if target.exists() and not png_error(target):
            print(f"  giữ ảnh đã có: {target.relative_to(ROOT)}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(png, target)
        print(f"  -> {target.relative_to(ROOT)}")
    if bad:
        sys.exit("Không tải được ảnh PNG hợp lệ sau 3 lần: " + ", ".join(p.name for p in bad)
                 + ". Chạy tools/run_kaggle.py <video> --fetch để tải lại, không cần sinh lại ảnh.")
    # clip chép SAU ảnh: clip không cũ hơn tranh cả cảnh của nó (make_jobs.clip_ready); luôn ghi đè clip cũ
    for mp4 in sorted(out.rglob("clip_*.mp4")):
        target = video / "clips" / f"{mp4.stem.removeprefix('clip_')}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(mp4, target)
        print(f"  -> {target.relative_to(ROOT)}")
    for found in out.rglob("clips_results.json"):
        local = video / "clips" / "results.json"
        local.parent.mkdir(parents=True, exist_ok=True)
        try:
            merged = json.loads(local.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            merged = {}
        merged.update(json.loads(found.read_text(encoding="utf-8")))
        local.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
        failed = {k: v.get("status") for k, v in merged.items() if not k.startswith("_") and v.get("status") != "done"}
        print(f"Clip: {sum(1 for k, v in merged.items() if v.get('status') == 'done')} xong. Lỗi: {failed or 'không'}")


def destination(video, name):
    """Chỗ đặt ảnh theo tiền tố tên job (xem tools/make_jobs.py). Tên khác thì để nguyên trong work/kaggle/."""
    prefix, _, rest = name.partition("_")
    return {"bg": ROOT / "library" / "backgrounds" / f"{rest}.png",      # nền dùng chung mọi video
            "ref": REFS / f"{rest}_front.png",                           # ảnh chuẩn dùng chung mọi video
            "ch": video / "characters" / f"{rest}.png",
            "full": video / "full" / f"{rest}.png"}.get(prefix)            # cách dựng mới: tranh vẽ cả cảnh có người


if __name__ == "__main__":
    main()
