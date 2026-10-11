"""Hiệu ứng vẽ bằng code cho từng khung hình, dùng trong build_video.py.

Một lớp hiệu ứng trong "layers":
  {"effect": "aura", "on": "father", "start": 0.2, "duration": 1.5, "colour": "#FFE680"}
  "on": id lớp nhân vật để bám theo (đi theo vị trí và độ phóng to); bỏ trống thì phủ cả khung hình.
  "colour": tùy chọn, đổi màu chính của hiệu ứng.
Thứ tự trong "layers" là thứ tự vẽ: aura, rays, gloom, speed_lines đặt TRƯỚC lớp nhân vật để nằm sau nhân vật;
sparkles, hearts, tears, confetti, rain, flash và ký hiệu cảm xúc (MANPU) đặt SAU để nằm trước.
"""
import math
from pathlib import Path
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

# hiệu ứng -> (cần "on" không, màu mặc định)
KINDS = {
    "aura": (True, "#FFD84A"),        # hào quang phát sáng sau nhân vật
    "rays": (True, "#FFE07A"),        # tia sáng xoay sau nhân vật
    "sparkles": (True, "#FFF6C8"),    # ngôi sao lấp lánh quanh nhân vật
    "hearts": (True, "#FF6F91"),      # trái tim bay lên
    "tears": (True, "#7CCBFF"),       # nước mắt rơi liên tục từ mắt
    "speed_lines": (False, "#1E1E28"),  # đường tập trung kiểu manga
    "flash": (False, "#FFFFFF"),      # chớp trắng
    "gloom": (False, "#1B2240"),      # phủ tối xanh
    "confetti": (False, None),        # giấy màu rơi
    "rain": (False, "#A8C8E8"),       # mưa
    # ký hiệu cảm xúc kiểu manga (漫符), vẽ quanh đầu nhân vật
    "sweat": (True, "#9ED8F5"),       # giọt mồ hôi to cạnh đầu (lúng túng, khó xử)
    "anger": (True, "#E53935"),       # dấu gân giận 💢 nhấp nháy
    "shock_lines": (True, "#3A3F8F"), # vạch dọc trên mặt kiểu ガーン (sốc, tái mặt)
    "dizzy": (True, "#FFD54A"),       # sao xoay vòng trên đầu (choáng, rối trí)
    "idea": (True, "#FFE45C"),        # bóng đèn bật sáng trên đầu (nảy ra ý)
    "sigh": (True, "#FFFFFF"),        # làn hơi thở dài bay ra từ miệng (mệt, chán, nhẹ nhõm)
    # chữ tượng thanh nhỏ rải quanh đầu (「ニヤ」「ドキッ」「イライラ」...), "text" của lớp; bám "on" nếu có, không thì vùng
    # mặt giữa khung (tranh vẽ cả cảnh: người đã vẽ sẵn, không có lớp để bám)
    "murmur": (False, "#FF8A1E"),
}
MANPU = ("sweat", "anger", "shock_lines", "dizzy", "idea", "sigh", "murmur")   # luôn vẽ trước mặt nhân vật
OUTLINE = "#2A2A35"
CONFETTI = ("#FF6F91", "#FFD54A", "#6EC1FF", "#7CD992", "#B18CFF", "#FF9A2E")


def rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), max(0, min(255, round(alpha)))


def fade(t, life, fade_in=0.3, fade_out=0.3):
    """Độ hiện 0..1: hiện dần lúc đầu, mờ dần lúc cuối."""
    return max(0.0, min(1.0, t / fade_in if fade_in else 1.0, (life - t) / fade_out if fade_out else 1.0))


def draw(frame, kind, t, life, box, size, colour=None, seed=0, text=None):
    """Vẽ hiệu ứng lên frame (RGB). box: (cx, cy, w, h, head_x, head_y, head_r) bằng pixel của lớp được bám,
    hoặc None nếu phủ cả khung. size: (W, H) của khung hình. text: chữ của hiệu ứng "murmur"."""
    colour = colour or KINDS[kind][1]
    overlay = Image.new("RGBA", size)
    if kind == "murmur":
        _murmur(overlay, t, life, box, size, colour, seed, text or "ニヤ")
    else:
        globals()["_" + kind](overlay, t, life, box, size, colour, seed)
    frame.paste(overlay, (0, 0), overlay)


# ---------- hiệu ứng bám nhân vật ----------

