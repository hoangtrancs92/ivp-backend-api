"""Chạy quy trình một video: đề tài -> kịch bản -> ảnh trên Kaggle -> người duyệt ảnh -> output.mp4.

  python tools/auto.py videos/<tên>        # đề tài đọc từ videos/<tên>/prompt.txt

Bước nào đã có kết quả thì bỏ qua, nên chạy lại là chạy tiếp từ chỗ dừng.
Chế độ duyệt ảnh SHORTS_REVIEW_MODE: manual (mặc định), ai (AI chấm hết, tự vẽ lại ảnh trượt rồi làm tiếp),
none (dùng luôn ảnh Kaggle vẽ). Chế độ manual: sau khi tải ảnh, dừng ở bước "Duyệt ảnh" (thoát với mã 3) chờ người xem trên web:
duyệt thì ghi review/approved.json rồi chạy lại lệnh này để làm tiếp; chọn ảnh để vẽ lại thì web chuyển ảnh sang rejected/
(hoặc đặt SHORTS_AI_CHECK=<khóa ảnh,...> để AI chấm các ảnh đó trước, chỉ ảnh dưới ngưỡng bị vẽ lại) rồi chạy lại.
Tài khoản lấy từ biến môi trường như tools/run_kaggle.py (SHORTS_KAGGLE_USERNAME, SHORTS_KAGGLE_KEY, SHORTS_HF_TOKEN),
khóa Claude từ ANTHROPIC_API_KEY. Tiến trình ghi vào videos/<tên>/progress.json cho trang web (web/app.py) đọc.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "steps"))
from run_local import missing_images   # noqa: E402
from common import image_stamp, review_items   # noqa: E402
from kaggle_quota import quota          # noqa: E402

STEPS = [
    ("script", "Viết kịch bản"),
    ("jobs", "Lên danh sách ảnh"),
    ("kaggle", "Sinh ảnh trên Kaggle"),
    ("photos", "Ảnh thật (Pixabay / Pexels)"),
    ("review", "Duyệt ảnh"),
    ("cutouts", "Tách nền"),
    ("faces", "Mắt, miệng"),
    ("preview", "Bố cục cảnh"),
    ("voice", "Giọng đọc"),
    ("build", "Dựng video"),
]
ROUNDS = 3      # số lượt Kaggle tối đa mỗi lần chạy (ảnh lỗi trên Kaggle, ảnh AI chấm trượt được vẽ lại ở lượt sau)
WAITING = 3     # mã thoát: đang chờ người duyệt ảnh
MODES = {"manual": "Người duyệt", "ai": "AI đã tự duyệt", "none": "Không duyệt, dùng luôn ảnh Kaggle"}   # SHORTS_REVIEW_MODE


class Progress:
    def __init__(self, video):
        self.path = video / "progress.json"
        old = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.data = {"steps": {k: {"label": label, "status": "pending"} for k, label in STEPS},
                     "gpu_hours": old.get("gpu_hours", 0.0), "error": None, "started": time.time()}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")

    def step(self, key, status, note=None):
        s = self.data["steps"][key]
        s["status"] = status
        s["started" if status == "running" else "ended"] = time.time()
        if note is not None:
            s["note"] = note
        self.save()
        print(f"== {s['label']}: {status}" + (f" ({note})" if note else ""), flush=True)


def run(args, cwd=ROOT, env=None):
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", **(env or {})}
    return subprocess.run([sys.executable, *map(str, args)], cwd=cwd, env=env).returncode == 0


def restore_rejected(video, missing):
    """Đưa lần vẽ bị loại gần nhất của từng ảnh còn thiếu trở lại characters/ (chuyển về, không chép)."""
    used = []
    for item in missing:
        target = video / item
        tries = [f for f in (video / "rejected").glob(f"{target.stem}*.png")
                 if f.stem == target.stem or f.stem[len(target.stem):].lstrip("_").isdigit()]
        if tries:
            max(tries, key=lambda f: f.stat().st_mtime).rename(target)
            used.append(target.name)
    return used


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    video = Path(sys.argv[1]).resolve()
    rel = video.relative_to(ROOT).as_posix()
    p = Progress(video)
    account = (os.environ.get("SHORTS_KAGGLE_USERNAME", ""), os.environ.get("SHORTS_KAGGLE_KEY", ""))

    def fail(key, message):
        p.step(key, "failed", message)
        p.data["error"] = message
        p.save()
        sys.exit(message)

    # 1. Kịch bản
    if (video / "script.json").exists():
        p.step("script", "skipped", "đã có script.json")
    else:
        p.step("script", "running")
        if not run(["steps/01_script.py", rel, video / "prompt.txt"]):
            fail("script", "Claude không viết được kịch bản, xem log.")
        p.step("script", "done")

    # 2-3. Ảnh: vẽ ảnh còn thiếu trên Kaggle. AI chấm khi người duyệt nhờ chấm vài ảnh (SHORTS_AI_CHECK)
    # hoặc khi video chọn chế độ "ai" (chấm hết); ảnh trượt bị bỏ và vẽ lại ở lượt sau bằng seed khác.
    mode = os.environ.get("SHORTS_REVIEW_MODE", "manual")
    if mode not in MODES:
        mode = "manual"
    progress_file = video / "work" / "kaggle_progress.json"
    ai_check = [k for k in os.environ.get("SHORTS_AI_CHECK", "").split(",") if k]
    for round_no in range(1, ROUNDS + 1):
        p.step("jobs", "running")
        if not run(["tools/make_jobs.py", rel]):
            fail("jobs", "Không tạo được jobs.json (kịch bản có lỗi?), xem log.")
        jobs = json.loads((video / "jobs.json").read_text(encoding="utf-8"))["jobs"]
        p.step("jobs", "done", f"{len(jobs)} ảnh cần sinh")
        if jobs:
            p.step("kaggle", "running", f"lượt {round_no}: {len(jobs)} ảnh")
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            progress_file.unlink(missing_ok=True)
            before = quota(*account)
            ok = run(["tools/run_kaggle.py", rel], env={"SHORTS_PROGRESS": str(progress_file)})
            after = quota(*account)
            if "used" in before and "used" in after:     # giờ GPU thật Kaggle trừ cho lần này
                p.data["gpu_hours"] = round(p.data["gpu_hours"] + max(0.0, after["used"] - before["used"]), 2)
            if not ok:
                fail("kaggle", "Lô Kaggle thất bại, xem log (có thể đã hết giờ GPU).")
            p.step("kaggle", "done", f"xong lượt {round_no}")
        elif p.data["steps"]["kaggle"]["status"] == "pending":
            p.step("kaggle", "skipped", "đủ ảnh")
        if missing_images(video):               # Kaggle vẽ lỗi vài ảnh: lượt sau vẽ lại
            continue

        if ai_check or mode == "ai":
            which = ["--only", ",".join(ai_check)] if ai_check else ["--all"]
            p.step("review", "running", f"AI chấm {len(ai_check) if ai_check else 'mọi'} ảnh (lượt {round_no})")
            if not run([ROOT / "review.py", "images", *which], cwd=video):
                fail("review", "AI không chấm được ảnh (khóa AI, model?), xem log.")
            ai_check = []
            redo = missing_images(video)
            p.step("review", "running", f"AI chấm xong lượt {round_no}: {len(redo)} ảnh cần vẽ lại")
            if redo:
                continue
        break
    else:
        if mode == "ai":                        # AI tự duyệt mà hết lượt: dùng tạm lần vẽ gần nhất để video vẫn ra
            used = restore_rejected(video, missing_images(video))
            p.data["review_warning"] = f"{len(used)} ảnh AI chưa chấm đạt sau {ROUNDS} lượt, dùng tạm: {', '.join(used)}"
        if missing_images(video):
            fail("kaggle", f"Sau {ROUNDS} lượt vẫn thiếu {len(missing_images(video))} ảnh, xem log.")

    # 3b. Ảnh thật Pexels cho cảnh "photo" (trước bước duyệt: người duyệt bỏ ảnh lạc đề, lần chạy sau lấy ảnh khác)
    p.step("photos", "running")
    if run(["steps/fetch_photos.py", rel]):
        p.step("photos", "done", "bỏ qua (lỗi tải ảnh, xem log), dựng không có ảnh thật")
    else:
        got = len(list((video / "photos").glob("[0-9][0-9][0-9].jpg"))) if (video / "photos").exists() else 0
        p.step("photos", "done", f"{got} ảnh" if got else "không có cảnh ảnh thật")

    # 4. Duyệt ảnh: người xem bằng mắt trên web (manual), hoặc tự qua khi chọn "ai" / "none"
    approved_file = video / "review" / "approved.json"
    if mode != "manual":
        approved_file.parent.mkdir(exist_ok=True)
        approved_file.write_text(json.dumps({"stamp": image_stamp(video), "by": mode, "note": MODES[mode], "at": time.time()},
                                            ensure_ascii=False), encoding="utf-8")
    approved = json.loads(approved_file.read_text(encoding="utf-8")) if approved_file.exists() else {}
    if approved.get("stamp") != image_stamp(video):
        p.step("review", "waiting", f"Chờ duyệt {len(review_items(video))} ảnh trên trang web")
        print("Đang chờ người duyệt ảnh. Duyệt trên trang web, quy trình sẽ chạy tiếp.", flush=True)
        sys.exit(WAITING)
    note = approved.get("note") or f"{approved.get('by', '?')} đã duyệt"
    p.step("review", "done", note + (f" · {p.data['review_warning']}" if p.data.get("review_warning") else ""))

    # 5-8. Phần chạy ở máy (giống run_local.py)
    for key, args, cwd in [("cutouts", ["steps/04_cutouts.py", rel], ROOT),
                           ("faces", ["tools/make_faces.py", rel], ROOT),
                           ("preview", [ROOT / "build_video.py", "--preview"], video),
                           ("voice", ["steps/06_voice.py", rel], ROOT),
                           ("build", [ROOT / "build_video.py"], video)]:
        p.step(key, "running")
        if not run(args, cwd=cwd):
            if key == "faces":                  # chớp mắt / mấp máy miệng chỉ thêm sinh động: lỗi thì dựng không có
                p.step(key, "done", "bỏ qua (lỗi tạo ảnh mắt, miệng, xem log)")
                continue
            fail(key, f"Lỗi ở bước {p.data['steps'][key]['label']}, xem log.")
        p.step(key, "done")
    print(f"Xong: {video / 'output.mp4'}")


if __name__ == "__main__":
    main()
