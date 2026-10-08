"""Vẽ bộ sticker cảm xúc cơ bản vào library/stickers/ (PNG nền trong suốt). Chạy một lần:

  python tools/make_stickers.py

Đây là bộ tạm, nét đơn giản. Về sau có thể thay bằng sticker sinh từ klein + style LoRA, giữ nguyên tên file.
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "library" / "stickers"
FONT = ROOT / "fonts" / "NotoSansCJKjp-Black.otf"
S = 400                                   # cạnh ảnh vẽ
INK = "#3A2A20"                           # màu viền
W = 14                                    # độ dày viền


def canvas():
    img = Image.new("RGBA", (S, S))
    return img, ImageDraw.Draw(img)


def save(img, name):
    img.crop(img.getbbox()).save(OUT / f"{name}.png")
    print(f"stickers/{name}.png")


def bar(d, x0, y0, x1, y1, width, fill):
    """Vạch có viền, đầu tròn."""
    r = width / 2 + W / 2
    d.line((x0, y0, x1, y1), fill=INK, width=round(2 * r))
    for x, y in ((x0, y0), (x1, y1)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=INK)
    d.line((x0, y0, x1, y1), fill=fill, width=width)
    for x, y in ((x0, y0), (x1, y1)):
        d.ellipse((x - width / 2, y - width / 2, x + width / 2, y + width / 2), fill=fill)


def spark():          # tia nhấn màu cam, xòe ra như tiếng "ồ"
    img, d = canvas()
    for angle in (-50, -20, 10):
        a = math.radians(angle)
        bar(d, 80 + 60 * math.cos(a), 220 + 60 * math.sin(a), 80 + 230 * math.cos(a), 220 + 230 * math.sin(a),
            34, "#FF9A2E")
    save(img, "spark")


def lines():          # vạch dọc màu vàng, sốc
    img, d = canvas()
    for i, h in enumerate((220, 300, 260, 180)):
        x = 70 + i * 85
        bar(d, x, 40, x, 40 + h, 30, "#FFD54A")
    save(img, "lines")


def gloom():          # vạch tím rủ xuống, buồn
    img, d = canvas()
    for i, h in enumerate((240, 320, 280, 200, 260)):
        x = 50 + i * 75
        d.line((x, 30, x, 30 + h), fill="#6E5A9E", width=16)
    save(img, "gloom")


def mark(char, colour, name):
    img, d = canvas()
    font = ImageFont.truetype(str(FONT), 330)
    d.text((S / 2, S / 2), char, font=font, anchor="mm", fill=colour, stroke_width=W, stroke_fill=INK)
    save(img, name)


def drop(colour, name):   # giọt mồ hôi / nước mắt
    img, d = canvas()
    pts = [(200 + 110 * math.sin(t) * (1 - math.cos(t)) / 2 * 1.6, 60 + 290 * (1 - math.cos(t)) / 2)
           for t in [i / 60 * 2 * math.pi for i in range(61)]]
    d.polygon(pts, fill=colour, outline=INK, width=W)
    d.ellipse((150, 230, 185, 290), fill="#FFFFFF")
    save(img, name)


def heart():
    img, d = canvas()
    pts = [(200 + 11 * 16 * math.sin(t) ** 3,
            190 - 11 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
           for t in [i / 120 * 2 * math.pi for i in range(121)]]
    d.polygon(pts, fill="#FF6F91", outline=INK, width=W)
    save(img, "heart")


def anger():          # dấu gân giận kiểu manga: bốn cung cong
    img, d = canvas()
    for cx, cy, start in ((100, 100, 0), (300, 100, 90), (300, 300, 180), (100, 300, 270)):
        box = (cx - 80, cy - 80, cx + 80, cy + 80)
        d.arc(box, start + 6, start + 84, fill=INK, width=40)
        inner = (box[0] + 10, box[1] + 10, box[2] - 10, box[3] - 10)    # Pillow vẽ độ dày vào phía trong khung
        d.arc(inner, start + 10, start + 80, fill="#F23C3C", width=20)
    save(img, "anger")


def sparkle():        # ngôi sao bốn cánh lấp lánh
    img, d = canvas()
    pts = []
    for i in range(8):
        r = 170 if i % 2 == 0 else 45
        a = math.pi / 4 * i - math.pi / 2
        pts.append((200 + r * math.cos(a), 200 + r * math.sin(a)))
    d.polygon(pts, fill="#FFE45C", outline=INK, width=W)
    save(img, "sparkle")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spark(); lines(); gloom(); heart(); anger(); sparkle()
    mark("?", "#4FA3FF", "question")
    mark("!", "#FF5A5A", "exclaim")
    drop("#8FD3FF", "sweat")
    drop("#6EC1FF", "tear")


if __name__ == "__main__":
    main()