@lru_cache(maxsize=16)
def _glow_sprite(w, h, colour):
    """Quầng sáng hình bầu dục, mờ dần ra ngoài."""
    pad = max(w, h) // 4
    img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad))
    d = ImageDraw.Draw(img)
    d.ellipse((pad, pad, pad + w, pad + h), fill=rgba(colour, 255))
    inner = 0.18                                        # lõi sáng trắng ở giữa cho cảm giác phát sáng
    d.ellipse((pad + w * inner, pad + h * inner, pad + w * (1 - inner), pad + h * (1 - inner)), fill=rgba("#FFFFFF", 255))
    return img.filter(ImageFilter.GaussianBlur(pad * 0.6))


def _aura(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h = box[:4]
    breathe = 0.85 + 0.15 * math.sin(2 * math.pi * 1.1 * t)
    sprite = _glow_sprite(int(w * 1.7), int(h * 1.25), colour)
    alpha = fade(t, life, 0.4, 0.4) * breathe
    sprite = sprite.copy()
    sprite.putalpha(sprite.getchannel("A").point(lambda a: round(a * alpha)))
    overlay.alpha_composite(sprite, (round(cx - sprite.width / 2), round(cy - sprite.height / 2)))


@lru_cache(maxsize=16)
def _ray_sprite(radius, colour, count=16):
    """Các tia sáng hình nan quạt, mờ dần từ tâm ra ngoài."""
    side = radius * 2
    rays = Image.new("RGBA", (side, side))
    d = ImageDraw.Draw(rays)
    for k in range(count):
        a0 = 2 * math.pi * k / count
        a1 = a0 + math.pi / count * 0.9
        d.polygon([(radius, radius), (radius + radius * math.cos(a0), radius + radius * math.sin(a0)),
                   (radius + radius * math.cos(a1), radius + radius * math.sin(a1))], fill=rgba(colour, 200))
    falloff = Image.radial_gradient("L").resize((side, side))          # 0 ở tâm, 255 ở mép
    mask = falloff.point(lambda v: max(0, round(255 - v * 1.1)))
    alpha = Image.composite(rays.getchannel("A"), Image.new("L", (side, side)), mask)
    rays.putalpha(alpha.point(lambda a: round(a * 0.85)))
    return rays.filter(ImageFilter.GaussianBlur(radius * 0.01))


def _rays(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy = box[:6]
    radius = int(max(w, h) * 0.85)
    sprite = _ray_sprite(radius, colour).rotate(18 * t, Image.BILINEAR)
    alpha = fade(t, life, 0.5, 0.4)
    sprite.putalpha(sprite.getchannel("A").point(lambda a: round(a * alpha)))
    overlay.alpha_composite(sprite, (round(hx - radius), round((hy + cy) / 2 - radius)))


def _star(d, x, y, r, fill):
    pts = []
    for i in range(8):
        rr = r if i % 2 == 0 else r * 0.28
        a = math.pi / 4 * i - math.pi / 2
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=fill)


def _sparkles(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h = box[:4]
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.2, 0.3)
    for _ in range(14):
        angle = rng.uniform(0, 2 * math.pi)
        dist = rng.uniform(0.45, 0.8)
        x = cx + math.cos(angle) * w * dist * 1.1
        y = cy + math.sin(angle) * h * dist * 0.75
        twinkle = max(0.0, math.sin(2 * math.pi * (1.4 * t + rng.random())))
        r = max(h, w) * rng.uniform(0.05, 0.09) * (0.35 + 0.65 * twinkle)
        if r > 1:
            _star(d, x, y, r, rgba(colour, 255 * base))
            _star(d, x, y, r * 0.45, rgba("#FFFFFF", 255 * base))


def _heart(d, x, y, r, fill, outline):
    pts = [(x + r * 16 * math.sin(a) ** 3 / 16,
            y - r * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16)
           for a in [i / 40 * 2 * math.pi for i in range(41)]]
    d.polygon(pts, fill=fill, outline=outline, width=max(2, round(r / 6)))


def _hearts(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h = box[:4]
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.2, 0.3)
    for k in range(7):
        phase = k / 7 + rng.uniform(-0.05, 0.05)
        p = (t / 1.8 + phase) % 1.0                                    # mỗi tim bay hết một vòng trong 1,8 giây
        x = cx + (rng.uniform(-0.6, 0.6) * w) + math.sin(2 * math.pi * (p * 1.5 + phase)) * w * 0.06
        y = cy + h * 0.25 - p * h * 0.9
        r = max(h * 0.5, w) * rng.uniform(0.06, 0.1) * (0.6 + 0.4 * p)
        a = base * min(1.0, p / 0.15, (1 - p) / 0.3) * 255
        _heart(d, x, y, r, rgba(colour, a), rgba("#7A2335", a))


def _tears(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.2, 0.2)
    for side in (-1, 1):
        x0, y0 = hx + side * hr * 0.42, hy + hr * 0.30                # dưới mắt
        for k in range(4):
            p = (t / 0.9 + k / 4 + (0.12 if side > 0 else 0)) % 1.0    # mỗi giọt rơi trong 0,9 giây
            x = x0 + side * p * hr * 0.25
            y = y0 + p * p * h * 0.45
            r = hr * 0.11 * (1 - 0.3 * p)
            a = base * min(1.0, (1 - p) / 0.3) * 230
            d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(colour, a))
            d.polygon([(x - r, y), (x + r, y), (x, y - r * 2.4)], fill=rgba(colour, a))


