"""Chạy phần local của pipeline cho một video. Bước nào thấy kết quả đã có thì bỏ qua.

  python run_local.py videos/001-ten-video ["chủ đề truyện"]

Ảnh nền, nhân vật và đạo cụ sinh trên Kaggle (tools/make_bg_jobs.py + tools/run_kaggle.py, xem README.md).
Lệnh này kiểm tra đủ ảnh rồi chạy: tách nền, xem trước bố cục, giọng đọc, dựng video.
Có ANTHROPIC_API_KEY thì Claude duyệt bố cục sau bước 5 (chỉ ghi đề xuất vào review/layout.json).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "steps"))
from common import character_files   # noqa: E402


def run(name, args, cwd=None):
    print(f"== {name}", flush=True)
    env = {**os.environ, "PYTHONUTF8": "1"}         # console Windows mặc định không in được tiếng Việt khi bị chuyển hướng
    if subprocess.run([sys.executable, *map(str, args)], cwd=cwd, env=env).returncode != 0:
        sys.exit(f"Dừng ở bước {name}. Sửa lỗi rồi chạy lại, các bước đã xong sẽ được bỏ qua.")


def missing_images(video):
    """Ảnh phải có trước khi dựng: nền theo bối cảnh, ảnh chủ thể (nhân vật hoặc đồ vật) theo cảnh."""
    script = json.loads((video / "script.json").read_text(encoding="utf-8"))
    missing = []
    for scene in script["scenes"]:
        bg = f"backgrounds/{scene['location']}.png"
        if not (video / bg).exists() and not (ROOT / "library" / bg).exists():
            missing.append(bg)
        files = [f for _, f in character_files(scene)]
        if scene.get("alt_pose"):                   # tư thế thứ hai của từng nhân vật có alt_pose
            pose = scene["alt_pose"]
            files += [f"{Path(f).stem}_alt.png" for name, f in character_files(scene)
                      if not isinstance(pose, dict) or pose.get(name)]
        missing += [f"characters/{f}" for f in files
                    if not (video / "characters" / f).exists() and not (video / "cutouts" / f).exists()]
    return sorted(set(missing))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    video = Path(sys.argv[1]).resolve()
    video.mkdir(parents=True, exist_ok=True)
    steps = ROOT / "steps"

    if not (video / "script.json").exists():
        if len(sys.argv) < 3:
            sys.exit("Chưa có script.json: thêm chủ đề truyện làm tham số thứ hai.")
        run("01 kịch bản", [steps / "01_script.py", video, sys.argv[2]])
        sys.exit("Đã có kịch bản. Đọc và sửa script.json, rồi chạy lại lệnh này.")

    missing = missing_images(video)
    if missing:
        print(f"Thiếu {len(missing)} ảnh, cần sinh trên Kaggle trước (xem README.md):")
        print("\n".join(f"  {m}" for m in missing[:20]) + ("\n  ..." if len(missing) > 20 else ""))
        sys.exit(1)

    run("04 tách nền", [steps / "04_cutouts.py", video])
    run("05 bố cục", [ROOT / "build_video.py", "--preview"], cwd=video)
    if os.environ.get("ANTHROPIC_API_KEY"):
        run("05 Claude duyệt bố cục", [ROOT / "review.py", "layout"], cwd=video)
    run("06 giọng đọc", [steps / "06_voice.py", video])
    run("07 dựng", [ROOT / "build_video.py"], cwd=video)
    print(f"Xong: {video / 'output.mp4'}")


if __name__ == "__main__":
    main()
