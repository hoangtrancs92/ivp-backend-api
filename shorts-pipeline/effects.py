"""Hiệu ứng vẽ bằng code cho từng khung hình, dùng trong build_video.py.

Một lớp hiệu ứng trong "layers":
  {"effect": "aura", "on": "father", "start": 0.2, "duration": 1.5, "colour": "#FFE680"}
  "on": id lớp nhân vật để bám theo (đi theo vị trí và độ phóng to); bỏ trống thì phủ cả khung hình.
  "colour": tùy chọn, đổi màu chính của hiệu ứng.
Thứ tự trong "layers" là thứ tự vẽ: aura, rays, gloom, speed_lines đặt TRƯỚC lớp nhân vật để nằm sau nhân vật;
sparkles, hearts, tears, confetti, rain, flash đặt SAU để nằm trước.
"""
import math
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
}
CONFETTI = ("#FF6F91", "#FFD54A", "#6EC1FF", "#7CD992", "#B18CFF", "#FF9A2E")


def rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), max(0, min(255, round(alpha)))


def fade(t, life, fade_in=0.3, fade_out=0.3):
    """Độ hiện 0..1: hiện dần lúc đầu, mờ dần lúc cuối."""
    return max(0.0, min(1.0, t / fade_in if fade_in else 1.0, (life - t) / fade_out if fade_out else 1.0))


def draw(frame, kind, t, life, box, size, colour=None, seed=0):
    """Vẽ hiệu ứng lên frame (RGB). box: (cx, cy, w, h, head_x, head_y, head_r) bằng pixel của lớp được bám,
    hoặc None nếu phủ cả khung. size: (W, H) của khung hình."""
    colour = colour or KINDS[kind][1]
    overlay = Image.new("RGBA", size)
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