# ---------- hiệu ứng phủ cả khung ----------

def _speed_lines(overlay, t, life, box, size, colour, seed):
    W, H = size
    rng = random.Random(seed * 1000 + int(t * 12))                      # đổi hình 12 lần mỗi giây
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.1, 0.2)
    cx, cy = W / 2, H * 0.62
    outer = math.hypot(W, H)
    for _ in range(90):
        a = rng.uniform(0, 2 * math.pi)
        inner = rng.uniform(0.42, 0.62) * min(W, H)
        half = rng.uniform(0.004, 0.012)
        pts = [(cx + outer * math.cos(a - half), cy + outer * math.sin(a - half)),
               (cx + outer * math.cos(a + half), cy + outer * math.sin(a + half)),
               (cx + inner * math.cos(a), cy + inner * math.sin(a))]
        d.polygon(pts, fill=rgba(colour, 150 * base))


def _flash(overlay, t, life, box, size, colour, seed):
    a = max(0.0, 1 - t / 0.35) * 220
    if a > 0:
        overlay.paste(Image.new("RGBA", size, rgba(colour, a)))


@lru_cache(maxsize=4)
def _gloom_sprite(size, colour):
    W, H = size
    grad = Image.linear_gradient("L").resize((W, H)).point(lambda v: round(150 - v * 0.45))   # tối hơn ở trên
    img = Image.new("RGBA", size, rgba(colour, 0))
    img.putalpha(grad)
    return img


def _gloom(overlay, t, life, box, size, colour, seed):
    sprite = _gloom_sprite(size, colour).copy()
    alpha = fade(t, life, 0.5, 0.3)
    sprite.putalpha(sprite.getchannel("A").point(lambda a: round(a * alpha)))
    overlay.alpha_composite(sprite)


def _confetti(overlay, t, life, box, size, colour, seed):
    W, H = size
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.1, 0.4)
    for _ in range(70):
        x0, speed = rng.uniform(0, W), rng.uniform(0.25, 0.45) * H
        y = (rng.uniform(-0.3, 1.0) * H + speed * t) % (H * 1.1) - H * 0.05
        x = x0 + math.sin(t * rng.uniform(2, 4) + x0) * W * 0.02
        spin = t * rng.uniform(4, 9) + rng.uniform(0, 6)
        lw, lh = W * 0.012, W * 0.022 * abs(math.cos(spin))
        c, s = math.cos(spin * 0.6), math.sin(spin * 0.6)
        pts = [(x + dx * c - dy * s, y + dx * s + dy * c) for dx, dy in ((-lw, -lh), (lw, -lh), (lw, lh), (-lw, lh))]
        d.polygon(pts, fill=rgba(colour or rng.choice(CONFETTI), 255 * base))


def _rain(overlay, t, life, box, size, colour, seed):
    W, H = size
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    base = fade(t, life, 0.3, 0.3)
    for _ in range(110):
        x0, speed = rng.uniform(-0.1, 1.1) * W, rng.uniform(1.8, 2.6) * H
        y = (rng.uniform(0, 1) * H + speed * t) % (H * 1.2) - H * 0.1
        x = x0 - (y / H) * W * 0.08
        length = H * rng.uniform(0.03, 0.06)
        d.line((x, y, x - length * 0.15, y + length), fill=rgba(colour, 170 * base), width=3)


# ---------- ký hiệu cảm xúc (漫符): nét phẳng, viền đậm như ảnh nhân vật ----------

def _pop(t, length=0.25):
    """Cỡ khi bật ra: 0 → hơi quá 1 → 1."""
    p = min(t / length, 1.0)
    c = 1.70158
    return max(1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2, 0.0)


