"""Tải video hiệu ứng nền đen (lấp lánh, bokeh, vệt sáng, bụi sáng, giấy màu, khói) từ Mixkit vào library/fx/<nhóm>/.

  python tools/fetch_fx.py          # tải file còn thiếu (nghỉ 1,5 giây giữa hai lần tải)

Giấy phép Mixkit (https://mixkit.co/license/#videoFree, đọc 2026-10-08): dùng miễn phí cả thương mại, không cần ghi nguồn;
cấm bán / phát tán lại chính file gốc. Thư mục library/fx/ nằm trong .gitignore.

Mỗi file được đổi sẵn sang khung dọc 540x960, 30 fps, tối đa 10 giây (nhẹ, đọc nhanh khi dựng); build_video.py phóng lên
1080x1920 và chồng bằng chế độ "screen" (phần đen biến mất, chỉ còn ánh sáng).
"""
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "library" / "fx"
UA = {"User-Agent": "Mozilla/5.0 (shorts-pipeline; personal use)"}
# nhóm -> [(id, slug trên mixkit.co/free-stock-video/<slug>-<id>/)]
PICKS = {   # đã xem từng file (2026-10-08): bỏ các file nền màu (tím, hồng), trắng xóa, vàng phủ kín khung, gần như đen
    "sparkle": [(47961, "inspirational-sparkles-on-black-background")],               # đốm sáng cam bay lên: vui
    "bokeh": [(99828, "monochrome-bokeh-lights-floating-softly"),
              (99858, "vertical-shot-of-colorful-bokeh-lights-against-a-dark-background")],   # cảm động, ấm áp
    "light_leak": [(48011, "light-leaks-overlay"), (48012, "purple-light-leaks-overlay"),
                   (48013, "blue-lights-leaks-overlay"), (48494, "sunlight-flare-overlay")],   # hồi tưởng, kỷ niệm
    "dust": [(47285, "dust-floating-on-black-background"),
             (4407, "white-particles-moving-on-black-background")],                   # lặng, đêm, buồn nhẹ
    "gold": [(30888, "sparkles-of-golden-glitter-moving-vertically")],                # mưa vàng chéo (dùng mờ): đắc ý
    "magic": [(18142, "luminous-particles-on-black-background")],                    # ý tưởng, kỳ diệu
    "glitter": [(99995, "shimmering-silver-confetti-falling-down-over-a-black-background"),
                (99994, "close-up-shot-of-metallic-confetti-falling-over-a-black")],   # mừng rỡ, ăn mừng
    # đã bỏ: smoke 12496 (khói quay thật trên tranh phẳng trông như vết bẩn, video 022 cảnh 39-41)
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return r.read()


def video_url(vid, slug):
    page = get(f"https://mixkit.co/free-stock-video/{slug}-{vid}/").decode("utf-8", "replace")
    found = re.findall(r"https://assets\.mixkit\.co/[^\"'?\s]*?-720\.mp4", page)
    return found[0] if found else f"https://assets.mixkit.co/videos/{vid}/{vid}-720.mp4"


def main():
    total = 0
    for group, items in PICKS.items():
        folder = OUT / group
        folder.mkdir(parents=True, exist_ok=True)
        for vid, slug in items:
            target = folder / f"{vid}.mp4"
            if target.exists():
                total += 1
                continue
            raw = folder / f"{vid}_raw.mp4"
            try:
                raw.write_bytes(get(video_url(vid, slug)))
            except Exception as e:  # noqa: BLE001
                print(f"{group}/{vid}: lỗi tải {e}", flush=True)
                continue
            # khung dọc 540x960 (phủ kín rồi cắt giữa), 30 fps, tối đa 10 giây, không tiếng
            ok = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-t", "10", "-an", "-vf",
                                 "scale=540:960:force_original_aspect_ratio=increase,crop=540:960,fps=30",
                                 "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(target)]).returncode == 0
            raw.unlink(missing_ok=True)
            print(f"{group}/{vid}: {'xong' if ok else 'lỗi đổi khung'}", flush=True)
            total += ok
            time.sleep(1.5)
    print(f"Tổng {total} hiệu ứng trong {len(PICKS)} nhóm.")


if __name__ == "__main__":
    sys.exit(main())
