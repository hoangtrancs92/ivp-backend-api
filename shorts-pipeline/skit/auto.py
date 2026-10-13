"""Tiểu phẩm: chạy trọn một video từ ý tưởng -> output.mp4.

  python skit/auto.py skits/<tên>        # ý tưởng đọc từ skits/<tên>/prompt.txt

Bước nào đã có kết quả thì bỏ qua, nên chạy lại là chạy tiếp từ chỗ dừng. Tiến trình ghi vào skits/<tên>/progress.json
(cùng dạng tools/auto.py để trang web đọc). Không duyệt ảnh: dùng luôn ảnh Kaggle vẽ.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from kaggle_quota import quota          # noqa: E402
from assets import missing_images, normalize_assets  # noqa: E402

STEPS = [
    ("script", "Viết tiểu phẩm"),
    ("voice", "Giọng đọc"),
    ("direct", "Kế hoạch dựng"),
    ("sounds", "Tìm tiếng hiệu ứng"),
    ("jobs", "Lên danh sách ảnh"),
    ("kaggle", "Sinh ảnh trên Kaggle"),
    ("cutouts", "Tách nền"),
    ("stage", "Dàn cảnh"),
    ("build", "Dựng video"),
]
ROUNDS = 3        # lượt Kaggle tối đa (ảnh lỗi vẽ lại ở lượt sau)
EXTENDS = 2       # số lần nhờ AI viết thêm khi đọc thật vẫn ngắn hơn 60 giây
SHORT = 5         # mã thoát của skit/voice.py


class Progress:
    def __init__(self, folder):
        self.path = folder / "progress.json"
        old = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.data = {"kind": "skit", "steps": {k: {"label": label, "status": "pending"} for k, label in STEPS},
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


def run(args, env=None):
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1", **(env or {})}
    return subprocess.run([sys.executable, *map(str, args)], cwd=ROOT, env=env).returncode


def missing(folder):
    """Cùng danh sách ảnh với bước sinh ảnh và dựng, kể cả biểu cảm / tư thế / tranh chèn."""
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    _, problems = normalize_assets(skit)
    if problems:
        raise ValueError("Tiểu phẩm có lỗi ảnh:\n  " + "\n  ".join(problems))
    return missing_images(folder, skit)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    folder = Path(sys.argv[1]).resolve()
    rel = folder.relative_to(ROOT).as_posix()
    p = Progress(folder)
    account = (os.environ.get("SHORTS_KAGGLE_USERNAME", ""), os.environ.get("SHORTS_KAGGLE_KEY", ""))

    def fail(key, message):
        p.step(key, "failed", message)
        p.data["error"] = message
        p.save()
        sys.exit(message)

    # 1-2. Kịch bản và giọng đọc (đọc trước khi vẽ: biết chắc đủ 60 giây, thiếu thì viết thêm khi chưa tốn GPU)
    if (folder / "skit.json").exists():
        p.step("script", "skipped", "đã có skit.json")
    else:
        p.step("script", "running")
        if run(["skit/write.py", rel, folder / "prompt.txt"]):
            fail("script", "AI không viết được tiểu phẩm, xem log.")
        p.step("script", "done")
    script_path = folder / "skit.json"
    skit = json.loads(script_path.read_text(encoding="utf-8"))
    before = json.dumps(skit, ensure_ascii=False)
    _, problems = normalize_assets(skit)
    if problems:
        fail("script", "Tiểu phẩm có lỗi ảnh:\n  " + "\n  ".join(problems))
    if json.dumps(skit, ensure_ascii=False) != before:
        script_path.write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    for attempt in range(EXTENDS + 1):
        p.step("voice", "running")
        code = run(["skit/voice.py", rel])
        if code == 0:
            break
        if code != SHORT or attempt == EXTENDS:
            fail("voice", "Lỗi giọng đọc (VOICEVOX?), xem log." if code != SHORT else "Tiểu phẩm vẫn ngắn hơn 60 giây.")
        seconds = json.loads((folder / "work" / "short.json").read_text(encoding="utf-8"))["seconds"]
        p.step("script", "running", f"đọc thật {seconds:.0f} giây, viết thêm")
        if run(["skit/write.py", rel, "--extend", seconds]):
            fail("script", "AI không viết thêm được, xem log.")
        p.step("script", "done", "đã viết thêm")
    timing = json.loads((folder / "audio" / "timing.json").read_text(encoding="utf-8"))
    p.step("voice", "done", f"{timing['total']:.0f} giây")

    # Lượt đạo diễn: AI lên kế hoạch dựng (kỹ xảo, chữ tượng thanh, tiếng, tông màu); lỗi thì dựng theo kịch bản gốc
    p.step("direct", "running")
    if run(["skit/write.py", rel, "--direct"]):
        p.step("direct", "done", "bỏ qua (lỗi, dựng theo kịch bản gốc)")
    else:
        p.step("direct", "done")

    # Tiếng hiệu ứng: tìm mới theo mô tả từng câu; lỗi (mạng, AI) thì dựng không có tiếng, không chặn video
    p.step("sounds", "running")
    if run(["skit/sounds.py", rel]):
        p.step("sounds", "done", "bỏ qua (lỗi tìm tiếng, xem log)")
    else:
        sounds = json.loads((folder / "skit.json").read_text(encoding="utf-8")).get("sounds") or {}
        p.step("sounds", "done", f"{sum(v is not None for v in sounds.values())}/{len(sounds)} tiếng")

    # 3-4. Ảnh trên Kaggle
    progress_file = folder / "work" / "kaggle_progress.json"
    for round_no in range(1, ROUNDS + 1):
        p.step("jobs", "running")
        if run(["skit/jobs.py", rel]):
            fail("jobs", "Không tạo được jobs.json, xem log.")
        jobs = json.loads((folder / "jobs.json").read_text(encoding="utf-8"))["jobs"]
        p.step("jobs", "done", f"{len(jobs)} ảnh cần sinh")
        if not jobs:
            if p.data["steps"]["kaggle"]["status"] == "pending":
                p.step("kaggle", "skipped", "đủ ảnh")
            break
        p.step("kaggle", "running", f"lượt {round_no}: {len(jobs)} ảnh")
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        progress_file.unlink(missing_ok=True)
        before = quota(*account)
        code = run(["tools/run_kaggle.py", rel], env={"SHORTS_PROGRESS": str(progress_file)})
        after = quota(*account)
        if "used" in before and "used" in after:
            p.data["gpu_hours"] = round(p.data["gpu_hours"] + max(0.0, after["used"] - before["used"]), 2)
        if code:
            fail("kaggle", "Lô Kaggle thất bại, xem log (có thể đã hết giờ GPU).")
        p.step("kaggle", "done", f"xong lượt {round_no}")
        if not missing(folder):
            break
    if missing(folder):
        fail("kaggle", f"Sau {ROUNDS} lượt vẫn thiếu ảnh: {', '.join(missing(folder))}")

    # 5-6. Tách nền, dựng
    for key, args in [("cutouts", ["steps/04_cutouts.py", rel]), ("stage", ["skit/stage.py", rel]),
                      ("build", ["skit/build.py", rel])]:
        p.step(key, "running")
        if run(args):
            if key == "stage":                      # dàn cảnh lỗi (AI): dựng xếp hàng, không chặn video
                p.step(key, "done", "bỏ qua (lỗi, nhân vật xếp hàng), xem log")
                continue
            fail(key, f"Lỗi ở bước {p.data['steps'][key]['label']}, xem log.")
        p.step(key, "done")
    if run(["skit/add_music.py", rel]):              # nhạc nền (library/bgm/comical); lỗi thì vẫn giữ video không nhạc
        print("Không chèn được nhạc nền, xem log.")
    print(f"Xong: {folder / 'output.mp4'}")


if __name__ == "__main__":
    main()
