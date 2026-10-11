"""Tiểu phẩm, bước cuối: dựng video kiểu "sân khấu".

  python skit/build.py skits/<tên>            # dựng output.mp4
  python skit/build.py skits/<tên> --frames   # chỉ xuất vài khung hình mẫu vào work/frames/ (xem nhanh bố cục)
  python skit/build.py skits/<tên> --lines 4,9,15   # khung hình của các câu này

Cần: skit.json, audio/*.wav + audio/timing.json (skit/voice.py), cutouts/<nhân vật>_<cảm xúc>.png, ảnh nền (skit/jobs.py).
- Sân khấu: mỗi nơi ("sets") một nền; nhân vật (và bản sao, vd 4 tiền bối) đứng thành hàng; vào / ra theo "enter" / "exit".
  Hai nơi (gọi điện): máy quay cắt qua lại theo người nói.
- Biểu cảm đổi theo "expression"; người đang nói nhún theo tiếng, người khác thở nhẹ. Dấu cảm xúc vẽ bằng code ("mark"):
  mảng tím trên mặt, mồ hôi, gân 💢, lấp lánh, sọc tái mặt.
- Máy quay theo "shot": wide / close:<id> / group:<id>,<id>; mở rộng nhóm thì lùi máy mượt, đổi hẳn góc thì lia nhòe.
- "insert": tranh chèn minh họa thay sân khấu trong câu đó, chữ ở giữa, câu liền nhau cùng tranh thì chữ chồng dần xuống.
- Chữ thoại cạnh người nói: màu theo người, cỡ theo "size", từ "emphasis" to và đỏ, hiện dần theo lời (mốc từ VOICEVOX),
  "stack" chồng lên câu trước, "glow" phát sáng; câu "silent" (chỉ dẫn sân khấu) hiện chữ, không tiếng.
  Dải tiêu đề trên cùng; nhãn "chapter" ở dưới.
Chức năng riêng: không đụng build_video.py (chỉ dùng lại hàm chỉnh âm lượng nhạc nền).
"""
import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1920, 30
GAP = 0.12                         # = skit/voice.py
FONT = str(ROOT / "fonts" / "NotoSansCJKjp-Black.otf")
BAND = 360                         # dải đen tiêu đề
TITLE_TOP = 70                     # thanh trên cùng của TikTok che mép trên
SIZE_PX = {"small": 58, "normal": 76, "big": 100, "shout": 132}
SHOUT_RED, EMPH_RED = (229, 57, 53), (229, 40, 40)
GLOOM = (120, 40, 170)             # tím: mảng mặt "gloom" và chữ glow của câu dọa
STAGE_H = {1: 0.74, 2: 0.66, 3: 0.58, 4: 0.5, 5: 0.46, 6: 0.42, 7: 0.38, 8: 0.36, 9: 0.34, 10: 0.32}   # chiều cao mỗi người theo số người trên sân khấu
WHIP = 0.14                        # giây lia nhòe khi đổi hẳn góc máy
EASE = 0.35                        # giây lùi / đẩy máy mượt
SLOTS = {"left": 0, "center": 1, "right": 2}
MOUTH_FLAP = 3                     # khung hình mỗi nhịp mở / khép miệng khi nói (30 fps: ~5 lần mở mỗi giây)
SFX_BELOW = 9                      # dB: tiếng hiệu ứng nhỏ hơn giọng nhân vật (đo độ to cả hai)
MUSIC_BELOW = 27                   # dB: nhạc nền nhỏ hơn giọng nhiều (truyện kể dùng 21)
HOP = 0.28                         # giây nảy lên khi đổi biểu cảm / tư thế


def font(size):
    return ImageFont.truetype(FONT, size)


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 3


def hex_rgb(colour):
    colour = colour.lstrip("#")
    return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))


def cover(img):
    """Phóng / cắt ảnh cho kín khung dọc W x H."""
    img = img.convert("RGB")
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


# ---------- dữ liệu ----------

def load(folder):
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    timing = json.loads((folder / "audio" / "timing.json").read_text(encoding="utf-8"))["lines"]
    starts, clock = [], 0.0
    for t in timing:
        starts.append(clock)
        clock += t["seconds"] + GAP
    return skit, timing, starts, clock


def envelope(path, frames_per_sec=FPS):
    """Độ to giọng theo từng khung hình (0-1) của một file wav: để người nói nhún theo tiếng."""
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        rate = w.getframerate()
    step = rate // frames_per_sec
    rms = np.array([np.sqrt(np.mean(x[i:i + step] ** 2)) for i in range(0, len(x), step)] or [0.0])
    return rms / (rms.max() or 1)


# ---------- sân khấu ----------

# Chiều cao tương đối so với người lớn (cast "height"); thiếu thì đoán theo mô tả ngoại hình.
HEIGHT_WORDS = (("kitten", 0.25), ("cat", 0.32), ("puppy", 0.35), ("hamster", 0.15), ("rabbit", 0.3), ("bird", 0.25),
                ("dog", 0.45), ("retriever", 0.55), ("shiba", 0.4), ("corgi", 0.35), ("poodle", 0.4), ("baby", 0.35), ("toddler", 0.5), ("child", 0.7), ("kid", 0.7), ("boy", 0.8), ("girl", 0.8))


def rel_height(c):
    if isinstance(c.get("height"), (int, float)) and 0.1 <= c["height"] <= 1.5:
        return float(c["height"])
    look = f" {c.get('look', '')} ".lower()
    return next((h for w, h in HEIGHT_WORDS if f" {w}" in look), 1.0)


def load_raw(folder, cast):
    """Ảnh gốc (chưa thu phóng) mọi biến thể của mọi nhân vật: (nhân vật, "normal" | "<cảm xúc>" | "pose_<tư thế>"[_talk])."""
    raw = {}
    for n in cast:
        if not (folder / "cutouts" / f"{n}_normal.png").exists():
            sys.exit(f"Thiếu ảnh cutouts/{n}_normal.png")
        for path in folder.glob(f"cutouts/{n}_*.png"):
            raw[(n, path.stem[len(n) + 1:])] = Image.open(path).convert("RGBA")
    return raw