def _side(seed):
    return 1 if seed % 2 == 0 else -1


def _sweat(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    side = _side(seed)
    p = (t % 1.4) / 1.4                                             # trượt xuống chậm, lặp mỗi 1,4 giây
    a = fade(t, life, 0.1, 0.3) * min(1.0, (1 - p) / 0.25) * 255
    r = hr * 0.2 * _pop(t)
    x, y = hx + side * hr * 1.08, hy - hr * 0.55 + p * hr * 0.35
    if r < 1:
        return
    edge = max(2.0, r * 0.18)
    for grow, fill in ((edge, rgba(OUTLINE, a)), (0, rgba(colour, a))):
        rr = r + grow
        d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=fill)
        d.polygon([(x - rr * 0.92, y - rr * 0.4), (x + rr * 0.92, y - rr * 0.4), (x, y - rr * 2.3 - grow * 0.5)], fill=fill)
    d.ellipse((x - r * 0.5, y - r * 0.55, x - r * 0.15, y - r * 0.05), fill=rgba("#FFFFFF", a))


def _anger(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    side = -_side(seed)
    a = fade(t, life, 0.1, 0.3) * 255
    r = hr * 0.32 * _pop(t) * (1 + 0.14 * abs(math.sin(2 * math.pi * 2.2 * t)))   # nhấp nháy như mạch đập
    x, y = hx + side * hr * 0.95, hy - hr * 0.95
    if r < 2:
        return
    for qx, qy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):            # bốn góc cong của 💢, mỗi góc hướng vào tâm
        ox, oy = x + qx * r * 0.62, y + qy * r * 0.62
        facing = math.degrees(math.atan2(-qy, -qx))
        rr = r * 0.55
        for width, fill in ((r * 0.46, rgba(OUTLINE, a)), (r * 0.30, rgba(colour, a))):
            d.arc((ox - rr, oy - rr, ox + rr, oy + rr), facing - 58, facing + 58, fill=fill, width=max(2, round(width)))


