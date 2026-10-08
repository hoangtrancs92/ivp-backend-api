"""Tạo ảnh giữ chỗ (nền, nhân vật, đạo cụ) cho một video, để chạy thử bước 4-7 khi chưa có GPU.

  python tools/make_placeholders.py videos/000-dry-run

Ghi vào backgrounds/ và characters/ đúng tên file mà Kaggle sẽ sinh; file đã có thì giữ nguyên.
Đừng chạy trên thư mục video thật: bước 2 và 3 thấy file đã có sẽ không sinh ảnh thật.
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "steps"))
from common import ROOT, character_files, load_script, video_dir   # noqa: E402

FONT = ROOT / "fonts" / "NotoSansCJKjp-Black.otf"
INK = "#3A2A20"


def colour(name, light=False):
    h = hashlib.md5(name.encode()).digest()
    base = 150 if light else 60
    return tuple(base + h[i] % 90 for i in range(3))


def font(size):
    return ImageFont.truetype(str(FONT), size)


def background(name, path):
    img = Image.new("RGB", (864, 1536))
    top, bottom = colour(name, light=True), colour(name + "x")
    d = ImageDraw.Draw(img)
    for y in range(1536):
        t = y / 1535
        d.line((0, y, 864, y), fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    d.text((432, 1300), name, font=font(60), anchor="mm", fill="white", stroke_width=4, stroke_fill=INK)
    img.save(path)


def character(name, label, path, alt=False):
    """alt=True: tư thế thứ hai (giơ tay phải, bước chân) để thử cảnh có alt_pose."""
    img = Image.new("RGB", (768, 1024), "white")
    d = ImageDraw.Draw(img)
    body = colour(name)
    d.rounded_rectangle((254, 330, 514, 760), 60, fill=body, outline=INK, width=8)       # thân
    step = 40 if alt else 0
    d.rectangle((290 - step, 750, 350 - step, 950), fill="#555555", outline=INK, width=8)   # chân
    d.rectangle((418 + step, 750, 478 + step, 950), fill="#555555", outline=INK, width=8)
    d.rounded_rectangle((180, 360, 250, 620), 30, fill=body, outline=INK, width=8)       # tay
    if alt:
        d.rounded_rectangle((518, 110, 588, 370), 30, fill=body, outline=INK, width=8)
    else:
        d.rounded_rectangle((518, 360, 588, 620), 30, fill=body, outline=INK, width=8)
    d.ellipse((264, 90, 504, 330), fill="#FFE0C4", outline=INK, width=8)                 # đầu
    d.ellipse((330, 190, 350, 215), fill=INK)
    d.ellipse((418, 190, 438, 215), fill=INK)
    d.text((384, 545), label, font=font(48), anchor="mm", fill="white", stroke_width=3, stroke_fill=INK)
    img.save(path)


def prop(name, path):
    img = Image.new("RGB", (768, 768), "white")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((214, 140, 554, 640), 50, fill=colour(name, light=True), outline=INK, width=10)
    d.text((384, 390), name, font=font(44), anchor="mm", fill=INK)
    img.save(path)


def main():
    video = video_dir()
    script = load_script(video)
    for d in ("backgrounds", "characters"):
        (video / d).mkdir(exist_ok=True)
    made = 0
    for scene in script["scenes"]:
        jobs = [(video / "backgrounds" / f"{scene['location']}.png", lambda p: background(scene["location"], p))]
        for name, filename in character_files(scene):
            if name is None:                        # cảnh chỉ có đồ vật
                jobs.append((video / "characters" / filename, lambda p: prop(scene["object"][:24], p)))
                continue
            jobs.append((video / "characters" / filename, lambda p, n=name: character(n, f"{n} {scene['id']}", p)))
            if scene.get("alt_pose"):
                jobs.append((video / "characters" / f"{Path(filename).stem}_alt.png",
                             lambda p, n=name: character(n, f"{n} {scene['id']}", p, alt=True)))
        for path, make in jobs:
            if not path.exists():
                make(path)
                made += 1
    print(f"Đã tạo {made} ảnh giữ chỗ trong {video}")


if __name__ == "__main__":
    main()