class View:
    """Một khung hình: nền + nhân vật đặt theo (tâm x, chân y, chiều cao ảnh gốc) pixel màn hình."""

    def __init__(self, bg, raw, place):
        self.bg, self.raw, self.cache = bg, raw, {}
        self.instances = sorted(place, key=lambda inst: place[inst][1])          # xa (chân cao hơn) vẽ trước
        self.x = {inst: p[0] for inst, p in place.items()}
        self.feet = {inst: p[1] for inst, p in place.items()}
        self.scale = {}
        for (n, k), p in place.items():                                         # mọi ảnh một nhân vật cùng tỉ lệ ảnh gốc
            self.scale[n] = p[2] / raw[(n, "normal")].height

    def image(self, name, expr, pose=None, talk=False):
        """Ảnh đang dùng: tư thế khác (nếu có) hoặc biểu cảm; đang mở miệng thì bản _talk (không có thì ảnh khép miệng)."""
        keys = [f"pose_{pose}"] if pose and (name, f"pose_{pose}") in self.raw else [expr, "normal"]
        key = next((k for k in keys if (name, k) in self.raw), "normal")
        if talk and (name, f"{key}_talk") in self.raw:
            key = f"{key}_talk"
        if (name, key) not in self.cache:
            img, sc = self.raw[(name, key)], self.scale[name]
            self.cache[(name, key)] = img.resize((max(1, round(img.width * sc)), max(1, round(img.height * sc))), Image.LANCZOS)
        return self.cache[(name, key)]

    def box(self, name, k=0, expr="normal", pose=None):
        """Khung (trái, trên, phải, dưới) pixel của một bản sao."""
        img = self.image(name, expr, pose)
        x, feet = self.x[(name, k)], self.feet[(name, k)]
        return x - img.width / 2, feet - img.height, x + img.width / 2, feet


def stage_view(skit, raw, key):
    """Toàn cảnh một nơi. Có dàn cảnh (skit["blocking"][nơi], skit/stage.py: AI xem ảnh nền chỉ chỗ đứng / ngồi từng vai) thì
    đặt theo đó; không có thì xếp hàng dưới đáy khung, chiều cao theo tỉ lệ thật (mèo, chó nhỏ hơn người)."""
    backgrounds = skit.get("backgrounds") or {key: skit["background"]}
    bg = cover(Image.open(ROOT / "library" / "backgrounds" / f"{backgrounds[key]}.png"))
    cast = skit["cast"]
    first = next(iter(backgrounds))
    members = [n for n in cast if (cast[n].get("set") or first) == key or len(backgrounds) == 1]   # thiếu nơi: nơi chính
    order = sorted(members, key=lambda n: (SLOTS.get(cast[n].get("slot"), 1), list(cast).index(n)))
    blocking = (skit.get("blocking") or {}).get(key) or {}
    instances = [(n, k) for n in order for k in range(cast[n]["copies"])]
    count = max(len(instances), 1)
    top = max(rel_height(cast[n]) for n in members) if members else 1.0
    base = STAGE_H.get(count, 0.3) * H
    margin = 0.5 / count
    place = {}
    for i, (n, k) in enumerate(instances):
        h = base * rel_height(cast[n]) / top
        x = (margin + i * (1 - 2 * margin) / max(count - 1, 1)) * W if count > 1 else W / 2
        feet = H - 20
        b = blocking.get(n)
        if isinstance(b, dict) and all(isinstance(b.get(v), (int, float)) for v in ("x", "y", "h")):
            h = min(max(b["h"], 0.05), 0.95) * H
            width = h * raw[(n, "normal")].width / raw[(n, "normal")].height
            x = min(max(b["x"], 0.0), 1.0) * W + (k - (cast[n]["copies"] - 1) / 2) * width * 0.75   # bản sao đứng cạnh nhau
            feet = min(max(b["y"], 0.3), 1.05) * H
        place[(n, k)] = (x, feet, h)
    return View(bg, raw, place)


def cut_view(stage, skit, insts, cache):
    """Khung cận / nhóm dựng riêng (như video mẫu): chỉ những người được nhắc, vẽ từ ảnh gốc (nét), đặt lớn giữa khung, trên
    nền phóng gần quanh chỗ họ đứng ở toàn cảnh, làm mờ nhẹ cho nổi người. Chiều cao giữ tỉ lệ thật giữa những người trong khung."""
    key = (id(stage), tuple(insts))
    if key in cache:
        return cache[key]
    cast, raw = skit["cast"], stage.raw
    cx = sum(stage.x[i] for i in insts) / len(insts)
    floor = sum(stage.feet[i] for i in insts) / len(insts)
    z = 1.8 if len(insts) == 1 else 1.4
    w, h = W / z, H / z
    bx = min(max(cx, w / 2), W - w / 2)
    by = min(max(floor - h * 0.62, h / 2), H - h / 2)
    bg = stage.bg.resize((W, H), Image.BICUBIC, box=(bx - w / 2, by - h / 2, bx + w / 2, by + h / 2))
    bg = bg.filter(ImageFilter.GaussianBlur(3))
    top = max(rel_height(cast[n]) for n, _ in insts)
    room = H - BAND                                         # phần khung dưới dải tiêu đề
    place = {}
    for i, (n, k) in enumerate(insts):
        img = raw[(n, "normal")]
        tall = img.height > 1.6 * img.width                  # ảnh đứng cả người: cắt ngang hông; ảnh thấp (thú, ngồi): thấy cả người
        rel = rel_height(cast[n]) / top
        if len(insts) == 1:
            ht = room * (1.5 if tall else 0.7)
        else:
            ht = room * (1.15 if tall else 0.6) * max(rel, 0.45)
        ht = min(ht, W * (0.92 if len(insts) == 1 else 0.98 / len(insts)) * img.height / img.width)   # không tràn ngang khung
        feet = (BAND + 170 + ht) if tall else H - 60        # đầu cách dải tiêu đề một khoảng cho chữ thoại
        if len(insts) > 1:
            feet = max(feet, H - 60)
        x = W * (i + 0.5) / len(insts)
        place[(n, k)] = (x, feet, ht)
    view = View(bg, raw, place)
    cache[key] = view
    return view


def face(box):
    """(tâm x, tâm y, bề ngang) ước lượng của mặt trong khung nhân vật: ảnh dài (cả người) thì đầu ~1/5 trên cùng,
    ảnh nửa người thì đầu lớn hơn."""
    l, t, r, b = box
    w, h = r - l, b - t
    head = h * (0.2 if h > 1.9 * w else 0.34)
    return (l + r) / 2, t + head * 0.58, min(w * 0.55, head * 0.95)