def _shock_lines(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    rng = random.Random(seed)
    d = ImageDraw.Draw(overlay)
    a = fade(t, life, 0.05, 0.3) * 210
    grow = min(t / 0.4, 1.0)                                        # vạch chảy từ đỉnh đầu xuống
    top = hy - hr * 0.8
    for k in range(9):
        x = hx - hr * 0.7 + k * hr * 1.4 / 8 + rng.uniform(-0.04, 0.04) * hr
        length = hr * rng.uniform(0.75, 1.05) * grow
        d.line((x, top, x, top + length), fill=rgba(colour, a), width=max(2, round(hr * 0.045)))


def _dizzy(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    a = fade(t, life, 0.15, 0.3) * 255
    ox, oy = hx, hy - hr * 1.2
    for k in range(3):                                              # ba ngôi sao chạy vòng elip trên đầu
        angle = 2 * math.pi * (0.8 * t + k / 3)
        x, y = ox + math.cos(angle) * hr * 0.9, oy + math.sin(angle) * hr * 0.25
        r = hr * 0.2 * (0.8 + 0.2 * math.sin(angle))                # xa thì nhỏ
        _star(d, x, y, r * 1.25, rgba(OUTLINE, a))
        _star(d, x, y, r, rgba(colour, a))


def _idea(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    a = fade(t, life, 0.05, 0.3) * 255
    r = hr * 0.3 * _pop(t, 0.3)
    x, y = hx + _side(seed) * hr * 0.35, hy - hr * 1.65
    if r < 2:
        return
    edge = max(2.0, r * 0.14)
    base_top, base_w = y + r * 0.75, r * 0.5
    d.rectangle((x - base_w - edge, base_top - edge, x + base_w + edge, base_top + r * 0.55 + edge), fill=rgba(OUTLINE, a))
    d.rectangle((x - base_w, base_top, x + base_w, base_top + r * 0.55), fill=rgba("#B8BCC6", a))
    d.ellipse((x - r - edge, y - r - edge, x + r + edge, y + r + edge), fill=rgba(OUTLINE, a))
    d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(colour, a))
    d.ellipse((x - r * 0.55, y - r * 0.6, x - r * 0.15, y - r * 0.15), fill=rgba("#FFFFFF", a))
    if t > 0.2:                                                     # tia sáng nhấp nháy quanh bóng đèn
        flicker = 0.6 + 0.4 * abs(math.sin(2 * math.pi * 3 * t))
        for k in range(8):
            angle = math.pi * (k / 7) + math.pi                     # nửa trên
            r0, r1 = r * 1.35, r * (1.35 + 0.45 * flicker)
            d.line((x + math.cos(angle) * r0, y + math.sin(angle) * r0, x + math.cos(angle) * r1, y + math.sin(angle) * r1),
                   fill=rgba("#F2A500", a), width=max(2, round(r * 0.14)))


def _sigh(overlay, t, life, box, size, colour, seed):
    cx, cy, w, h, hx, hy, hr = box
    d = ImageDraw.Draw(overlay)
    side = _side(seed)
    p = (t % 2.0) / 1.4                                             # mỗi 2 giây thở ra một lần, kéo dài 1,4 giây
    if p > 1:
        return
    a = fade(t, life, 0.1, 0.3) * min(1.0, p / 0.15, (1 - p) / 0.4) * 235
    x0, y0 = hx + side * hr * 0.75, hy + hr * 0.9                   # ngoài má, ngang miệng
    for k, (dist, rr) in enumerate(((0.2, 0.13), (0.55, 0.18), (0.95, 0.24))):   # ba cụm khói to dần
        q = min(max(p * 1.6 - k * 0.2, 0.0), 1.0)
        if q <= 0:
            continue
        x = x0 + side * hr * dist * (0.6 + 0.4 * q)
        y = y0 + hr * 0.2 * dist * q
        r = hr * rr * q
        d.ellipse((x - r - 3, y - r - 3, x + r + 3, y + r + 3), fill=rgba("#9AA3B5", a))
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgba(colour, a))


FONT_FILE = str(Path(__file__).resolve().parent / "fonts" / "NotoSansCJKjp-Black.otf")


@lru_cache(maxsize=32)
def _murmur_word(text, px, colour):
    """Một chữ tượng thanh nhỏ: màu, viền trắng dày + viền tối mảnh (đọc rõ trên mọi nền)."""
    from PIL import ImageFont
    f = ImageFont.truetype(FONT_FILE, px)
    w = round(f.getlength(text)) + px
    img = Image.new("RGBA", (w, px * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((px // 2, px // 3), text, font=f, fill=rgba(OUTLINE, 255), stroke_width=max(4, px // 6) + 2, stroke_fill=rgba(OUTLINE, 255))
    d.text((px // 2, px // 3), text, font=f, fill=rgba(colour, 255), stroke_width=max(4, px // 6), stroke_fill=(255, 255, 255, 255))
    return img.crop(img.getbbox())


def _murmur(overlay, t, life, box, size, colour, seed, text):
    """5-7 chữ nhỏ nghiêng ngẫu nhiên quanh đầu, bật ra lần lượt rồi nhấp nháy nhẹ (như 「ニヤ ニヤ」 quanh mặt)."""
    W, H = size
    if box:
        _, _, _, _, hx, hy, hr = box
    else:                                   # không có lớp để bám: vùng mặt ước lượng giữa khung
        hx, hy, hr = W * 0.5, H * 0.42, W * 0.2
    rng = random.Random(seed)
    count = rng.randint(5, 7)
    a0 = fade(t, life, 0.05, 0.3)
    for k in range(count):
        # vòng quanh đầu từ má trái qua đỉnh đầu sang má phải (chừa cằm), ngoài viền mặt
        ang = math.radians(195 - k * 210 / max(count - 1, 1) + rng.uniform(-8, 8))
        dist = hr * rng.uniform(1.2, 1.55)
        x, y = hx + math.cos(ang) * dist * 1.1, hy - math.sin(ang) * dist * 0.85 + hr * 0.1
        px = max(20, round(hr * rng.uniform(0.28, 0.4)))
        word = _murmur_word(text, px, colour)
        appear = k * 0.06                                   # bật ra lần lượt
        if t < appear:
            continue
        pop = min(1.0, (t - appear) / 0.12)
        blink = 0.8 + 0.2 * math.sin(2 * math.pi * 2.4 * t + k)              # nhấp nháy nhẹ
        s = (0.6 + 0.4 * pop) * (0.95 + 0.08 * math.sin(2 * math.pi * 1.7 * t + k * 1.3))
        img = word.resize((max(1, round(word.width * s)), max(1, round(word.height * s))), Image.BILINEAR)
        img = img.rotate(rng.uniform(-25, 25), Image.BICUBIC, expand=True)
        alpha = a0 * blink * pop
        if alpha < 1:
            img.putalpha(img.getchannel("A").point(lambda v: round(v * alpha)))
        overlay.alpha_composite(img, (round(x - img.width / 2), round(y - img.height / 2)))