def draw_mark(img, box, mark, t):
    """Dấu cảm xúc vẽ thêm lên sân khấu (tọa độ sân khấu nên đi theo máy quay)."""
    cx, cy, fw = face(box)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if mark == "gloom":                                   # mảng tím trên nửa trên mặt: cười mà đáng sợ
        d.ellipse((cx - fw * 0.4, cy - fw * 0.22, cx + fw * 0.4, cy + fw * 0.22), fill=(*GLOOM, 140))   # quanh mắt, mũi
        layer = layer.filter(ImageFilter.GaussianBlur(fw * 0.08))
    elif mark == "sweat":                                 # giọt mồ hôi cạnh trán, nhích xuống
        x, y, s = cx + fw * 0.55, cy - fw * 0.45 + 8 * math.sin(t * 5), fw * 0.16
        d.polygon([(x, y - s * 1.6), (x - s * 0.8, y + s * 0.2), (x + s * 0.8, y + s * 0.2)], fill=(120, 200, 255, 235))
        d.ellipse((x - s * 0.8, y - s * 0.6, x + s * 0.8, y + s), fill=(120, 200, 255, 235), outline=(40, 90, 160, 255),
                  width=max(2, round(s * 0.12)))
    elif mark == "anger":                                 # gân 💢 trên trán, đập theo nhịp
        x, y = cx + fw * 0.42, cy - fw * 0.62
        s = fw * 0.2 * (1 + 0.12 * abs(math.sin(t * 7)))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            a0 = {(-1, -1): 0, (1, -1): 90, (-1, 1): 270, (1, 1): 180}[(dx, dy)]
            d.arc((x + dx * s * 0.9 - s * 0.7, y + dy * s * 0.9 - s * 0.7, x + dx * s * 0.9 + s * 0.7,
                   y + dy * s * 0.9 + s * 0.7), a0, a0 + 90, fill=(225, 35, 35, 255), width=max(4, round(s * 0.28)))
    elif mark == "sparkle":                               # ngôi sao lấp lánh quanh đầu
        for k, (ox, oy) in enumerate(((-0.75, -0.7), (0.8, -0.45), (0.65, 0.35))):
            s = fw * 0.13 * (0.6 + 0.4 * abs(math.sin(t * 4 + k * 2)))
            x, y = cx + ox * fw, cy + oy * fw
            d.polygon([(x, y - s * 2), (x + s * 0.45, y - s * 0.45), (x + s * 2, y), (x + s * 0.45, y + s * 0.45),
                       (x, y + s * 2), (x - s * 0.45, y + s * 0.45), (x - s * 2, y), (x - s * 0.45, y - s * 0.45)],
                      fill=(255, 220, 60, 240))
    elif mark == "shock":                                 # sọc xanh tím trên trán (tái mặt)
        for k in range(5):
            x = cx - fw * 0.32 + k * fw * 0.16
            for j in range(12):                           # sọc nhạt dần xuống dưới
                y0 = cy - fw * 0.55 + j * fw * 0.04
                d.line((x, y0, x, y0 + fw * 0.04), fill=(70, 60, 160, round(200 * (1 - j / 12))), width=max(3, round(fw * 0.035)))
    img.alpha_composite(layer)


# ---------- máy quay ----------

def shot_people(stage, shot, present, speaker=None):
    """Những bản sao trong khung cận / nhóm (None = toàn cảnh). Cận một nhóm bản sao: đúng bản sao đang nói."""
    if shot.startswith("close:"):
        name = shot[6:].strip()
        if speaker and speaker[0] == name and speaker in present and speaker in stage.x:
            return [speaker]
        found = [(n, k) for (n, k) in stage.instances if n == name and (n, k) in present][:1]
        return found or None
    if shot.startswith("group:"):
        names = [v.strip() for v in shot[6:].split(",")]
        found = sorted(((n, k) for (n, k) in stage.instances if n in names and (n, k) in present), key=lambda i: stage.x[i])
        if speaker in found or len(found) <= 3:
            return found[:3] or None
        return found[:2] + [speaker] if speaker in stage.x else found[:3]
    return None


def camera_of(box):
    """(tâm x, tâm y, zoom) để khung vừa box trong phần dưới dải tiêu đề, giữ tỉ lệ dọc 9:16, không ra ngoài sân khấu."""
    l, t, r, b = box
    if (l, t, r, b) == (0, 0, W, H):
        return W / 2, H / 2, 1.0
    z = max(1.0, min(W / max(r - l, 1), (H - BAND) / max(b - t, 1), 3.2))
    cx, cy = (l + r) / 2, (t + b) / 2 - BAND / 2 / z
    w, h = W / z, H / z
    cx = min(max(cx, w / 2), W - w / 2)
    cy = min(max(cy, h / 2), H - h / 2)
    return cx, cy, z


def contains(outer, inner):
    return outer[0] <= inner[0] + 5 and outer[1] <= inner[1] + 5 and outer[2] >= inner[2] - 5 and outer[3] >= inner[3] - 5


def crop(frame, cam):
    cx, cy, z = cam
    w, h = W / z, H / z
    return frame.resize((W, H), Image.BICUBIC if z > 1.01 else Image.BILINEAR,
                        box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))


# ---------- chữ ----------

def segments(text, emphasis):
    """Chia câu thành [(đoạn, có nhấn không)] theo các từ nhấn."""
    out, i = [], 0
    while i < len(text):
        hit = next((w for w in emphasis if w and text.startswith(w, i)), None)
        if hit:
            out.append((hit, True))
            i += len(hit)
        else:
            if out and not out[-1][1]:
                out[-1] = (out[-1][0] + text[i], False)
            else:
                out.append((text[i], False))
            i += 1
    return out


def text_block(line, colour, visible, max_w=W - 140):
    """Ảnh RGBA của câu thoại (đã hiện `visible` ký tự): chữ màu viền trắng dày + viền tối mảnh, từ nhấn to đỏ, xuống dòng
    khi quá bề ngang. Câu shout: đỏ khổng lồ. Câu glow: quầng sáng màu quanh chữ. Câu silent: chữ trắng viền tối, nhỏ."""
    size = SIZE_PX[line["size"]] if not line.get("silent") or line.get("blackout") else SIZE_PX["small"]
    shout = line["size"] == "shout" and not line.get("silent")
    base = (255, 255, 255) if line.get("silent") else SHOUT_RED if shout else colour
    chars = []
    for seg, emph in segments(line["text"].replace("\n", ""), line.get("emphasis") or []):
        for ch in seg:
            chars.append((ch, round(size * (1.35 if emph and not shout else 1.0)), EMPH_RED if emph else base))
    full = sum(font(s).getlength(ch) for ch, s, _ in chars)
    if full > max_w:                                     # chia dòng đều nhau (không để dòng cuối lẻ 1-2 chữ), theo cả câu
        max_w = min(max_w, full / math.ceil(full / max_w) * 1.08 + 40)
    chars = chars[:max(1, visible)]
    rows, row, width = [], [], 0
    for ch, s, c in chars:
        w = font(s).getlength(ch)
        if row and width + w > max_w:
            rows.append(row)
            row, width = [], 0
        row.append((ch, s, c, w))
        width += w
    rows.append(row)
    max_w = round(max_w)
    glow = 26 if line.get("glow") else 0
    pad = max(s for _, s, _ in chars) // 6 + 6 + glow
    heights = [max(s for _, s, _, _ in r) for r in rows]
    img = Image.new("RGBA", (max_w + 2 * pad, sum(round(h * 1.18) for h in heights) + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    light = line.get("silent") or line.get("glow")
    y = pad
    for r, rh in zip(rows, heights):
        x = pad + (max_w - sum(w for *_, w in r)) / 2
        for ch, s, c, w in r:
            f = font(s)
            stroke = max(4, s // 7)
            if light:                                    # chữ sáng viền tối (như phụ đề chỉ dẫn / câu phát sáng)
                d.text((x, y + rh - s), ch, font=f, fill=(255, 255, 255) if line.get("silent") else c,
                       stroke_width=stroke, stroke_fill=(30, 20, 40))
            else:
                d.text((x, y + rh - s), ch, font=f, fill=(40, 30, 30), stroke_width=stroke + 3, stroke_fill=(40, 30, 30))
                d.text((x, y + rh - s), ch, font=f, fill=c, stroke_width=stroke, stroke_fill=(255, 255, 255))
            x += w
        y += round(rh * 1.18)
    if glow:                                             # quầng sáng: bóng chữ phóng to, nhòe, màu tím / màu người nói
        halo_colour = GLOOM if sum(colour) < 400 or colour == GLOOM else colour
        mask = img.getchannel("A").filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(glow / 2))
        halo = Image.new("RGBA", img.size, (*halo_colour, 0))
        halo.putalpha(mask.point(lambda a: min(255, a * 2)))
        img = Image.alpha_composite(halo, img)
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def revealed(timing, local):
    """Số phần chữ đã đọc tới giây `local` của câu (0-1), nội suy theo mốc từng cụm của VOICEVOX."""
    pts = timing["reveal"]
    if local >= pts[-1][0]:
        return 1.0
    for (t0, f0), (t1, f1) in zip(pts, pts[1:]):
        if local < t1:
            return f0 + (f1 - f0) * max(local - t0, 0) / max(t1 - t0, 1e-3)
    return 1.0


def title_band(skit):
    """Dải đen tiêu đề 2 dòng chữ vàng viền nâu, thấp xuống tránh thanh TikTok."""
    band = Image.new("RGBA", (W, BAND), (0, 0, 0, 255))
    d = ImageDraw.Draw(band)
    lines = [str(t) for t in skit.get("title", []) if str(t).strip()][:2]
    y = TITLE_TOP + 10
    for k, text in enumerate(lines):
        size = 120 if k == 0 else 96
        while size > 40 and font(size).getlength(text) > W - 200:
            size -= 4
        f = font(size)
        x = (W - f.getlength(text)) / 2
        d.text((x, y), text, font=f, fill=(255, 207, 66), stroke_width=max(6, size // 10), stroke_fill=(48, 28, 14))
        y += round(size * 1.2)
    return band


def chapter_band(text):
    f = font(70)
    while f.size > 36 and f.getlength(text) > W - 120:
        f = font(f.size - 4)
    band = Image.new("RGBA", (W, 150), (20, 14, 10, 200))
    d = ImageDraw.Draw(band)
    d.text(((W - f.getlength(text)) / 2, (150 - f.size) / 2 - 8), text, font=f, fill=(255, 255, 255),
           stroke_width=5, stroke_fill=(0, 0, 0))
    return band


# ---------- kỹ xảo dựng ("fx" từng câu, "grade" cả video, "bigword") ----------

_fx_cache = {}


def cached(key, make):
    if key not in _fx_cache:
        _fx_cache[key] = make()
    return _fx_cache[key]


def gloom_layer():
    """Nền ガーン: phủ xanh tím + sọc dọc nhạt dần xuống (dán lên nền, sau lưng nhân vật)."""
    layer = Image.new("RGBA", (W, H), (40, 30, 90, 150))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(3)
    for _ in range(46):
        x, length = rnd.randrange(W), rnd.uniform(0.35, 0.8) * H
        for j in range(20):
            y0 = j * length / 20
            d.line((x, y0, x, y0 + length / 20), fill=(20, 15, 60, round(220 * (1 - j / 20))), width=rnd.choice((3, 5, 8)))
    return layer


def sparkle_layer(t):
    """Nền lấp lánh hồng (tự mãn, mơ mộng): phủ hồng nhạt + sao nhấp nháy."""
    layer = Image.new("RGBA", (W, H), (255, 190, 220, 120))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(7)
    for k in range(40):
        x, y, s = rnd.randrange(W), rnd.randrange(BAND, H), rnd.uniform(10, 30) * (0.5 + 0.5 * abs(math.sin(t * 3 + k)))
        d.polygon([(x, y - s), (x + s * 0.25, y - s * 0.25), (x + s, y), (x + s * 0.25, y + s * 0.25), (x, y + s),
                   (x - s * 0.25, y + s * 0.25), (x - s, y), (x - s * 0.25, y - s * 0.25)], fill=(255, 255, 255, 230))
    return layer


def speed_layer(t):
    """Nền vệt tốc độ ngang chạy qua (lao đi, vội vàng)."""
    layer = Image.new("RGBA", (W, H), (235, 240, 250, 170))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(11)
    for _ in range(60):
        y, length, speed = rnd.randrange(H), rnd.uniform(150, 600), rnd.uniform(1500, 3000)
        x = (rnd.uniform(0, W + length) - t * speed) % (W + length) - length
        d.line((x, y, x + length, y), fill=(120, 130, 150, 200), width=rnd.choice((2, 4, 6)))
    return layer


def focus_layer(cx, cy, variant):
    """Đường tập trung kiểu manga quanh (cx, cy) màn hình; 3 biến thể đổi luân phiên cho rung rinh."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rnd = random.Random(variant)
    for _ in range(110):
        a = rnd.uniform(0, 2 * math.pi)
        r0, w = rnd.uniform(0.33, 0.45) * W, rnd.uniform(0.006, 0.02)
        far = 1.5 * H
        d.polygon([(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                   (cx + math.cos(a - w) * far, cy + math.sin(a - w) * far),
                   (cx + math.cos(a + w) * far, cy + math.sin(a + w) * far)], fill=(20, 20, 20, 235))
    return layer


def spotlight_layer(cx, cy, radius):
    """Tối xung quanh, sáng tròn quanh (cx, cy) tọa độ sân khấu."""
    mask = Image.new("L", (W // 4, H // 4), 210)
    ImageDraw.Draw(mask).ellipse(((cx - radius) / 4, (cy - radius * 1.5) / 4, (cx + radius) / 4, (cy + radius * 1.2) / 4), fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR)
    layer = Image.new("RGBA", (W, H), (5, 5, 15, 0))
    layer.putalpha(mask)
    return layer


GRADE_MIX = 0.4    # tông màu cả video chỉ phủ 40% (100% làm mặt nhân vật lem màu, skit-006 noir)
GRADES = {   # ma trận màu RGB (Image.convert) cho "grade" cả video
    "noir": (0.36, 0.6, 0.12, -20, 0.36, 0.6, 0.12, -20, 0.36, 0.6, 0.12, -20),
    "retro": (0.39, 0.77, 0.19, 0, 0.35, 0.69, 0.17, 0, 0.27, 0.53, 0.13, 0),
    "warm": (1.08, 0.04, 0, 6, 0, 1.0, 0, 2, 0, 0, 0.88, 0),
    "cool": (0.92, 0, 0, 0, 0, 1.0, 0.03, 0, 0, 0.04, 1.1, 8),
    "night": (0.62, 0, 0, 0, 0, 0.7, 0.05, 0, 0, 0.08, 0.95, 14),
}


def grade(view, name, t):
    if name not in GRADES:
        return view
    base = view.convert("RGB")
    out = base.convert("RGB", GRADES[name])
    if name == "noir":
        out = out.point(lambda v: max(0, min(255, round((v - 128) * 1.35 + 128))))
    out = Image.blend(base, out, GRADE_MIX)                 # phủ nhẹ: giữ màu gốc của nét Irasutoya
    if name == "retro":                                     # hạt phim đổi theo khung
        grain = cached(("grain", int(t * 12) % 4), lambda: Image.effect_noise((W // 2, H // 2), 28).resize((W, H)))
        out = Image.blend(out, Image.merge("RGB", (grain, grain, grain)), 0.08)
    return out.convert("RGBA")


def bigword_block(text):
    """Chữ tượng thanh khổng lồ: vàng viền đỏ sẫm dày, xoay chéo."""
    size = 190 if len(text) <= 4 else 150 if len(text) <= 6 else 115
    f = font(size)
    img = Image.new("RGBA", (round(f.getlength(text)) + 80, size + 100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((40, 30), text, font=f, fill=(40, 10, 10), stroke_width=size // 6 + 6, stroke_fill=(40, 10, 10))
    d.text((40, 30), text, font=f, fill=(255, 226, 60), stroke_width=size // 9, stroke_fill=(200, 30, 30))
    return img.rotate(9, Image.BICUBIC, expand=True)


# ---------- dựng ----------

def plan(skit, stages, inserts):
    """Theo từng câu: nơi, ai có mặt, biểu cảm + dấu cảm xúc từng người, người nói (bản sao nào), góc máy, tranh chèn,
    chồng chữ."""
    cast = skit["cast"]
    home = {n: (cast[n].get("set") if cast[n].get("set") in stages else next(iter(stages))) for n in cast}
    entering = {l["enter"] for l in skit["lines"] if l.get("enter") in cast}
    present = {(n, k) for n in cast if n not in entering for k in range(cast[n]["copies"])}
    expr, marks, poses = {n: "normal" for n in cast}, {}, {}
    turns, steps, stack = {n: 0 for n in cast}, [], []
    for i, line in enumerate(skit["lines"]):
        if line.get("enter") in cast:
            present |= {(line["enter"], k) for k in range(cast[line["enter"]]["copies"])}
        expr.update(line.get("expression") or {})
        for n, q in (line.get("pose") or {}).items():
            if q == "default":
                poses.pop(n, None)
            else:
                poses[n] = q
        for n, m in (line.get("mark") or {}).items():
            if m == "none":
                marks.pop(n, None)
            else:
                marks[n] = m
        speaker = line["speaker"]
        k = turns[speaker] % cast[speaker]["copies"]          # nhóm bản sao: lần lượt từng người nói
        turns[speaker] += 1
        shot = line.get("shot") or "wide"
        target = shot.split(":", 1)[1].split(",")[0].strip() if ":" in shot else speaker
        where = home.get(target, home[speaker])
        insert = inserts.get(line.get("insert") or "")
        prev = steps[-1] if steps else None
        same_view = prev and prev["insert"] is insert and prev["set"] == where
        stack = (stack + [i])[-(6 if insert else 4):] if (line.get("stack") or (insert and prev and prev["insert"] is insert)) \
            and same_view else [i]
        steps.append({"set": where, "present": set(present), "expr": dict(expr), "marks": dict(marks), "pose": dict(poses),
                      "speaker": (speaker, k), "insert": insert, "stack": list(stack),
                      "people": shot_people(stages[where], shot, present, (speaker, k)),
                      "exit": line.get("exit") if line.get("exit") in cast else None})
        if line.get("exit") in cast:
            present -= {(line["exit"], k) for k in range(cast[line["exit"]]["copies"])}
    return steps


def render(folder, frames_only=False):
    skit, timing, starts, total = load(folder)
    keys = list(skit.get("backgrounds") or {"main": skit["background"]})
    raw = load_raw(folder, skit["cast"])
    stages = {key: stage_view(skit, raw, key) for key in keys}
    cuts = {}
    library = ROOT / "library" / "backgrounds"
    inserts = {text: cover(Image.open(library / f"{name}.png")) for text, name in (skit.get("inserts") or {}).items()
               if (library / f"{name}.png").exists()}
    steps = plan(skit, stages, inserts)
    # toàn cảnh có người vẽ sẵn trong bối cảnh (skit/jobs.py: skit["scenes"], câu góc rộng ghi "scene"): dùng thay cho ghép ảnh cắt
    scene_images = {name: cover(Image.open(library / f"{name}.png")) for name in (skit.get("scenes") or {})
                    if (library / f"{name}.png").exists()}
    for st, line in zip(steps, skit["lines"]):
        st["scene"] = scene_images.get(line.get("scene") or "") if not st["people"] and st["insert"] is None else None
    envs = [envelope(folder / "audio" / t["wav"]) for t in timing]
    band = title_band(skit)
    colours = {n: hex_rgb(c["colour"]) for n, c in skit["cast"].items()}
    chapters, current = [], None
    for line in skit["lines"]:
        current = line.get("chapter") or current
        chapters.append(current)
    for st in steps:                                     # khung nhìn từng câu: toàn cảnh, hoặc khung cận / nhóm dựng riêng
        st["view"] = cut_view(stages[st["set"]], skit, st["people"], cuts) if st["people"] else stages[st["set"]]
    block_cache = {}

    def block(i, visible, max_w=W - 140):
        key = (i, visible, max_w)
        if key not in block_cache:
            block_cache[key] = text_block(skit["lines"][i], colours[skit["lines"][i]["speaker"]], visible, max_w)
        return block_cache[key]

    def visible_chars(j, i, local):
        line = skit["lines"][j]
        frac = revealed(timing[j], local) if j == i else 1.0
        return math.ceil(len(line["text"].replace("\n", "")) * frac)

    def scene_frame(i, local):
        """Toàn cảnh vẽ sẵn: phóng rất chậm trong câu (đổi ảnh / vào từ khung khác thì bật vào nhẹ); chữ thoại phía trên,
        câu "stack" chồng từ trên xuống. Nhân vật không chuyển động: nhịp do chữ, tiếng, kỹ xảo và các khung cận xen kẽ."""
        step = steps[i]
        prev = steps[i - 1] if i else None
        fresh = not prev or prev.get("scene") is not step["scene"]
        z = 1.0 + 0.03 * min(local / max(timing[i]["seconds"], 0.5), 1.0)
        if fresh and local < 0.18:
            z += 0.05 * (1 - ease(local / 0.18))
        view = crop(step["scene"], (W / 2, H / 2, z)).convert("RGBA")
        y = BAND + 60
        for j in step["stack"]:
            blk = block(j, visible_chars(j, i, local), W - 160)
            if y + blk.height > H * 0.5:
                break
            view.alpha_composite(blk, (round((W - blk.width) / 2), round(y)))
            y += blk.height + 12
        return view

    def insert_frame(i, local):
        """Tranh chèn: phóng chậm (đếm từ câu đầu của chuỗi cùng tranh), bật vào nhẹ; chữ chồng từ trên xuống ở giữa."""
        step = steps[i]
        first = i
        while first and steps[first - 1]["insert"] is step["insert"]:
            first -= 1
        since = starts[i] + local - starts[first]
        z = 1.0 + 0.02 * since + (0.06 * (1 - ease(since / 0.18)) if since < 0.18 else 0)
        view = crop(step["insert"], (W / 2, H / 2, z)).convert("RGBA")
        y = BAND + 90
        for j in step["stack"]:
            blk = block(j, visible_chars(j, i, local), W - 180)
            if y + blk.height > H - 260:
                break
            view.alpha_composite(blk, (round((W - blk.width) / 2), round(y)))
            y += blk.height + 14
        return view

    def blackout_frame(i, local):
        """Màn đen chữ trắng giữa khung (chuyển thời gian, câu im lặng)."""
        view = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        line = dict(skit["lines"][i], silent=True, blackout=True, size="big", emphasis=[])
        blk = text_block(line, (255, 255, 255), visible_chars(i, i, local))
        view.alpha_composite(blk, (round((W - blk.width) / 2), round((H + BAND - blk.height) / 2)))
        return view

    def split_frame(i, local, t):
        """Chia đôi: nơi của người nói ở dưới, nơi kia ở trên (gọi điện)."""
        step = steps[i]
        other = next((key for key in stages if key != step["set"]), step["set"])
        top = stage_frame(i, local, t, where=other, text=False)
        bottom = stage_frame(i, local, t)
        view = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        half = (H - BAND) // 2
        # mỗi nửa lấy phần ngay dưới dải tiêu đề: đầu nhân vật nằm ở đó cả ở toàn cảnh lẫn khung cận (lấy dải giữa thì mất đầu)
        view.paste(top.crop((0, BAND, W, BAND + half)), (0, BAND))
        view.paste(bottom.crop((0, BAND, W, BAND + half)), (0, BAND + half))
        ImageDraw.Draw(view).rectangle((0, BAND + half - 5, W, BAND + half + 5), fill=(255, 255, 255, 255))
        return view

    def frame_at(t):
        i = max(k for k, s in enumerate(starts) if s <= t + 1e-6)
        local = t - starts[i]
        step = steps[i]
        fx = skit["lines"][i].get("fx") or []
        if "blackout" in fx:
            view = blackout_frame(i, local)
        elif step["insert"] is not None:
            view = insert_frame(i, local)
        elif step.get("scene") is not None and "split" not in fx:
            view = scene_frame(i, local)
        elif "split" in fx and len(stages) > 1:
            view = split_frame(i, local, t)
        else:
            view = stage_frame(i, local, t)
        view = post_fx(i, local, view)
        view = grade(view, skit.get("grade"), t)
        if chapters[i]:
            view.alpha_composite(chapter_band(chapters[i]), (0, H - 230))
        view.alpha_composite(band, (0, 0))
        return view.convert("RGB")

    def post_fx(i, local, view):
        """Kỹ xảo trên cả khung: rung, lóe trắng, âm bản, chữ tượng thanh."""
        line = skit["lines"][i]
        fx = line.get("fx") or []
        if "shake" in fx and local < 0.55:
            fall = 1 - local / 0.55
            rnd = random.Random(int(local * FPS) + i)
            view = view.transform(view.size, Image.AFFINE, (1, 0, rnd.uniform(-22, 22) * fall, 0, 1, rnd.uniform(-16, 16) * fall))
        if "flash" in fx and local < 0.22:
            view = Image.blend(view, Image.new("RGBA", view.size, (255, 255, 255, 255)), 0.9 * (1 - local / 0.22))
        if "invert" in fx and int(local * FPS) in (0, 1, 4):
            view = ImageOps.invert(view.convert("RGB")).convert("RGBA")
        if line.get("bigword"):
            blk = cached(("bigword", line["bigword"]), lambda: bigword_block(line["bigword"]))
            p = local / 0.15
            s = 1.6 - 0.6 * ease(p) if p < 1 else 1.0 + 0.02 * math.sin(local * 12)
            out_fade = min(1.0, max(0.0, (timing[i]["seconds"] + GAP - local) / 0.2))
            pic = blk.resize((round(blk.width * s), round(blk.height * s)), Image.BILINEAR)
            if out_fade < 1:
                pic.putalpha(pic.getchannel("A").point(lambda a: round(a * out_fade)))
            x = W - pic.width - 20 if i % 2 else 20
            view.alpha_composite(pic, (max(0, min(W - pic.width, x)), round(BAND + 170 - (pic.height - blk.height) / 2)))
        return view

    def stage_frame(i, local, t, where=None, text=True):
        step = steps[i]
        fx = skit["lines"][i].get("fx") or []
        said = local                                         # chữ vẫn hiện dần theo lời kể cả khi đứng hình
        if "freeze" in fx:                                   # đứng hình: nhân vật, máy quay dừng ở đầu câu (không lia nhòe)
            t, local = starts[i], WHIP + EASE
        other = where is not None and where != step["set"]
        stage = stages[where] if other else step["view"]
        prev = steps[i - 1] if i else step
        # đổi khung nhìn (toàn cảnh <-> cận / nhóm, đổi nơi, ra khỏi tranh chèn): cắt thẳng, lia nhòe
        whip = 0.0
        if i and not other and (prev["view"] is not step["view"] or prev["insert"] is not None) and local < WHIP:
            whip = 1 - local / WHIP
        cx, cy, z = W / 2, H / 2, 1.0
        if not step["people"] and stage.instances:          # toàn cảnh: khung ôm vừa nhóm người (bỏ bớt trần / sàn trống của nền)
            here = [inst for inst in stage.instances if inst in step["present"]] or stage.instances
            boxes = [stage.box(n, k, step["expr"][n], step["pose"].get(n)) for n, k in here]
            l, t = min(b[0] for b in boxes), min(b[1] for b in boxes)
            r, b = max(b[2] for b in boxes), max(b[3] for b in boxes)
            pad = 0.35 * (b - t)                              # chừa chỗ quanh người cho chữ thoại và bối cảnh
            cx, cy, z = camera_of((l - pad, t - pad * 1.6, r + pad, b + pad * 0.8))
            z = min(z, 1.9)
            # nhóm ngang trong khung dọc luôn dư chỗ trên / dưới: đặt đáy nhóm ở ~86% khung (khoảng trống dồn lên tường,
            # cửa sổ, chỗ cho chữ thoại) thay vì để nửa dưới là sàn trống
            cy = min(max(b - (0.86 * H - H / 2) / z, H / 2 / z), H - H / 2 / z)
        z *= 1 + 0.015 * min(local / max(timing[i]["seconds"], 0.5), 1.0)   # nhích nhẹ trong câu
        if "zoom_punch" in fx and not other and step["speaker"] in stage.x:   # giật cận vào mặt người nói
            fx_, fy_, _ = face(stage.box(*step["speaker"], step["expr"][step["speaker"][0]], step["pose"].get(step["speaker"][0])))
            p = ease(local / 0.12)
            z2 = max(z * 1.35, 2.2)
            cx, cy, z = cx + (fx_ - cx) * p, cy + (fy_ + H * 0.12 / z2 - cy) * p, z + (z2 - z) * p
            cx = min(max(cx, W / 2 / z), W - W / 2 / z)
            cy = min(max(cy, H / 2 / z), H - H / 2 / z)
        img = stage.bg.convert("RGBA")
        if "gloom_lines" in fx:
            img.alpha_composite(cached("gloom", gloom_layer))
        if "sparkle_bg" in fx:
            img.alpha_composite(sparkle_layer(t))
        if "speed_lines" in fx:
            img.alpha_composite(speed_layer(t))
        for inst in stage.instances:
            name, k = inst
            if inst not in step["present"]:
                continue
            fade = 1.0
            if step["exit"] == name:                            # rời sân khấu: tan dần cuối câu
                fade = 1 - ease((local - timing[i]["seconds"] * 0.5) / 0.5)
            expr, pose = step["expr"][name], step["pose"].get(name)
            # rối giấy như video mẫu: mấp máy miệng (ảnh _talk), lắc lư quanh chân, nhún theo tiếng, nảy khi đổi
            # biểu cảm / tư thế, rung khi hét
            level, talk = 0.0, False
            speaking = inst == step["speaker"] and not timing[i].get("silent") and local < timing[i]["seconds"] \
                and "freeze" not in fx
            if speaking:
                env = envs[i]
                level = float(env[min(int(local * FPS), len(env) - 1)])
                talk = level > 0.22 and (int(local * FPS) // MOUTH_FLAP) % 2 == 0
            phase = k * 1.7 + len(name)
            angle = (2.0 * math.sin(2 * math.pi * 1.1 * t + phase) if speaking
                     else 0.7 * math.sin(2 * math.pi * 0.35 * t + phase))
            dx, dy = 0.0, -14 * level
            changed = i and (steps[i - 1]["expr"][name] != expr or steps[i - 1]["pose"].get(name) != pose)
            if changed and local < HOP:                         # đổi biểu cảm / tư thế: nảy lên
                dy -= 45 * math.sin(math.pi * local / HOP)
            if speaking and skit["lines"][i]["size"] == "shout" and local < 0.6:   # hét: rung mạnh rồi dịu
                fall = 1 - local / 0.6
                angle += 4 * math.sin(2 * math.pi * 9 * local) * fall
                dx += 12 * math.sin(2 * math.pi * 13 * local) * fall
            pic = stage.image(name, expr, pose, talk)
            x0 = stage.x[inst]
            b = stage.feet[inst]
            pad = round(pic.height * 0.07) + 4                  # chừa chỗ để xoay không bị cắt
            canvas = Image.new("RGBA", (pic.width + 2 * pad, pic.height + pad), (0, 0, 0, 0))
            canvas.paste(pic, (pad, pad))
            canvas = canvas.rotate(angle, Image.BICUBIC, center=(canvas.width / 2, canvas.height))   # xoay quanh chân
            if fade < 1:
                canvas.putalpha(canvas.getchannel("A").point(lambda a: round(a * max(fade, 0))))
            img.alpha_composite(canvas, (round(x0 - canvas.width / 2 + dx), round(b - canvas.height + dy)))
            if step["marks"].get(name) and fade > 0.5:
                draw_mark(img, (x0 - pic.width / 2 + dx, b - pic.height + dy, x0 + pic.width / 2 + dx, b + dy),
                          step["marks"][name], t + k)
        if "spotlight" in fx and step["speaker"] in stage.x and not other:
            fx_, fy_, fw_ = face(stage.box(*step["speaker"], step["expr"][step["speaker"][0]], step["pose"].get(step["speaker"][0])))
            img.alpha_composite(cached(("spot", round(fx_), round(fy_)), lambda: spotlight_layer(fx_, fy_ + fw_ * 2, fw_ * 2.4)))
        view = crop(img, (cx, cy, z))
        if "freeze" in fx:                                   # ngả xám
            view = Image.blend(view, view.convert("L").convert("RGBA"), 0.75)
        if "focus_lines" in fx and step["speaker"] in stage.x and not other:
            fx_, fy_, _ = face(stage.box(*step["speaker"], step["expr"][step["speaker"][0]], step["pose"].get(step["speaker"][0])))
            sx_, sy_ = (fx_ - cx) * z + W / 2, (fy_ - cy) * z + H / 2
            variant = int(local * 10) % 3
            view.alpha_composite(cached(("focus", round(sx_ / 20), round(sy_ / 20), variant),
                                        lambda: focus_layer(sx_, sy_, variant)))
        if not text:
            return view
        if whip > 0:                                            # lia nhòe: trộn các bản dịch ngang
            shifts = [view.transform(view.size, Image.AFFINE, (1, 0, dx * whip, 0, 1, 0)) for dx in (-60, -30, 30, 60)]
            view = Image.blend(Image.blend(shifts[0], shifts[3], 0.5), Image.blend(shifts[1], shifts[2], 0.5), 0.5)
        # chữ thoại: câu đang nói + các câu chồng trước đó
        y_next = None
        for j in reversed(step["stack"]):
            line = skit["lines"][j]
            blk = block(j, visible_chars(j, i, said))
            shout = line["size"] == "shout" and not line.get("silent")
            if j == i and shout and local < 0.15:               # câu hét bật ra
                s = 1.25 - 0.25 * (local / 0.15)
                blk = blk.resize((round(blk.width * s), round(blk.height * s)), Image.BILINEAR)
            if shout:
                blk = blk.rotate(4 if j % 2 else -4, Image.BICUBIC, expand=True)
            # vị trí: trên đầu người nói (theo máy quay), không lấn dải tiêu đề
            name, k = steps[j]["speaker"]
            if (name, k) in stage.x:
                l, top, r, b = stage.box(name, k, steps[j]["expr"][name], steps[j]["pose"].get(name))
            else:
                l, top, r, b = W / 2 - 1, H * 0.4, W / 2 + 1, H
            sx = ((l + r) / 2 - cx) * z + W / 2
            sy_top = (top - cy) * z + H / 2
            if y_next is None:
                y = min(max(sy_top - blk.height - 10, BAND + 30), H * 0.55)
                if line["size"] in ("big", "shout") and steps[j]["people"]:
                    y = BAND + 60                                # câu chính khi cận: giữa phía trên
            else:
                y = y_next - blk.height - 6
            if y < BAND + 10:
                break
            x = min(max(sx - blk.width / 2, 30), W - 30 - blk.width)
            view.alpha_composite(blk, (round(x), round(y)))
            y_next = y
        return view

    if frames_only:
        out = folder / "work" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.png"):
            old.unlink()
        picks = [int(x) - 1 for x in frames_only.split(",")] if isinstance(frames_only, str)             else range(0, len(starts), max(1, len(starts) // 16))
        for i in picks:
            at = 0.06 if any(f in (skit["lines"][i].get("fx") or []) for f in ("flash", "shake", "invert")) else 0.5
            frame_at(starts[i] + timing[i]["seconds"] * at).save(out / f"line{i + 1:03d}.png")
        return print(f"Đã xuất khung hình mẫu vào {out}")

    # giọng nối liền + nhạc nền
    voice = folder / "work" / "voice.wav"
    voice.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    for t in timing:
        with wave.open(str(folder / "audio" / t["wav"])) as w:
            data = np.frombuffer(w.readframes(w.getnframes()), "<i2")
        parts += [data, np.zeros(round(48000 * GAP), np.int16)]
    mix = np.concatenate(parts).astype(np.float32) / 32768
    loud = mix[np.abs(mix) > 0.02]
    voice_rms = float(np.sqrt(np.mean(loud ** 2))) if len(loud) else 0.1     # độ to giọng (bỏ đoạn lặng)
    sounds = skit.get("sounds") or {}
    placed = 0
    for i, line in enumerate(skit["lines"]):            # tiếng hiệu ứng tìm mới theo mô tả (skit/sounds.py), nhỏ hơn giọng
        path = sounds.get(line.get("sfx") or "")
        if not path or not (ROOT / path).exists():
            continue
        with wave.open(str(ROOT / path)) as w:
            sfx = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        at = round(48000 * (starts[i] + (timing[i]["seconds"] if line.get("sfx_at") == "end" else 0)))
        end = min(len(mix), at + len(sfx))
        if at < end:
            body = sfx[np.abs(sfx) > 0.02]
            rms = float(np.sqrt(np.mean(body ** 2))) if len(body) else 1.0
            gain = min(voice_rms * 10 ** (-SFX_BELOW / 20) / max(rms, 1e-4), 0.6 / max(float(np.abs(sfx).max()), 1e-4))
            mix[at:end] += sfx[:end - at] * gain
            placed += 1
    mix = np.clip(mix, -1, 1)
    print(f"  {placed} tiếng hiệu ứng", flush=True)
    with wave.open(str(voice), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(48000)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    frames = round(total * FPS)
    silent = folder / "work" / "video.mp4"
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for f in range(frames):
        proc.stdin.write(frame_at(f / FPS).tobytes())
        if f % (FPS * 10) == 0:
            print(f"  {f / FPS:5.1f} / {total:.1f} giây", flush=True)
    proc.stdin.close()
    if proc.wait():
        sys.exit("ffmpeg lỗi khi ghi hình.")
    music = pick_music(folder)
    out = folder / "output.mp4"
    if music:
        sys.path[:0] = [str(ROOT), str(ROOT / "steps")]
        import build_video
        # music_gain đưa nhạc về music_below_voice (settings, cho truyện kể); tiểu phẩm nhỏ hơn nữa tới MUSIC_BELOW
        below = build_video.MUSIC_LOUDER.get(music.parent.name, build_video.VIDEO.get("music_below_voice", 18))
        gain = build_video.music_gain(music, [voice], music.parent.name) * 10 ** (-(MUSIC_BELOW - below) / 20)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice), "-stream_loop", "-1",
                        "-i", str(music), "-filter_complex",
                        f"[2:a]volume={gain:.4f},afade=t=in:d=1,afade=t=out:st={max(total - 2, 0):.2f}:d=2[m];"
                        f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.2f}", "-movflags", "+faststart",
                        str(out)], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(3.0, total / 2):.2f}", "-i", str(out), "-frames:v", "1",
                    "-vf", f"crop={W}:{H - BAND}:0:{BAND},scale=540:-2", str(folder / "work" / "poster.jpg")])     # ảnh bìa cho trang web
    print(f"Xong: {out} ({total:.1f} giây, {len(starts)} câu)")


def pick_music(folder):
    """Nhạc hài trong library/bgm/comical, mỗi tiểu phẩm một bài cố định (theo tên thư mục)."""
    tracks = sorted((ROOT / "library" / "bgm" / "comical").glob("*.mp3"))
    return tracks[random.Random(folder.name).randrange(len(tracks))] if tracks else None


if __name__ == "__main__":
    lines = sys.argv[sys.argv.index("--lines") + 1] if "--lines" in sys.argv else None
    render(Path(sys.argv[1]).resolve(), frames_only=lines or "--frames" in sys.argv)
