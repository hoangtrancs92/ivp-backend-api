"""Dựng video dọc theo lớp: nền + nhân vật + đạo cụ + sticker + chữ, mỗi lớp chuyển động riêng.

Chạy trong thư mục của video (cần ffmpeg và ffprobe trong PATH, và Pillow):
  python <dự án>/build_video.py             dựng output.mp4
  python <dự án>/build_video.py --preview   chỉ xuất một ảnh tĩnh cho mỗi cảnh vào work/preview/ để duyệt bố cục

Đầu vào:
  script.json                 kịch bản, mỗi cảnh có danh sách "layers"
  cutouts/, props/            nhân vật và đạo cụ đã tách nền
  audio/001.wav               giọng đọc từng cảnh
  music.mp3                   nhạc nền (không bắt buộc)
File không có trong thư mục video thì tìm trong library/ của dự án (nền theo bối cảnh và sticker dùng chung).
File tạm nằm trong work/build/, xóa được.

Một lớp trong "layers" được đặt bằng tên, không cần tọa độ:
  {"id": "father", "image": "cutouts/001.png", "size": "large", "path": ["off_left", "center"], "anim": "bounce"}
  {"id": "beer", "image": "props/beer.png", "size": "medium", "at": "father.hand_left", "anim": "wobble"}
  {"image": "props/ice.png", "size": "tiny", "path": ["off_left", "father.above", "beer.top"], "over": 1.0}
  {"word": "キンキンで", "at": "father.beside_right", "vertical": true, "anim": "pop_fade", "start": 0.4}
at:    tên vị trí trong SLOTS, hoặc "<id lớp khác>.<điểm neo>", hoặc [x, y] theo tỉ lệ khung hình
path:  danh sách các vị trí như trên; lớp đi qua lần lượt trong "over" giây rồi mới chạy anim
size:  tên trong SIZES, hoặc chiều cao theo tỉ lệ khung hình
anim:  none | bounce | wobble | pulse | pop | pop_fade | drop | slide_left | slide_right
       | exit_left | exit_right (đi ra cuối cảnh) | approach | recede (tiến lại gần / đi xa) | jump
at "floor" | "floor_left" | "floor_right": đứng sát mép dưới khung (dùng cho shot half, close)
shot (của cảnh): full | half | close; lớp nhân vật chính bỏ trống size, at thì lấy theo [shots] trong settings.toml
motion: (cả khung hình) zoom_in | zoom_out | pan_left | pan_right | shake | none
filter: none | sepia
alt_pose (của cảnh): có giá trị thì mỗi lớp ảnh có bản <tên>_alt (vd cutouts/003_alt.png) được đổi qua lại
       giữa hai tư thế, mỗi alt_interval giây (config/settings.toml)
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import wave
import tomllib
from pathlib import Path

import numpy as np
import pytweening
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import variety  # noqa: E402                       tự đa dạng anim, motion, chuyển cảnh còn trống
import effects  # noqa: E402                       hiệu ứng vẽ bằng code: hào quang, tia sáng, lấp lánh...
sys.path.insert(0, str(Path(__file__).resolve().parent / "steps"))
from common import normalize_script  # noqa: E402  sửa chỗ model viết lệch ("src" -> "image", "shot": null...)

ROOT = Path(__file__).resolve().parent             # thư mục dự án
# Thông số chỉnh được nằm ở config/settings.toml (mục [video] và [layout])
SETTINGS = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))
VIDEO = SETTINGS["video"]
W, H, FPS = 1080, 1920, 30
PAD = VIDEO["pad"]                    # giây nghỉ sau mỗi câu
MUSIC_VOLUME = VIDEO["music_volume"]  # nhạc nền so với giọng đọc
TRANSITION = VIDEO["transition"]      # giây chuyển cảnh ở đầu mỗi cảnh
ALT_INTERVAL = VIDEO["alt_interval"]  # giây giữa hai lần đổi tư thế (cảnh có alt_pose)
LIBRARY = ROOT / "library"

# Vị trí có tên: tâm của lớp theo tỉ lệ khung hình (x, y)
SLOTS = {name: tuple(xy) for name, xy in SETTINGS["layout"]["slots"].items()}
# Kích thước có tên: chiều cao của lớp so với khung hình
SIZES = SETTINGS["layout"]["sizes"]
SHOTS = SETTINGS["shots"]                    # khung hình của cảnh: cỡ và vị trí mặc định của lớp nhân vật
FLOOR = {"floor": 0.50, "floor_left": 0.40, "floor_right": 0.60}   # vị trí x; y tính theo chiều cao lớp
EDGES = ("edge_left", "edge_right")         # dán sát mép trái/phải và mép dưới (ảnh có cột, tường, cửa vẽ dính)
GAP = SETTINGS["layout"]["sticker_gap"]      # khoảng hở giữa sticker và đầu nhân vật
EDGE = SETTINGS["layout"]["edge_margin"]     # lề tối thiểu từ lớp đứng yên tới mép khung
TMP = Path("work") / "build"
PREVIEW = Path("work") / "preview"


def run(*args, **kw):
    return subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True, **kw)


def duration(path):
    if Path(path).suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as audio:
                rate = audio.getframerate()
                frames = audio.getnframes()
            if rate > 0 and frames > 0:
                return frames / rate
            raise ValueError(f"WAV không có dữ liệu âm thanh: {path}")
        except (wave.Error, EOFError, ZeroDivisionError) as error:
            raise ValueError(f"WAV không hợp lệ hoặc rỗng: {path}") from error
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    value = out.stdout.strip()
    try:
        seconds = float(value)
    except ValueError as error:
        raise ValueError(f"ffprobe không trả thời lượng hợp lệ cho {path}: {value!r}") from error
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"ffprobe trả thời lượng không hợp lệ cho {path}: {value!r}")
    return seconds


def find(path):
    """Tìm file trong thư mục video trước, rồi tới thư viện dùng chung."""
    for candidate in (Path(path), LIBRARY / path):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(path)


def font_path(script):
    """font_file trong script.json tính từ thư mục dự án ("fonts/..."); đường dẫn cũ kiểu "../../fonts/..." vẫn nhận."""
    name = script.get("font_file")
    if not name:
        return None
    for candidate in (ROOT / name, Path(name), ROOT / "fonts" / Path(name).name):
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(name)


# ---------- chuyển động của từng lớp ----------

ease_out = pytweening.easeOutCubic          # chậm dần khi tới nơi
overshoot = pytweening.easeOutBack          # 0 → 1, vượt quá 1 một chút rồi về lại: cảm giác bật ra
landing = pytweening.easeOutBounce          # rơi chạm đất rồi nảy hai nhịp nhỏ


def animate(kind, t, life):
    """Trả về (dx, dy, scale, góc xoay, alpha) của lớp ở giây thứ t kể từ lúc nó xuất hiện.
    dx, dy tính theo tỉ lệ khung hình."""
    dx = dy = angle = 0.0
    scale = alpha = 1.0
    enter = min(t / 0.3, 1.0)
    if kind == "bounce":                       # nhún lên xuống
        dy = -0.012 * abs(math.sin(math.pi * 2.2 * t))
    elif kind == "wobble":                     # lắc qua lại
        angle = 8 * math.sin(2 * math.pi * 1.6 * t)
    elif kind == "pulse":                      # to dần
        scale = 1 + 0.08 * min(t / life, 1.0)
    elif kind in ("pop", "pop_fade"):          # bật ra
        scale = max(overshoot(enter), 0.01)
        if kind == "pop_fade":                 # rồi mờ dần ở cuối
            alpha = min(max((life - t) / 0.4, 0.0), 1.0)
    elif kind == "drop":                       # rơi từ trên xuống
        dy = -(1 - landing(min(t / 0.6, 1.0))) * 0.6
    elif kind == "slide_left":                 # trượt vào từ bên trái
        dx = -(1 - overshoot(min(t / 0.45, 1.0))) * 0.8
    elif kind == "slide_right":                # trượt vào từ bên phải
        dx = (1 - overshoot(min(t / 0.45, 1.0))) * 0.8
    elif kind in ("exit_left", "exit_right"):  # đứng yên, rồi đi ra khỏi khung trong 0,6 giây cuối
        leave = min(max((t - (life - 0.6)) / 0.6, 0.0), 1.0)
        dx = leave ** 3 * 0.9 * (-1 if kind == "exit_left" else 1)
    elif kind in ("approach", "recede"):       # tiến lại gần: to dần và trượt xuống cho chân bám mặt đường
        near = ease_out(min(t / life, 1.0))
        if kind == "recede":
            near = 1 - near
        scale = 0.55 + 0.45 * near
        dy = -0.10 * (1 - near)
    elif kind == "jump":                       # nhảy lên một lần ở đầu
        dy = -0.10 * math.sin(math.pi * min(t / 0.5, 1.0))
    elif kind == "nod":                        # gật đầu vài lần
        dy = 0.008 * max(0.0, math.sin(2 * math.pi * 2.4 * t)) * (t < 1.3)
    elif kind == "shake_no":                   # lắc người qua lại, nhỏ dần (phủ nhận, bối rối)
        dx = 0.012 * math.sin(2 * math.pi * 3.2 * t) * math.exp(-1.6 * t)
    elif kind == "sway":                       # đung đưa chậm
        angle = 2.5 * math.sin(2 * math.pi * 0.7 * t)
        dx = 0.005 * math.sin(2 * math.pi * 0.7 * t)
    elif kind == "tilt":                       # nghiêng người như nghiêng đầu thắc mắc
        angle = 5 * ease_out(min(t / 0.4, 1.0))
    elif kind == "breathe":                    # thở nhẹ, gần như đứng yên
        scale = 1 + 0.012 * math.sin(2 * math.pi * 0.5 * t)
    elif kind == "shiver":                     # run rẩy (sợ, giận, sốc)
        dx = 0.003 * math.sin(2 * math.pi * 13 * t) + 0.002 * math.sin(2 * math.pi * 7 * t)
    elif kind == "hop":                        # nhảy lò cò ba lần (vui, hớn hở)
        dy = -0.03 * abs(math.sin(math.pi * t / 0.33)) * (t < 0.99)
    elif kind == "sink":                       # chùng xuống (buồn, thất vọng)
        sag = ease_out(min(t / 1.0, 1.0))
        dy, scale = 0.04 * sag, 1 - 0.03 * sag
    elif kind == "float":                      # bồng bềnh (mơ màng, hồi tưởng)
        dy = -0.01 * math.sin(2 * math.pi * 0.45 * t)
        angle = 1.2 * math.sin(2 * math.pi * 0.3 * t)
    elif kind == "punch":                      # bật mạnh lên rồi về cỡ thường (nhấn mạnh, sốc)
        scale = 1 + 0.16 * max(0.0, 1 - t / 0.25) ** 2
    elif kind == "spin_in":                    # xoay vào
        p = min(t / 0.55, 1.0)
        angle, scale = 360 * (1 - ease_out(p)), max(overshoot(p), 0.01)
    elif kind == "lean_in":                    # chồm tới gần người xem
        p = ease_out(min(t / 0.6, 1.0))
        scale, dy = 1 + 0.07 * p, 0.015 * p
    elif kind == "snap":                       # giật người / quay đầu thật nhanh rồi rung về (thốt lên, phản bác)
        spring = math.exp(-7.0 * t) * math.sin(2 * math.pi * 2.4 * t + 0.4)
        angle, dx = 7 * spring, 0.012 * spring
        scale = 1 + 0.06 * math.exp(-10.0 * t)
    elif kind == "rise":                       # trồi lên từ mép dưới khung
        dy = (1 - overshoot(min(t / 0.5, 1.0))) * 0.45
    return dx, dy, scale, angle, alpha


def deform(kind, t, life):
    """Co giãn ảnh cho các anim kiểu hoạt hình: (sx, sy, jelly). sx, sy: tỉ lệ ngang, dọc (chân giữ trên mặt đất);
    jelly: độ lắc ngang của phần trên người (tỉ lệ bề rộng ảnh), cho hiệu ứng rung như thạch."""
    sx = sy = 1.0
    jelly = 0.0
    if kind == "squash":                       # bẹp xuống rồi bật lên, nảy vài nhịp (hăng hái, phấn khích)
        sy = 1 - 0.16 * math.exp(-4.0 * t) * math.cos(2 * math.pi * 2.2 * t)
        sx = sy ** -0.5                        # giữ thể tích: bẹp thì bè ra
    elif kind == "jelly":                      # rung như thạch, nhỏ dần (giật mình, xấu hổ, cười ngượng)
        jelly = 0.03 * math.exp(-2.0 * t) + 0.004
        sy = 1 + 0.03 * math.exp(-3.0 * t) * math.sin(2 * math.pi * 3 * t)
        sx = sy ** -0.5
    elif kind == "puff":                       # phồng người lên vì giận, run nhẹ
        p = ease_out(min(t / 0.35, 1.0))
        sx = 1 + 0.07 * p + 0.012 * p * math.sin(2 * math.pi * 9 * t)
        sy = 1 + 0.03 * p
    elif kind == "deflate":                    # xẹp xuống (thất vọng, kiệt sức)
        p = ease_out(min(t / 0.9, 1.0))
        sy, sx = 1 - 0.10 * p, 1 + 0.04 * p
    elif kind == "stretch_up":                 # giật mình vươn dài người rồi về (ngạc nhiên)
        sy = 1 + 0.12 * math.exp(-4.0 * t) * math.sin(2 * math.pi * 1.8 * t)
        sx = sy ** -0.5
    return sx, sy, jelly


IDLE = VIDEO.get("idle_motion", True)       # nhân vật luôn thở, đung đưa nhẹ (tắt: idle_motion = false trong [video])
IDLE_SKIP = {"squash", "jelly", "puff", "deflate", "stretch_up", "none"}   # anim co giãn tự lo; "none": cố ý đứng yên


def idle(t, seed):
    """Chuyển động nhỏ luôn có của nhân vật: thở (giãn dọc rất nhẹ) và đung đưa thân trên (nghiêng, chân đứng yên).
    seed lệch pha để hai nhân vật cùng cảnh không thở đều như nhau. Trả về (sy, độ nghiêng thân trên)."""
    phase = (seed % 97) / 97 * 2 * math.pi
    sy = 1 + 0.009 * math.sin(2 * math.pi * 0.42 * t + phase)
    lean = 0.010 * math.sin(2 * math.pi * 0.31 * t + phase * 1.7) + 0.004 * math.sin(2 * math.pi * 0.83 * t + phase)
    return sy, lean


def lean_over(img, lean, sx=1.0, sy=1.0):
    """Co giãn sx, sy và nghiêng thân trên (đỉnh ảnh lệch ngang lean × chiều cao, chân đứng yên) trong một lần lấy mẫu."""
    w, h = max(round(img.width * sx), 1), max(round(img.height * sy), 1)
    shift = lean * h
    pad = math.ceil(abs(shift)) + 1
    return img.transform((w + 2 * pad, h), Image.AFFINE,
                         (1 / sx, shift / h / sx, (-pad - shift) / sx, 0, 1 / sy, 0), Image.BILINEAR)


def jiggle(img, amount, t):
    """Lắc ngang từng dải ngang của ảnh theo sóng, đầu lắc nhiều, chân đứng yên."""
    pad = math.ceil(amount * img.width) + 1
    out = Image.new("RGBA", (img.width + 2 * pad, img.height))
    step = 6
    for y in range(0, img.height, step):
        k = 1 - y / img.height
        offset = amount * img.width * k * math.sin(2 * math.pi * 5.5 * t - 3 * y / img.height)
        out.paste(img.crop((0, y, img.width, min(y + step, img.height))), (pad + round(offset), y))
    return out


def word_image(layer, font_file, factor=1.0):
    """Vẽ chữ tượng thanh thành một ảnh trong suốt, để xử lý như mọi lớp ảnh khác."""
    size = max(round(layer.get("size", 64) * factor), 12)
    font = ImageFont.truetype(font_file, size) if font_file else ImageFont.load_default(size)
    text = "\n".join(layer["word"]) if layer.get("vertical") else layer["word"]
    stroke = max(size // 10, 2)
    box = ImageDraw.Draw(Image.new("RGBA", (1, 1))).multiline_textbbox(
        (0, 0), text, font=font, stroke_width=stroke, align="center")
    left, top, right, bottom = map(round, box)
    img = Image.new("RGBA", (right - left + 8, bottom - top + 8))
    ImageDraw.Draw(img).multiline_text(
        (4 - left, 4 - top), text, font=font, align="center",
        fill=layer.get("colour", "#111111"), stroke_width=stroke, stroke_fill=layer.get("outline", "#FFFFFF"))
    return img


def silhouette(img):
    """Đọc hình dáng thật của lớp từ vùng không trong suốt (pixel, tính từ góc trên trái của ảnh):
    đỉnh, đáy, đầu (trái, phải, tâm dọc) và điểm xa nhất hai bên ở dải thân (tay)."""
    alpha = np.asarray(img.getchannel("A")) > 40
    rows = np.flatnonzero(alpha.any(axis=1))
    if rows.size == 0:
        return None
    top, bottom = int(rows[0]), int(rows[-1])
    height = bottom - top + 1
    # tâm đầu: trung bình các cột có hình ở 6% trên cùng; bề rộng đầu: đoạn liền chứa tâm đó ở 14% chiều cao
    crown = np.flatnonzero(alpha[top:top + max(1, round(0.06 * height))].any(axis=0))
    x0 = int(crown.mean())
    row = alpha[top + round(0.14 * height)]
    if row[x0]:
        left = x0
        while left > 0 and row[left - 1]:
            left -= 1
        right = x0
        while right < row.size - 1 and row[right + 1]:
            right += 1
    else:
        left, right = int(crown[0]), int(crown[-1])
    # tay: điểm xa nhất bên trái và bên phải trong dải 30%-80% chiều cao
    band_top = top + round(0.30 * height)
    band = alpha[band_top:top + round(0.80 * height)]
    cols = np.flatnonzero(band.any(axis=0))

    def reach(col):
        return int(col), band_top + int(np.flatnonzero(band[:, col]).mean())

    return {"top": top, "bottom": bottom, "head": (left, right, top + round(0.13 * height)),
            "hand_left": reach(cols[0]), "hand_right": reach(cols[-1])}


def anchor(centre, img, shape, name, child):
    """Điểm neo trên lớp cha, tính theo hình dáng thật của lớp cha (silhouette) và cỡ của lớp con:
    sticker đặt sát cạnh đầu hoặc trên đầu, không đè lên mặt."""
    cx, cy = centre

    def frame(px, py):                        # pixel trong ảnh lớp cha -> tỉ lệ khung hình
        return cx + (px - img.width / 2) / W, cy + (py - img.height / 2) / H

    w = img.width / W
    if shape is None or name in ("center", "left", "right"):
        return {"center": (cx, cy), "left": (cx - w / 2, cy), "right": (cx + w / 2, cy)}.get(name, (cx, cy))
    half_w, half_h = child.width / W / 2, child.height / H / 2
    head_left, head_right, head_y = shape["head"]
    x_left, y = frame(head_left, head_y)
    x_right, _ = frame(head_right, head_y)
    head_x, top = frame((head_left + head_right) / 2, shape["top"])
    return {
        "top": (head_x, top), "bottom": frame(img.width / 2, shape["bottom"]),
        "head": (head_x, y), "above": (head_x, top - GAP - half_h),
        "beside_left": (x_left - GAP - half_w, y), "beside_right": (x_right + GAP + half_w, y),
        "hand_left": frame(*shape["hand_left"]), "hand_right": frame(*shape["hand_right"]),
    }[name]


def fits(x, child):
    half_w = child.width / W / 2
    return half_w + EDGE <= x <= 1 - half_w - EDGE


def inside(point, child):
    """Kẹp tâm lớp để lớp nằm trọn trong khung, cách mép ít nhất EDGE."""
    x, y = point
    half_w, half_h = child.width / W / 2, child.height / H / 2
    return min(max(x, half_w + EDGE), 1 - half_w - EDGE), min(max(y, half_h + EDGE), 1 - half_h - EDGE)


def resolve(place, placed, child, clamp=False):
    """Đổi một vị trí viết bằng tên thành tọa độ (x, y).
    clamp (lớp đứng yên bằng "at"): sticker cạnh đầu mà tràn mép thì đổi sang bên kia đầu, rồi kẹp trong khung."""
    if not isinstance(place, str):
        return tuple(place)
    if place in FLOOR:                         # đứng sát mép dưới khung (nửa người, cận mặt)
        return FLOOR[place], 1 - child.height / H / 2
    if place in EDGES:                         # dán sát mép trái/phải và mép dưới: ảnh có cột, tường, cửa vẽ dính
        half_w = child.width / W / 2
        return (half_w if place == "edge_left" else 1 - half_w), 1 - child.height / H / 2
    if place in SLOTS:
        return SLOTS[place]
    target, name = place.split(".")
    parent = placed[target]                    # KeyError nếu lớp kia chưa được đặt
    point = anchor(*parent, name, child)
    if not clamp:
        return point
    if name in ("beside_left", "beside_right") and not fits(point[0], child):
        other = anchor(*parent, "beside_right" if name == "beside_left" else "beside_left", child)
        if fits(other[0], child):
            point = other
    return inside(point, child)


# Tư thế thứ hai: trước đây đổi qua lại mỗi 0,25 giây ở mọi cảnh -> nhấp nháy (hai ảnh vẽ riêng luôn lệch nét, có cặp khác
# hẳn bề ngang; video 024: 20/48 cảnh). Nay mặc định đổi MỘT lần ở giữa câu (như đổi cử chỉ); chỉ động tác lặp lại thật
# (đi, chạy, vẫy, gõ, ăn, nhai, khóc nấc, cười lăn) mới luân phiên, chậm hơn.
ALT_LOOP = 0.4
ALT_SWITCH = 0.5
LOOP_WORDS = ("walk", "run", "jog", "march", "wav", "typ", "eat", "chew", "munch", "sob", "laugh", "clap", "nod", "shak",
              "tremb", "shiver", "jump", "danc", "knock", "stir", "cook", "scrub", "wipe")


def alt_loops(scene, layer_id):
    """Ảnh tư thế 2 của lớp này có phải động tác lặp lại (luân phiên) không, theo mô tả alt_pose (chỉ tư thế 2: action
    tả tư thế 1 hay có "typing" mà tư thế 2 lại là gãi đầu, hai cử chỉ khác nhau thì phải đổi một lần)."""
    value = scene.get("alt_pose")
    if isinstance(value, dict):
        value = value.get(layer_id) or " ".join(map(str, value.values()))
    words = re.findall(r"[a-z]+", str(value or "").lower())
    return any(w.startswith(k) for w in words for k in LOOP_WORDS)


MULTI_SCALE = {2: 0.8, 3: 0.7}     # cỡ mỗi nhân vật khi cảnh có 2 / 3 người, so với cảnh một người


def with_shot(scene, layer):
    """Lớp nhân vật chính của cảnh (cutouts/NNN...png) bỏ trống size, at thì lấy theo "shot" của cảnh."""
    image = Path(layer.get("image", ""))
    if image.parent.name != "cutouts" or not image.stem.startswith(f"{scene['id']:03d}"):
        return layer
    shot = SHOTS[scene.get("shot", "full")]
    layer = dict(layer)
    # nhiều nhân vật cùng khung: mỗi người nhỏ lại cho vừa (video 024: hai, ba người cỡ cảnh một người chen chúc, cắt mép)
    people = sum(1 for l in scene.get("layers", []) if Path(str(l.get("image", ""))).parent.name == "cutouts"
                 and Path(str(l.get("image", ""))).stem.startswith(f"{scene['id']:03d}"))
    layer.setdefault("size", round(shot["size"] * MULTI_SCALE.get(min(people, 3), 1.0), 3))
    if "path" not in layer:
        layer.setdefault("at", shot["at"])
    return layer


def fit_height(path, target, fill_holes=None):
    img = Image.open(path).convert("RGBA")
    if fill_holes:
        img = fill_enclosed(img, fill_holes)
    return img.resize((max(round(img.width * target / img.height), 1), target), Image.LANCZOS)


def fill_enclosed(img, colour):
    """Tô màu các lỗ trong suốt nằm gọn bên trong hình (lòng tấm ảnh chụp, khung tranh), không tô vùng
    trong suốt thông ra mép ảnh. Dùng cho lớp có "fill_holes": "#RRGGBB"."""
    from scipy import ndimage
    alpha = np.asarray(img.getchannel("A"))
    labels, _ = ndimage.label(alpha < 128)
    edge = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    holes = (labels > 0) & ~np.isin(labels, list(edge))
    if not holes.any():
        return img
    backing = Image.new("RGBA", img.size, colour)
    backing.putalpha(Image.fromarray((holes * 255).astype(np.uint8)))
    return Image.alpha_composite(backing, img)


def load_layers(scene, font_file):
    """Nạp ảnh của từng lớp, thu về đúng kích thước và tính các điểm trên đường đi. Làm một lần mỗi cảnh.
    Lớp neo vào lớp khác ("at": "father.beside_left") có cỡ tỉ lệ theo lớp đó: nhân vật nhỏ thì sticker nhỏ."""
    items, by_id = [], {}
    for index, layer in enumerate(scene.get("layers", [])):
        if "effect" in layer:                  # hiệu ứng vẽ bằng code mỗi khung hình (effects.py), không có ảnh
            item = {"layer": layer, "img": None, "id": f"effect_{index}", "effect": True, "shape": None,
                    "points": [(0.5, 0.5)], "seed": scene["id"] * 100 + index}
            box = (scene.get("effect_anchors") or {}).get(layer.get("on"))
            if box is not None and scene.get("full"):
                from effect_rules import project_anchor
                with Image.open(Path("full") / f"{scene['id']:03d}.png") as source:
                    item["anchor_box"] = project_anchor(box, source.size, (W, H), FULL_SHIFT)
            files = fx_files(fx_group(layer["effect"]))
            if files:                          # hiệu ứng là video nền đen (library/fx), chồng kiểu screen
                rng = random.Random(item["seed"])
                item["fx"] = {"path": rng.choice(files), "offset": rng.uniform(0, 4), "frames": None}
            items.append(item)
            continue
        layer = with_shot(scene, layer)
        parent = by_id.get(parent_of(layer))
        factor = parent["img"].height / (SIZES["large"] * H) if parent else 1.0
        if "word" in layer:
            img = word_image(layer, font_file, factor)
        else:
            size = layer.get("size", "medium")
            target = round(SIZES[size] * H * factor) if size in SIZES else round(size * H)
            img = fit_height(find(layer["image"]), target, layer.get("fill_holes"))
        name = layer.get("id") or Path(layer.get("image", "word")).stem
        if name in by_id:                      # hai sticker cùng ảnh: mỗi lớp một tên riêng, không bị vẽ chồng
            name = f"{name}_{index}"
        item = {"layer": layer, "img": img, "id": name, "shape": silhouette(img) if "image" in layer else None,
                "character": Path(str(layer.get("image", ""))).parent.name == "cutouts"}
        if scene.get("alt_pose") and "image" in layer:   # tư thế thứ hai: cutouts/003.png -> cutouts/003_alt.png
            alt = Path(layer["image"])
            alt = alt.with_name(f"{alt.stem}_alt{alt.suffix}")
            if Path(alt).exists() or (LIBRARY / alt).exists():
                item["alt"] = fit_height(find(alt), img.height)
                item["alt_loop"] = alt_loops(scene, item["id"])
        if item["character"]:
            add_faces(scene, item, img.height)
        items.append(item)
        by_id[name] = item

    placed, waiting = {}, [i for i in items if not i.get("effect")]   # một lớp có thể neo vào lớp khai báo sau nó
    while waiting:
        before = len(waiting)
        for item in list(waiting):
            layer = item["layer"]
            places = layer.get("path") or [layer.get("at", "center")]
            try:
                item["points"] = [resolve(place, placed, item["img"], clamp=not layer.get("path"))
                                  for place in places]
            except KeyError:
                continue
            placed[item["id"]] = (item["points"][-1], item["img"], item["shape"])
            waiting.remove(item)
        if len(waiting) == before:
            raise ValueError(f"Cảnh {scene['id']}: không tìm thấy vị trí của lớp {[i['id'] for i in waiting]}")
    scene["_focus"] = focus_point(scene, placed)
    return items


# ---------- "focus": hai cú máy trong một cảnh (toàn cảnh, rồi đẩy vào một nhân vật / đồ vật trên tay / một điểm) ----------

FOCUS_MOVE = 0.35            # giây đẩy máy vào


def focus_point(scene, placed):
    """(điểm (x, y), giây bắt đầu hoặc tỉ lệ cảnh, độ zoom) của "focus" trong kịch bản, hoặc None.
    "on": "<id>" (mặt nhân vật), "<id>.<điểm neo>" (vd "father.hand_right": đồ đang cầm), hoặc [x, y]."""
    focus = scene.get("focus")
    if not isinstance(focus, dict) or not focus.get("on"):
        return None
    on, dummy = focus["on"], Image.new("RGBA", (2, 2))
    try:
        if isinstance(on, (list, tuple)):
            point = (float(on[0]), float(on[1]))
        elif "." not in str(on):
            point = anchor(*placed[on], "head", dummy)      # nhân vật: đẩy vào mặt
        else:
            point = resolve(on, placed, dummy)
    except (KeyError, ValueError, IndexError):
        return None
    return point, float(focus.get("at", 0.45)), float(focus.get("zoom", 1.45))


def focus_camera(frame, scene, t, length):
    """Trước mốc "at": toàn cảnh, máy nhích vào rất chậm; tới mốc: đẩy nhanh vào điểm focus rồi giữ."""
    (px, py), at, zoom = scene["_focus"]
    start = at * length if at < 1 else at
    p = ease_out(min(max((t - start) / FOCUS_MOVE, 0.0), 1.0))
    z = 1 + 0.04 * min(t / max(start, 0.01), 1.0)
    z += (zoom - z) * p
    cx, cy = 0.5 + (px - 0.5) * p, 0.5 + (py - 0.5) * p
    w, h = W / z, H / z
    left = min(max(cx * W - w / 2, 0), W - w)
    top = min(max(cy * H - h / 2, 0), H - h)
    return frame.resize((W, H), Image.BILINEAR, box=(left, top, left + w, top + h))


# ---------- hiệu ứng video nền đen (library/fx, tools/fetch_fx.py): lấp lánh, bokeh, vệt sáng, bụi, khói ----------

FX_DIR = LIBRARY / "fx"
FX_SIZE = (540, 960)            # tools/fetch_fx.py đổi sẵn mọi file về khung dọc này
FX_FADE = 0.3                   # giây hiện dần / tắt dần
FX_OPACITY = {"sparkle": 1.0, "gold": 0.45, "bokeh": 0.6, "light_leak": 0.8, "dust": 0.85, "magic": 0.4,
              "glitter": 0.9}
# nền Irasutoya sáng màu, "screen" chỉ làm sáng thêm: tăng sáng video hiệu ứng để thấy rõ (đo bằng mắt trên video 015)
FX_GAIN = {"sparkle": 2.4, "light_leak": 2.2, "dust": 1.8, "bokeh": 1.3, "glitter": 1.5}
FX_BANNED = {"smoke"}   # khói quay thật trên tranh phẳng trông như vết bẩn (video 022): không bao giờ dùng


def fx_group(kind):
    """"fx_bokeh" -> "bokeh"; hiệu ứng vẽ bằng code (không có tiền tố fx_) -> None."""
    return kind[3:] if isinstance(kind, str) and kind.startswith("fx_") else None


def fx_files(group):
    return sorted((FX_DIR / group).glob("*.mp4")) if group and group not in FX_BANNED else []


def fx_frames(path, offset, seconds):
    """Đọc các khung hình (540x960) của file hiệu ứng từ giây offset, lặp lại nếu file ngắn hơn."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-ss", f"{offset:.2f}", "-i", str(path),
                          "-t", f"{seconds:.2f}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    size = FX_SIZE[0] * FX_SIZE[1] * 3
    return np.frombuffer(raw[:len(raw) // size * size], np.uint8).reshape(-1, FX_SIZE[1], FX_SIZE[0], 3)


def fx_blend(frame, item, local, life):
    """Chồng một khung của video hiệu ứng lên ảnh kiểu "screen": phần đen biến mất, chỉ còn ánh sáng; mờ vào / ra."""
    fx = item["fx"]
    if fx["frames"] is None:                  # đọc một lần mỗi cảnh, đủ cho thời gian hiệu ứng hiện
        frames = fx_frames(fx["path"], fx["offset"], life + 0.3)
        gain = FX_GAIN.get(fx_group(item["layer"]["effect"]), 1.0)
        fx["frames"] = np.clip(frames * gain, 0, 255).astype(np.uint8) if gain != 1.0 else frames
    frames = fx["frames"]
    if not len(frames):
        return frame
    layer = item["layer"]
    overlay = Image.fromarray(frames[min(int(local * FPS), len(frames) - 1)]).resize((W, H), Image.BILINEAR)
    fade = min(1.0, local / FX_FADE, (life - local) / FX_FADE)
    opacity = layer.get("opacity", FX_OPACITY.get(fx_group(layer["effect"]), 0.7)) * max(fade, 0.0)
    return Image.blend(frame, ImageChops.screen(frame, overlay), opacity) if opacity > 0.01 else frame


# ---------- chớp mắt, mấp máy miệng (ảnh do tools/make_faces.py tạo trong cutouts/faces/) ----------

BLINK_LENGTH = 0.13        # giây mắt nhắm mỗi lần chớp
BLINK_GAP = (2.2, 4.2)     # giây giữa hai lần chớp (ngẫu nhiên, cố định theo nhân vật và cảnh)
MOUTH_FLAP = 3             # số khung hình mỗi nhịp đóng / mở miệng khi đang nói (30 fps: ~5 lần mở mỗi giây)


def add_faces(scene, item, height):
    """Gắn ảnh mắt nhắm / miệng mở (nếu có) cho lớp nhân vật, cùng cỡ với ảnh chính và ảnh tư thế 2.
    Miệng chỉ mấp máy với nhân vật đang nói câu của cảnh (speaker), không mấp máy khi là lời kể."""
    stem = Path(item["layer"]["image"]).stem
    for key, name in (("main", stem), ("alt", f"{stem}_alt")):
        for kind in ("blink", "talk"):
            path = Path("cutouts") / "faces" / f"{name}_{kind}.png"
            if path.exists():
                item.setdefault("faces", {})[(key, kind)] = fit_height(path, height)
    if "faces" not in item:
        return
    speaker, who = scene.get("speaker", ""), stem[4:]
    item["speaks"] = (scene.get("_dialogue", True) and speaker not in ("", "narrator")     # lời kể: miệng đứng yên
                      and (who == speaker or (not who and scene.get("characters") == [speaker])))
    rng = random.Random(scene["id"] * 1000 + sum(map(ord, stem)))
    t, blinks = rng.uniform(0.3, 1.6), []
    while t < 60:
        blinks.append(t)
        t += rng.uniform(*BLINK_GAP)
    item["blinks"] = blinks


def face_frame(scene, item, img, key, t):
    """Ảnh nhân vật của khung hình này: mắt nhắm khi tới lượt chớp, miệng mở theo tiếng nói, không thì ảnh thường."""
    faces = item.get("faces")
    if not faces:
        return img
    if any(b <= t < b + BLINK_LENGTH for b in item["blinks"]) and (key, "blink") in faces:
        return faces[(key, "blink")]
    mouth = scene.get("_mouth")
    if item.get("speaks") and mouth is not None and (key, "talk") in faces:
        i = int(t * FPS)
        if i < len(mouth) and mouth[i] and (i // MOUTH_FLAP) % 2 == 0:
            return faces[(key, "talk")]
    return img


def mouth_track(audio, frames):
    """Mỗi khung hình: giọng đang có tiếng không (RMS > 25% mức to nhất của câu). Dùng cho mấp máy miệng."""
    voice, rate = read_wav(audio)
    if voice is None or not len(voice):
        return None
    step = rate / FPS
    rms = np.array([np.sqrt(np.mean(voice[int(i * step):int((i + 1) * step)] ** 2)) if int(i * step) < len(voice) else 0.0
                    for i in range(frames)])
    return rms > rms.max() * 0.25 if rms.max() > 0 else None


def along(points, p):
    """Vị trí trên đường cong mượt đi qua các điểm; p chạy từ 0 đến 1."""
    if len(points) == 1:
        return points[0]
    p = p * p * (3 - 2 * p)                    # nhanh dần rồi chậm dần
    last = len(points) - 1
    seg = min(int(p * last), last - 1)
    u = p * last - seg
    a, b, c, d = (points[min(max(seg + k, 0), last)] for k in (-1, 0, 1, 2))
    return tuple(0.5 * (2 * b[i] + (c[i] - a[i]) * u + (2 * a[i] - 5 * b[i] + 4 * c[i] - d[i]) * u ** 2
                        + (3 * b[i] - a[i] - 3 * c[i] + d[i]) * u ** 3) for i in (0, 1))


FULL_SHIFT = 300      # px: tranh vẽ cả cảnh dời xuống để mặt người nằm dưới phụ đề (phụ đề ~410-700 px từ đỉnh)


def place_full(img):
    """Tranh vẽ người cự ly gần: mặt hay nằm đúng vùng phụ đề (dưới dải tiêu đề). Đẩy tranh xuống FULL_SHIFT px (mất một ít
    ở đáy), phần hở phía trên (gần như bị dải tiêu đề che) lấp bằng chính mép trên của tranh làm mờ (video 031)."""
    img = ImageOps.fit(img, (W, H), Image.LANCZOS)
    out = img.crop((0, 0, W, FULL_SHIFT)).resize((W, FULL_SHIFT + 40)).filter(ImageFilter.GaussianBlur(18))
    canvas = Image.new("RGB", (W, H))
    canvas.paste(out, (0, 0))
    canvas.paste(img.crop((0, 0, W, H - FULL_SHIFT)), (0, FULL_SHIFT))
    return canvas


def clip_backgrounds(scene):
    """Cảnh "motion_level": "low" có clips/NNN.mp4 (clip image-to-video từ tranh cả cảnh, tools/run_kaggle.py):
    trả về danh sách khung nền theo FPS của video, đặt như tranh cả cảnh. Clip ngắn hơn câu thoại thì giữ khung cuối.
    Clip cũ hơn tranh (tranh vẽ lại sau khi duyệt) thì bỏ, dùng ảnh tĩnh."""
    clip, full = Path("clips") / f"{scene['id']:03d}.mp4", Path("full") / f"{scene['id']:03d}.png"
    if scene.get("motion_level") != "low" or not clip.exists() or \
            full.exists() and clip.stat().st_mtime < full.stat().st_mtime:
        return []
    # gọi thẳng ffprobe / ffmpeg (hàm run() đã tự thêm "ffmpeg -y" ở đầu: dùng nó ra lệnh "ffmpeg ffprobe ...", video 045)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(clip)], capture_output=True, text=True, check=True).stdout
    w, h = (int(x) for x in probe.strip().split(",")[:2])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-"], capture_output=True, check=True).stdout
    return [place_full(Image.frombytes("RGB", (w, h), raw[k:k + w * h * 3])) for k in range(0, len(raw), w * h * 3)]


def background(scene):
    if scene.get("_analysis") and (scene.get("compare") or scene.get("photo")
                                   or str(scene.get("location", "")).startswith("mood_")):
        return Image.new("RGB", (W, H), "#EAF0F6")
    full = Path("full") / f"{scene['id']:03d}.png"          # cách dựng mới: tranh vẽ cả cảnh làm nền (có người sẵn)
    if scene.get("full") and full.exists():
        return place_full(Image.open(full).convert("RGB"))
    bg = Image.open(find(f"backgrounds/{scene['location']}.png")).convert("RGB")
    if scene.get("phone"):                                   # màn hình điện thoại: nền mờ để máy nổi lên
        bg = bg.filter(ImageFilter.GaussianBlur(8))
    return ImageOps.fit(bg, (W, H), Image.LANCZOS)


# ---------- vẽ một khung hình ----------

def camera(frame, kind, p, t):
    """Chuyển động của cả khung hình. p chạy từ 0 đến 1 theo chiều dài cảnh."""
    zoom, cx, cy = 1.0, 0.5, 0.5
    if kind == "zoom_in":
        zoom = 1 + 0.08 * p
    elif kind == "zoom_out":
        zoom = 1.08 - 0.08 * p
    elif kind in ("pan_left", "pan_right"):
        zoom = 1.08
        cx = 0.5 + (0.035 - 0.07 * p) * (1 if kind == "pan_left" else -1)
    elif kind == "shake":
        zoom = 1.05
        cx += 0.012 * math.sin(2 * math.pi * 9 * t)
        cy += 0.008 * math.cos(2 * math.pi * 7 * t)
    elif kind == "punch_in":                   # giật zoom vào thật nhanh rồi giữ (câu nhấn, sốc)
        zoom = 1 + 0.12 * ease_out(min(t / 0.22, 1.0))
        cy = 0.58
    elif kind in ("tilt_up", "tilt_down"):     # lia máy lên hoặc xuống
        zoom = 1.1
        cy = 0.5 + (0.04 - 0.08 * p) * (1 if kind == "tilt_up" else -1)
    elif kind in ("dolly_left", "dolly_right"):   # trượt ngang kèm zoom vào chậm
        zoom = 1.04 + 0.06 * p
        cx = 0.5 + (0.03 - 0.06 * p) * (1 if kind == "dolly_left" else -1)
    elif kind == "focus":                      # zoom chậm vào vùng mặt nhân vật
        zoom = 1 + 0.18 * ease_out(p)
        cy = 0.5 + 0.12 * ease_out(p)
    elif kind == "drift":                      # trôi nhẹ, như máy cầm tay
        zoom = 1.06
        cx += 0.012 * math.sin(2 * math.pi * 0.25 * t)
        cy += 0.008 * math.sin(2 * math.pi * 0.18 * t + 1)
    elif kind == "talk_in":                    # nhân vật cất lời: nhích máy vào ~108% thật nhanh rồi trôi rất chậm
        zoom = 1 + 0.08 * ease_out(min(t / 0.18, 1.0)) + 0.025 * p
        cy = 0.54
    elif kind == "build":                      # zoom vào chậm và nhanh dần: dồn nén trước câu chốt
        zoom = 1 + 0.10 * pytweening.easeInQuad(p)
        cy = 0.5 + 0.06 * p
    elif kind == "impact":                     # câu chốt: giật zoom ~120% gần như tức thì, rung tắt dần, giữ ~113%
        snap = min(t / 0.06, 1.0)
        zoom = 1 + 0.20 * snap - 0.07 * ease_out(min(max(t - 0.06, 0.0) / 0.5, 1.0))
        cy = 0.58
        shake = 0.016 * math.exp(-6.0 * t)
        cx += shake * math.sin(2 * math.pi * 11 * t)
        cy += shake * 0.7 * math.cos(2 * math.pi * 9 * t)
    elif kind == "dutch":                      # nghiêng khung dần (bất an, căng thẳng)
        frame = frame.rotate(4 * ease_out(p), Image.BILINEAR)
        zoom = 1.12
    if zoom == 1.0:
        return frame
    w, h = W / zoom, H / zoom
    left = min(max(cx * W - w / 2, 0), W - w)      # không để khung cắt tràn ra ngoài ảnh
    top = min(max(cy * H - h / 2, 0), H - h)
    return frame.resize((W, H), Image.BILINEAR, box=(left, top, left + w, top + h))


from render_rules import ANIMS, MOTIONS, TRANSITIONS
ANCHORS = ("center", "top", "bottom", "left", "right", "above", "head", "beside_left", "beside_right",
           "hand_left", "hand_right")


def guess_slot(name):
    """Vị trí model tự đặt tên (bottom_right, center_left...) -> [x, y] ghép từ SLOTS; không đoán được thì center."""
    parts = set(str(name).lower().replace("-", "_").split("_"))
    x = SLOTS["left"][0] if "left" in parts else SLOTS["right"][0] if "right" in parts else SLOTS["center"][0]
    y = SLOTS["top"][1] if "top" in parts else SLOTS["bottom"][1] if "bottom" in parts else SLOTS["center"][1]
    return [x, y] if parts & {"left", "right", "top", "bottom"} else "center"


def new_style_layers(scene):
    """Cách dựng mới / màn hình điện thoại: bỏ lớp ảnh nhân vật cắt rời (người đã vẽ trong tranh, hoặc cảnh là điện thoại),
    chữ / sticker neo vào lớp đã bỏ thì đặt ở góc trên phải; cảnh "phone" thêm lớp màn hình điện thoại (phone.py)."""
    changes = []
    card = None
    photo = Path("photos") / f"{scene['id']:03d}.jpg"
    if scene.get("compare"):                         # thẻ so sánh (compare.py): lớp giữa khung, mọi cách dựng
        import compare
        card = ("compare", Path("compare") / f"{scene['id']:03d}{'_analysis' if scene.get('_analysis') else ''}.png",
                0.34 if scene.get("_analysis") else 0.3)
        if scene.get("_analysis") or not card[1].exists():
            compare.render(scene["compare"], card[1])
    elif isinstance(scene.get("photo"), dict) and photo.exists():   # ảnh thật Pexels (steps/fetch_photos.py) trong khung
        import compare
        card = ("photo", photo.with_name(f"{photo.stem}_card.png"), 0.34)
        if not card[1].exists():
            compare.photo_card(photo, card[1], str(scene["photo"].get("caption") or ""))
    if card:
        if scene.get("_analysis"):
            # Bỏ cả lớp thẻ cũ nếu kịch bản đã lưu bố cục từ lần dựng trước.
            scene["layers"] = [l for l in scene.get("layers", []) if l.get("id") not in ("compare", "photo")]
        if not any(layer.get("id") == card[0] for layer in scene.get("layers", [])):
            scene.setdefault("layers", []).append({"id": card[0], "image": card[1].as_posix(), "size": card[2],
                                                   "at": [0.5, 0.57] if scene.get("_analysis") else [0.5, 0.45],
                                                   "anim": "none" if scene.get("_analysis") else "pop"})
        # hai linh vật đứng hai bên dưới thẻ / ảnh, đủ to để thấy đầu bản đồ (kịch bản hay để chồng nhau ở giữa)
        scene["motion"] = "none"                     # máy đứng yên: zoom / lia sẽ cắt mất thẻ
        sides = [[0.25, 0.83], [0.75, 0.83]]
        for layer, at in zip([x for x in scene["layers"] if Path(x.get("image", "")).parent.name == "cutouts"], sides):
            layer.update(at=at, size=half_width(layer["image"], 0.32))
            layer.pop("path", None)
    mascots = [x for x in scene.get("layers", []) if Path(x.get("image", "")).parent.name == "cutouts"
               and str(x.get("id", "")).startswith("mascot_") and "path" not in x]
    if len(mascots) == 2 and not card:   # hai linh vật: đầu bản đồ rất rộng, đứng sát nhau thì che nhau
        for layer, x in zip(mascots, (0.27, 0.73)):
            layer.update(at=[x, 0.78], size=half_width(layer["image"], 0.46))
        if scene.get("motion") in ("dolly_left", "dolly_right", "focus", "tilt_up", "tilt_down", "dutch", "pan_left",
                                   "pan_right", "talk_in"):
            scene["motion"] = "zoom_in"                  # zoom / lia mạnh cắt mất một linh vật ở mép
        scene.pop("focus", None)
    if not (scene.get("full") or scene.get("phone")):
        return changes
    layers = scene.get("layers", [])
    gone = {layer.get("id") or Path(layer["image"]).stem for layer in layers
            if "image" in layer and Path(layer["image"]).parent.name == "cutouts"}
    kept = [layer for layer in layers if not ("image" in layer and Path(layer["image"]).parent.name == "cutouts")]
    # neo vào lớp không còn trong cảnh (lớp vừa bỏ, hoặc tên nhân vật vốn không có lớp: người đã vẽ trong tranh, video 031)
    gone |= {p.split(".")[0] for layer in kept for p in ([layer.get("at")] + (layer.get("path") or []))
             if isinstance(p, str) and "." in p}
    gone -= {layer.get("id") or Path(layer["image"]).stem for layer in kept if "image" in layer}
    for layer in kept:
        for key in ("at", "path"):
            places = layer.get(key)
            listed = places if isinstance(places, list) and key == "path" else [places]
            if any(isinstance(p, str) and "." in p and p.split(".")[0] in gone for p in listed):
                layer.pop("path", None)
                layer["at"] = "top_right"
        if layer.get("on") in gone:
            layer.pop("on")
    if scene.get("phone"):
        import phone
        out = Path("phone") / f"{scene['id']:03d}.png"
        if not out.exists():
            phone.render(scene["phone"], out)
        kept.insert(0, {"id": "phone", "image": out.as_posix(), "size": 0.8, "at": [0.5, 0.56], "anim": "pop"})
    if len(kept) != len(layers) or scene.get("phone"):
        changes.append(f"cảnh {scene['id']}: {'màn hình điện thoại' if scene.get('phone') else 'tranh cả cảnh'}, "
                       f"bỏ {len(layers) - len(kept) + (1 if scene.get('phone') else 0)} lớp ảnh cắt rời")
    scene["layers"] = kept
    return changes


def half_width(image, size):
    """Cỡ (theo chiều cao khung) để lớp không rộng quá nửa khung: đầu bản đồ của linh vật rất rộng, hai lớp đứng hai bên che nhau."""
    path = Path(image)
    if not path.exists() and path.stem[4:]:             # tên viết tắt chưa sửa (052_jpn.png -> 052_mascot_jpn.png)
        found = sorted(path.parent.glob(f"{path.stem[:3]}_*{path.stem[4:]}.png"))
        path = found[0] if len(found) == 1 else path
    try:
        with Image.open(find(path)) as img:
            aspect = img.width / img.height
    except (OSError, FileNotFoundError):
        return size
    return round(min(size, 0.48 * W / H / aspect), 3)


def split_group_layer(scene, note, renamed):
    """Model gộp nhiều nhân vật vào MỘT lớp ảnh không có thật (cutouts/006_mascot_jpn_mascot_chn.png, video 045) trong khi
    mỗi nhân vật có file riêng: tách thành một lớp mỗi nhân vật (giữ anim...), đứng hai bên."""
    names = scene.get("characters") or []
    files = [Path("cutouts") / f"{scene['id']:03d}_{n}.png" for n in names]
    layers = scene.get("layers", [])
    used = {Path(x["image"]).as_posix() for x in layers if "image" in x}
    cut = [x for x in layers if Path(x.get("image", "")).parent.name == "cutouts"]
    # chỉ khi cả cảnh có đúng MỘT lớp nhân vật (lớp gộp); đủ lớp riêng mà sai tên thì để bước đổi tên lo
    if len(names) < 2 or len(cut) != 1 or not all(f.exists() for f in files) or any(f.as_posix() in used for f in files):
        return
    for k, layer in enumerate(layers):
        image = layer.get("image")
        if image and Path(image).parent.name == "cutouts" and not Path(image).exists():
            spots = ["floor_left", "floor_right"] + ["floor"] * len(names)
            parts = [{**{key: v for key, v in layer.items() if key not in ("id", "image", "at", "path")},
                      "id": n, "image": f.as_posix(), "at": spots[i]} for i, (n, f) in enumerate(zip(names, files))]
            layers[k:k + 1] = parts
            renamed[layer.get("id") or Path(image).stem] = names[0]
            note(f"{image} gộp {len(names)} nhân vật, tách thành {len(names)} lớp")
            return


def repair(script):
    """Chuẩn hóa bố cục, hiệu ứng và vị trí sau khi common đã đồng bộ ảnh chủ thể."""
    changes = []
    for scene in script["scenes"]:
        if isinstance(scene.get("compare"), dict):    # nước đem so (Nhật Bản vs nước khác, steps/01_script.py)
            scene["compare"].setdefault("country", script.get("country", "CHN"))
        def note(message):
            changes.append(f"cảnh {scene['id']}: {message}")
        renamed = {}                                    # tên cũ (id / tên file / tên nhân vật) -> id lớp ảnh sau khi sửa
        changes += new_style_layers(scene)
        for layer in scene.get("layers", []):
            if isinstance(layer.get("path"), str):    # "path": "off_right": một điểm, không phải đường đi
                place = layer.pop("path")
                if not place.startswith("off_") and "at" not in layer:
                    layer["at"] = place
                note(f"\"path\": \"{place}\" không phải danh sách điểm, "
                     + (f"dùng \"at\": \"{place}\"" if layer.get("at") == place else "bỏ (anim lo phần đi vào)"))
            for key in ("at", "path"):
                places = layer.get(key)
                if places is None:
                    continue
                listed = places if key == "path" else [places]
                fixed = [guess_slot(p) if isinstance(p, str) and "." not in p and p not in SLOTS
                         and p not in FLOOR and p not in EDGES else p for p in listed]
                if fixed != listed:
                    layer[key] = fixed if listed is places else fixed[0]
                    note(f"vị trí {places} không có, dùng {layer[key]}")
        # id lớp ảnh như check() / positions() tính: "id" nếu có, không thì tên file (lớp ảnh không ghi id vẫn bám được)
        ids = [layer.get("id") or Path(layer["image"]).stem for layer in scene.get("layers", []) if "image" in layer]
        anchor_ids = list((scene.get("effect_anchors") or {})) if scene.get("full") else []
        main = variety.main_layer(scene)
        target = (main.get("id") or Path(main["image"]).stem) if main else (ids[0] if ids else None)
        # neo vào lớp không có (thường là tên nhân vật "best_friend.beside_right" khi cảnh chỉ có cutouts/NNN.png): chuyển sang
        # lớp ảnh đổi tên ở trên, hoặc lớp ảnh chủ thể của cảnh
        for layer in scene.get("layers", []):
            if layer.get("effect"):
                continue
            for key in ("at", "path"):
                places = layer.get(key)
                listed = places if key == "path" and isinstance(places, list) else [places]
                fixed = []
                for place in listed:
                    if isinstance(place, str) and "." in place and place.split(".", 1)[0] not in ids:
                        name, anchor = place.split(".", 1)
                        to = renamed.get(name) or target
                        if to:
                            fixed.append(f"{to}.{anchor}")
                            note(f"'{place}': không có lớp '{name}', neo vào '{to}'")
                            continue
                    fixed.append(place)
                if fixed != listed:
                    layer[key] = fixed if key == "path" and isinstance(places, list) else fixed[0]
        kept = []
        # Sticker cảm xúc trùng hiệu ứng động dễ che mặt, đặc biệt trên tranh full.
        duplicate_stickers = {"tear": "tears", "sweat": "sweat", "anger": "anger",
                              "heart": "hearts", "sparkle": "sparkles"}
        active_effects = {l.get("effect") for l in scene.get("layers", [])}
        for layer in scene.get("layers", []):
            image_path = Path(layer.get("image", ""))
            if (image_path.parent.name == "stickers"
                    and duplicate_stickers.get(image_path.stem) in active_effects
                    and not any(key in layer for key in ("id", "at", "path"))):
                note(f"bỏ sticker '{image_path.stem}' trùng hiệu ứng động để không che mặt")
                continue
            kind = layer.get("effect")
            if kind in effects.KINDS:
                if not effects.KINDS[kind][0] and kind != "murmur":
                    # Hiệu ứng toàn khung không cần bám nhân vật/sticker.
                    layer.pop("on", None)
                elif scene.get("full") and layer.get("on") not in anchor_ids:
                    names = scene.get("characters") or []
                    default = scene.get("speaker") if scene.get("speaker") in names else names[0] if len(names) == 1 else "__subject"
                    if default in anchor_ids:
                        layer["on"] = default
                    elif len(anchor_ids) == 1:
                        layer["on"] = anchor_ids[0]
                    elif effects.KINDS[kind][0] or layer.get("on"):
                        raise ValueError(f"cảnh {scene['id']}: hiệu ứng '{kind}' cần điểm neo nhân vật trên tranh; chạy tools/prepare_effects.py")
            # hiệu ứng cần bám mà thiếu "on", hoặc ghi "on" trỏ vào lớp không có (vd "me": tên nhân vật) thì bám lớp ảnh của cảnh
            if kind in effects.KINDS and layer.get("on") not in ids + anchor_ids and (effects.KINDS[kind][0] or layer.get("on")):
                # Chỉ neo hiệu ứng cơ thể vào chủ thể, không chọn sticker làm người thay thế.
                subjects = [l for l in scene.get("layers", []) if Path(l.get("image", "")).parent.name == "cutouts"]
                subject = next((l for l in subjects if l.get("id") == layer.get("on")), None)
                subject = subject or main or (subjects[0] if len(subjects) == 1 else None)
                target = (subject.get("id") or Path(subject["image"]).stem) if subject else None
                if target is None:
                    note(f"bỏ hiệu ứng '{kind}': cảnh không có lớp ảnh để bám")
                    continue
                layer["on"] = target
                note(f"hiệu ứng '{kind}' bám vào '{target}'")
            kept.append(layer)
        for layer in [l for l in kept if l.get("effect") in effects.MANPU]:   # ký hiệu cảm xúc phải nằm trước mặt
            target = next((l for l in kept if l.get("id") == layer.get("on")), None)
            if target is not None and kept.index(layer) < kept.index(target):
                kept.remove(layer)
                kept.insert(kept.index(target) + 1, layer)
                note(f"hiệu ứng '{layer['effect']}' chuyển ra sau lớp '{target['id']}' để vẽ trước mặt")
        scene["layers"] = kept
    return changes


def check(script):
    """Kiểm tra kịch bản trước khi dựng: tên chuyển động, hiệu ứng, vị trí, lớp được neo vào và file ảnh
    đều hợp lệ. Trả về danh sách lỗi, mỗi lỗi ghi rõ cảnh."""
    problems = []
    for scene in script["scenes"]:
        def bad(message):
            problems.append(f"cảnh {scene['id']}: {message}")
        if scene.get("motion", "none") not in MOTIONS:
            bad(f"motion '{scene['motion']}' không có; có: {', '.join(MOTIONS)}")
        if scene.get("filter", "none") not in ("none", "sepia"):
            bad(f"filter '{scene['filter']}' không có")
        if scene.get("transition", "cut") not in TRANSITIONS:
            bad(f"transition '{scene['transition']}' không có; có: {', '.join(TRANSITIONS)}")
        if scene.get("shot", "full") not in SHOTS:
            bad(f"shot '{scene['shot']}' không có; có: {', '.join(SHOTS)}")
        layers = scene.get("layers", [])
        ids, seen = set(scene.get("effect_anchors") or {}) if scene.get("full") else set(), set()
        for index, layer in enumerate(layers):
            if "effect" not in layer:
                name = layer.get("id") or Path(layer.get("image", "word")).stem
                ids.add(name if name not in seen else f"{name}_{index}")
                seen.add(name)
        for layer in layers:
            if not any(k in layer for k in ("image", "word", "effect")):
                bad(f"lớp không có \"image\", \"word\" hay \"effect\": {layer}")
                continue
            if "effect" in layer:
                kind = layer["effect"]
                if kind not in effects.KINDS and not fx_files(fx_group(kind)):
                    bad(f"hiệu ứng '{kind}' không có; có: {', '.join(effects.KINDS)}, "
                        f"{', '.join('fx_' + d.name for d in sorted(FX_DIR.glob('*')) if d.is_dir())}")
                elif kind in effects.KINDS and effects.KINDS[kind][0] and layer.get("on") not in ids:
                    bad(f"hiệu ứng '{kind}' cần \"on\" là id một lớp trong cảnh (có: {', '.join(sorted(ids))})")
                continue
            if layer.get("anim", "none") not in ANIMS:
                bad(f"anim '{layer['anim']}' không có; có: {', '.join(ANIMS)}")
            if "image" in layer and not (Path(layer["image"]).exists() or (LIBRARY / layer["image"]).exists()):
                bad(f"không có file ảnh {layer['image']}")
            size = layer.get("size")
            if "image" in layer and size is not None and size not in SIZES and not isinstance(size, (int, float)):
                bad(f"size '{size}' không có; có: {', '.join(SIZES)} hoặc số")
            for place in layer.get("path") or ([layer["at"]] if "at" in layer else []):
                if isinstance(place, list):
                    if len(place) != 2:
                        bad(f"vị trí {place} phải là [x, y]")
                elif place in SLOTS or place in FLOOR or place in EDGES:
                    pass
                elif "." in place:
                    target, anchor_name = place.split(".", 1)
                    if target not in ids:
                        bad(f"'{place}': không có lớp id '{target}' (có: {', '.join(sorted(ids))})")
                    if anchor_name not in ANCHORS:
                        bad(f"'{place}': điểm neo '{anchor_name}' không có; có: {', '.join(ANCHORS)}")
                else:
                    bad(f"vị trí '{place}' không có")
    return problems


def parent_of(layer):
    """Lớp đứng neo vào lớp khác ("at": "father.hand_left") thì đi theo lớp đó; trả về id lớp cha."""
    at = layer.get("at")
    return at.split(".")[0] if isinstance(at, str) and "." in at and not layer.get("path") else None


def timing(layer, t, length):
    """(giây kể từ lúc lớp xuất hiện, thời gian tồn tại của lớp)."""
    return t - layer.get("start", 0.0), layer.get("duration", length - layer.get("start", 0.0))


def positions(layers, t, length):
    """Lượt 1: vị trí và tỉ lệ hiện tại của mọi lớp ảnh, kể cả lớp vẽ sau, để hiệu ứng nằm sau nhân vật
    (vẽ trước) vẫn biết nhân vật đang ở đâu. Trả về id lớp -> (vị trí đứng yên, vị trí hiện tại, tỉ lệ, độ lệch, anim)."""
    moves, waiting = {}, [item for item in layers if not item.get("effect")]
    while waiting:
        before = len(waiting)
        for item in list(waiting):
            layer, points = item["layer"], item["points"]
            parent_id = parent_of(layer)
            if parent_id in by_ids(layers) and parent_id not in moves:
                continue                                   # chờ lớp cha được tính trước
            local, life = timing(layer, t, length)
            travel = layer.get("over", 0.8) if len(points) > 1 else 0.0
            px, py = along(points, min(max(local, 0.0) / travel, 1.0) if travel else 1.0)
            dx, dy, scale, angle, alpha = animate(layer.get("anim", "none"), max(local - travel, 0.0),
                                                  max(life - travel, 0.01))
            parent = moves.get(parent_id)
            if parent:      # giữ đúng chỗ trên lớp cha khi lớp cha di chuyển hoặc phóng to
                (rx, ry), (cx, cy), s = parent[:3]
                px, py = cx + (px - rx) * s, cy + (py - ry) * s
                scale *= s
            moves[item["id"]] = (points[-1], (px + dx, py + dy), scale, angle, alpha)
            waiting.remove(item)
        if len(waiting) == before:                         # không còn lớp nào tính được (không xảy ra nếu check() qua)
            break
    return moves


def by_ids(layers):
    return {item["id"] for item in layers if not item.get("effect")}


def effect_box(item, moves, lookup):
    """Khung (pixel) của lớp được hiệu ứng bám theo: tâm, rộng, cao, tâm đầu, bán kính đầu."""
    if "anchor_box" in item:
        return item["anchor_box"]
    target = item["layer"].get("on")
    if not target:
        return None
    parent, (_, (cx, cy), s) = lookup[target], moves[target][:3]
    w, h = parent["img"].width * s, parent["img"].height * s
    cx, cy = cx * W, cy * H
    shape = parent["shape"]
    if not shape:
        return cx, cy, w, h, cx, cy - h * 0.3, w * 0.3
    left, right, head_y = shape["head"]
    return (cx, cy, w, h, cx + ((left + right) / 2 - parent["img"].width / 2) * s,
            cy + (head_y - parent["img"].height / 2) * s, (right - left) / 2 * s)


def render_frame(scene, bg, layers, t, length):
    frame = bg.copy()
    moves = positions(layers, t, length)
    lookup = {item["id"]: item for item in layers}
    for item in layers:                                    # lượt 2: vẽ theo đúng thứ tự trong "layers"
        layer = item["layer"]
        local, life = timing(layer, t, length)
        if local < 0 or local > life:
            continue
        if item.get("fx"):
            frame = fx_blend(frame, item, local, life)
            continue
        if item.get("effect"):
            effects.draw(frame, layer["effect"], local, life, effect_box(item, moves, lookup), (W, H),
                         layer.get("colour"), seed=item["seed"], text=layer.get("text"),
                         occlude=bool(scene.get("full") and "anchor_box" in item))
            continue
        _, (px, py), scale, angle, alpha = moves[item["id"]]
        img, key = item["img"], "main"
        if "alt" in item and (int(local / ALT_LOOP) % 2 if item.get("alt_loop")    # đi, chạy, vẫy: luân phiên
                              else local >= life * ALT_SWITCH):                     # còn lại: đổi một lần giữa câu
            img, key = item["alt"], "alt"
        img = face_frame(scene, item, img, key, t)
        travel = layer.get("over", 0.8) if len(item["points"]) > 1 else 0.0
        sx, sy, jelly = deform(layer.get("anim", "none"), max(local - travel, 0.0), max(life - travel, 0.01))
        lean = 0.0
        if IDLE and not scene.get("_analysis") and item.get("character") and layer.get("anim", "none") not in IDLE_SKIP:
            breath, lean = idle(t, sum(map(ord, item["id"])))
            sy *= breath
        drop = 0.0                                         # co giãn dọc giữ chân trên mặt đất
        if lean and not jelly:
            height = max(round(img.height * scale * sy), 1)
            drop = (img.height * scale - height) / 2
            img = lean_over(img, lean, scale * sx, scale * sy)
        elif scale != 1.0 or sx != 1.0 or sy != 1.0:
            height = max(round(img.height * scale * sy), 1)
            drop = (img.height * scale - height) / 2
            img = img.resize((max(round(img.width * scale * sx), 1), height), Image.BILINEAR)
        if jelly:
            img = jiggle(img, jelly, local)
        if angle:
            img = img.rotate(angle, Image.BICUBIC, expand=True)
        if alpha < 1.0:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a: round(a * alpha)))
        frame.paste(img, (round(px * W - img.width / 2), round(py * H - img.height / 2 + drop)), img)
    if scene.get("filter") == "sepia":
        frame = ImageOps.colorize(ImageOps.grayscale(frame), "#2B1D0E", "#F3E3C3")
    if scene.get("_focus"):                    # hai cú máy trong cảnh: thay cho chuyển động máy quay thường
        return focus_camera(frame, scene, t, length)
    return camera(frame, scene.get("motion", "none"), t / length, t)


# ---------- hiệu ứng âm thanh (library/sfx, tạo bằng tools/make_sfx.py) ----------

SFX_VOLUME = VIDEO.get("sfx_volume", 1.0)
AMBIENT_VOLUME = VIDEO.get("ambient_volume", 1.0)
SFX_BELOW = VIDEO.get("sfx_below_voice", 12)       # dB: hiệu ứng luôn nhỏ hơn giọng nói của cảnh
AMBIENT_BELOW = VIDEO.get("ambient_below_voice", 22)


def loudness(x):
    """Độ to (RMS) của phần có tiếng: bỏ các đoạn im lặng để tiếng ngắn (ポン) và tiếng dài (mưa) so được với nhau."""
    if x is None or not len(x):
        return 0.0
    block = 480                                     # 10 ms ở 48 kHz
    n = len(x) // block * block
    frames = x[:n].reshape(-1, block) if n else x.reshape(1, -1)
    energy = np.sqrt((frames ** 2).mean(axis=1))
    loud = energy[energy > energy.max() * 0.1] if energy.max() > 0 else energy
    return float(np.sqrt((loud ** 2).mean())) if len(loud) else 0.0


def match_gain(sound, voice_level, below_db, peak_limit):
    """Hệ số nhân để sound nhỏ hơn giọng below_db dB, và đỉnh không vượt peak_limit (một nửa đỉnh giọng)."""
    level = loudness(sound)
    if level <= 0 or voice_level <= 0:
        return 0.0
    gain = voice_level * 10 ** (-below_db / 20) / level
    peak = float(np.abs(sound).max()) * gain
    return gain * min(1.0, peak_limit / peak) if peak > 0 else gain
# tên bối cảnh (tiếng Anh, vd "station_platform_morning") chứa từ khóa -> nhóm tiếng nền; dò theo thứ tự, gặp đầu tiên là dùng.
# Trong nhà yên tĩnh (bếp, phòng ngủ, văn phòng, bệnh viện) không có tiếng nền; "morning"/"evening"/"night" chỉ là dự phòng.
AMBIENT = [("storm", "amb_storm"), ("thunder", "amb_storm"), ("rain", "amb_rain"), ("snow", "amb_wind"),
           ("train_car", "amb_train"), ("train_inside", "amb_train"), ("bus", "amb_street"),
           ("station", "amb_station"), ("platform", "amb_station"), ("airport", "amb_airport"),
           ("classroom", "amb_school"), ("school_ground", "amb_ground"), ("schoolyard", "amb_ground"), ("gym", "amb_ground"),
           ("courtyard", "amb_ground"), ("ground", "amb_ground"),
           ("festival", "amb_festival"), ("firework", "amb_festival"),
           ("supermarket", "amb_store"), ("convenience", "amb_store"), ("drugstore", "amb_store"), ("pharmacy", "amb_store"),
           ("store", "amb_store"), ("shop", "amb_store"), ("mall", "amb_store"), ("market", "amb_store"),
           ("bakery", "amb_store"), ("bookstore", "amb_store"),
           ("restaurant", "amb_restaurant"), ("ramen", "amb_restaurant"), ("cafe", "amb_restaurant"), ("izakaya", "amb_restaurant"),
           ("beach", "amb_sea"), ("seaside", "amb_sea"), ("sea", "amb_sea"), ("ocean", "amb_sea"), ("coast", "amb_sea"),
           ("port", "amb_port"), ("harbor", "amb_port"), ("fishing", "amb_port"), ("pier", "amb_port"),
           ("river", "amb_river"), ("stream", "amb_river"), ("park", "amb_park"), ("playground", "amb_park"),
           ("downtown", "amb_city"), ("city", "amb_city"), ("shopping", "amb_city"), ("crowd", "amb_city"),
           ("street", "amb_street"), ("road", "amb_street"), ("crossing", "amb_street"), ("town", "amb_street"),
           ("neighborhood", "amb_street"), ("gate", "amb_street"), ("country", "amb_country"), ("field", "amb_country"),
           ("forest", "amb_country"), ("mountain", "amb_country"), ("rice", "amb_country"), ("shrine", "amb_country"),
           ("wind", "amb_wind"), ("dining", "amb_home_meal")]
QUIET = ("kitchen", "bedroom", "office", "hospital", "room", "apartment", "genkan", "hallway", "bathroom", "toilet",
         "living", "inside")
AMBIENT_TIME = [("night", "amb_night"), ("morning", "amb_morning"), ("dusk", "amb_evening"), ("evening", "amb_evening"),
                ("sunset", "amb_evening")]


def ambient_for(location):
    """Nhóm tiếng nền của một bối cảnh, hoặc None (trong nhà yên tĩnh / không khớp). So khớp theo từng từ của tên
    (tách bằng "_"), không theo chuỗi con: "train_car" không bị nhận là "rain", "stationery_shop" không là "station"."""
    name = f"_{(location or '').lower()}_"
    has = lambda word: f"_{word}_" in name or f"_{word}s_" in name      # noqa: E731  (chấp nhận số nhiều)
    for word, group in AMBIENT:
        if has(word):
            return group
    if any(has(word) for word in QUIET):
        return None
    return next((group for word, group in AMBIENT_TIME if has(word)), None)
SFX_TRANSITION = {"push_left": "whoosh", "push_right": "whoosh", "push_up": "whoosh", "zoom": "whoosh",
                  "wipe": "whoosh", "iris": "whoosh", "whip": "swish", "flash": "dodon"}
SFX_EFFECT = {"fx_sparkle": "kiran", "fx_glitter": "kiran", "fx_magic": "kiran", "fx_gold": "shakin",
              "flash": "dodon", "speed_lines": "don", "gloom": "gaan", "tears": "tear",
              "sparkles": "kiran", "hearts": "kiran", "confetti": "fanfare", "aura": "aura", "rays": "shakin",
              "sweat": "hyu", "anger": "don", "shock_lines": "gaan", "idea": "pikon", "sigh": "shoboon",
              "dizzy": "hatena"}
SFX_STICKER = {"exclaim": "bikkuri", "question": "hatena", "sweat": "hyu", "gloom": "shoboon", "tear": "tear",
               "anger": "don", "lines": "gaan", "heart": "kiran", "spark": "pikon", "sparkle": "kiran"}
# chỉ gắn tiếng cho chuyển động có chủ ý (kịch bản ghi); kiểu nhún variety.py tự chọn thì im lặng (video 009: quá nhiều ボヨン)
SFX_ANIM = {"punch": "don", "jump": "boyon", "spin_in": "warp", "squash": "boyon", "jelly": "boyon",
            "puff": "don", "deflate": "shoboon", "stretch_up": "bikkuri"}
SFX_MAX_PER_NAME = {"whoosh": 3}               # mỗi tiếng tối đa 4 lần một video (trừ tiếng ghi ở đây)
SFX_SHARE = 0.3                                  # tổng số tiếng ~30% số cảnh; cảnh cảm xúc mạnh (variety.add_reaction) luôn được kêu
SFX_STRONG = {"dodon", "jan", "gaan", "don", "kaisou", "whoosh", "heartbeat", "fall", "punch", "slap", "wrong", "correct"}
# chữ tượng thanh trong kịch bản -> nhóm tiếng (khớp phần đầu chữ); "" = cố ý im lặng (シーン)
SFX_WORD = [("シーン", ""), ("ドドン", "dodon"), ("ドキ", "heartbeat"), ("ゴゴゴ", "gogogo"), ("ガーン", "gaan"),
            ("ズーン", "shoboon"), ("ショボ", "shoboon"), ("チーン", "chiin"), ("ドン", "don"), ("ドーン", "don"),
            ("バン", "don"), ("バーン", "don"), ("ドカ", "don"), ("ジャーン", "jan"), ("ジャン", "jan"), ("ピコ", "pikon"),
            ("ピン", "pikon"), ("ハッ", "bikkuri"), ("エッ", "bikkuri"), ("キラ", "kiran"), ("ピカ", "kiran"),
            ("シャキ", "shakin"), ("ボヨ", "boyon"), ("ピョン", "boyon"), ("ヒュー", "hyu"), ("ピュー", "hyu"),
            ("ダッ", "dash"), ("ダダ", "dash"), ("タタ", "dash"), ("ブル", "shiver"), ("カタカタ", "shiver"),
            ("ガクガク", "shiver"), ("ズキ", "guki"), ("グキ", "guki"), ("ポロ", "tear"), ("ポタ", "drop"),
            ("ジャラ", "money"), ("チャリ", "money"), ("ガチャ", "door"), ("ギィ", "door"),
            ("コンコン", "knock"), ("トントン", "knock"), ("スタスタ", "walk"), ("テクテク", "walk"),
            ("ビシ", "tsukkomi"), ("ズコ", "zukkoke"), ("ズテ", "zukkoke"),
            ("ガタン", "train"), ("ゴトン", "train"), ("プシュ", "train_door"), ("ジリリ", "bell"), ("リリリ", "bell"),
            ("プルル", "phone"), ("ピロ", "phone"), ("ブーッ", "vibe"), ("ヴー", "vibe"), ("パシャ", "camera"),
            ("カシャ", "camera"), ("カタカタカタ", "keyboard"), ("カチッ", "click"), ("ポチ", "click"),
            ("バシッ", "punch"), ("ボコ", "punch"), ("ドゴ", "punch"), ("ゴッ", "punch"), ("パチン", "slap"),
            ("ビンタ", "slap"), ("バタン", "fall"), ("ドサ", "fall"), ("ブン", "swish"), ("シュッ", "swish"),
            ("ヒュン", "swish"), ("ピンポーン", "correct"), ("ピンポン", "correct"), ("ブブー", "wrong"),
            ("ブッブー", "wrong"), ("ピロン", "message"), ("ピコン", "message"), ("ピッ", "beep"), ("ビー", "warning"),
            ("チクタク", "timer"), ("ドゥルル", "drumroll"), ("ゾク", "horror"), ("ヒィ", "horror"),
            ("パクッ", "eat"), ("モグ", "eat"), ("ムシャ", "eat"), ("ゴクッ", "eat"), ("ジャジャーン", "jan"),
            ("パンパカ", "fanfare"), ("ホッ", "heal"), ("ほっ", "heal"), ("ノビ", "stretch"), ("グイ", "stretch")]
SFX_ALIAS = {"boom": "dodon", "shock": "don", "ding": "pikon", "sparkle": "kiran", "pop": "pon"}   # tên cũ
SFX_PRIORITY = ["dodon", "jan", "gaan", "don", "kaisou", "chiin", "shakin", "heartbeat", "gogogo", "whoosh", "swish",
                "bikkuri", "pikon", "hatena", "shoboon", "tear", "hyu", "dash", "guki", "door", "money", "knock",
                "punch", "slap", "fall", "fanfare", "horror", "wrong", "correct", "aura", "warp", "slowmo", "heal",
                "drumroll", "timer", "warning", "success", "message", "beep", "eat", "stretch",
                "tsukkomi", "zukkoke", "shiver", "train", "train_door", "bell", "phone", "vibe", "camera", "keyboard", "click",
                "kiran", "boyon", "walk", "drop", "pon", "chanchan"]


def word_sfx(word):
    for prefix, name in sorted(SFX_WORD, key=lambda x: -len(x[0])):   # khớp chữ dài trước (カタカタカタ trước カタカタ)
        if prefix in word:
            return name
    return ""                                       # chữ không có tiếng hợp: im lặng (trước đây mọi chữ đều kêu ポン)


# Tiếng theo NỘI DUNG câu (chữ tiếng Nhật trong lời, hoặc tiếng Anh trong action): tiếng của chính sự việc trong cảnh,
# hợp lý nhất nên được ưu tiên như tiếng ghi tay. Khớp mục đầu tiên. Nhóm tiếng: library/sfx/lab/<tên>.
SFX_TEXT = [
    (("着信", "電話が鳴", "スマホが鳴", "phone ringing", "phone rings"), "phone"),
    (("メッセージが届", "通知が", "メールが届", "message notification"), "message"),
    (("ノック", "knocking"), "knock"),
    (("ドアを開", "扉を開", "ドアが開", "玄関を開", "opening the door", "opens the door"), "door"),
    (("チャイム", "ベルが鳴", "school bell"), "bell"),
    (("走って", "走り", "駆け", "急いで", "running", "rushing"), "dash"),
    (("歩いて", "歩き", "walking"), "walk"),
    (("食べ", "弁当", "ご飯を", "いただきます", "eating", "biting"), "eat"),
    (("写真を撮", "シャッター", "taking a photo", "taking a picture"), "camera"),
    (("財布", "お金", "給料", "小銭", "wallet", "coins"), "money"),
    (("電車", "train"), "train"),
    (("パソコン", "キーボード", "typing"), "keyboard"),
    (("ドキドキ", "胸が高鳴", "鼓動", "heart pounding"), "heartbeat"),
    (("時計", "時間がない", "締め切り", "looking at the clock", "clock"), "timer"),
    (("転ん", "倒れ", "falling down", "trips"), "fall"),
    (("ビンタ", "叩か", "slapping"), "slap"),
    (("不合格", "間違い", "ハズレ", "失敗"), "wrong"),
    (("合格", "正解", "当たり"), "correct"),
    (("優勝", "おめでとう", "やったー", "celebrating"), "fanfare"),
    (("なんでやねん", "ツッコ"), "tsukkomi"),
    (("ずっこけ",), "zukkoke"),
    (("泣い", "涙", "泣き", "crying", "tears"), "tear"),
    (("怖", "恐ろし", "ゾッと", "horror"), "horror"),
    (("ほっと", "安心", "relieved"), "heal"),
    (("ひらめ", "思いつ", "そうだ！", "idea"), "pikon"),
]


SFX_TEXT_MAX = 2


def text_sfx(scene, japanese_only=False):
    """Tiếng hợp với nội dung câu (lời tiếng Nhật, action tiếng Anh), hoặc None. japanese_only: chỉ xét lời thoại
    (action tiếng Anh hay đoán sai: "typing on phone" thành gõ phím, "eating" ở câu không liên quan)."""
    text = str(scene.get("text", ""))
    action = "" if japanese_only else str(scene.get("action", "")).lower()
    for keys, name in SFX_TEXT:
        if any(k in text or k.lower() in action for k in keys):
            return name
    return None


# Tiếng chỉ khi THẬT cần (góp ý video 024: 36 tiếng / 48 cảnh, nhiều tiếng sai nghĩa: tiếng ăn ở câu "gọi điện cho trường",
# gõ phím, bước chân, ドドン ở cảnh khóc). Không còn tự gắn theo chuyển cảnh, hiệu ứng, sticker, động tác, cảm xúc, hay đoán
# theo action tiếng Anh. Chỉ: tiếng kịch bản ghi rõ ("sfx"), chữ tượng thanh có trên hình, câu thoại nhắc sự việc có tiếng
# thật (SFX_REAL), câu chốt (impact), vào twist, vào hồi tưởng, kết video hài.
SFX_REAL = {"phone", "message", "knock", "door", "bell", "camera", "fall", "slap", "train", "fanfare", "correct", "wrong",
            "tsukkomi", "zukkoke"}
SFX_SPARSE_SHARE = 0.1          # tiếng tự gắn tối đa ~10% số cảnh (tiếng ghi tay, chữ tượng thanh không tính)
SFX_SPARSE_MAX = 2              # mỗi tiếng tối đa 2 lần / video


def sfx_events(scene, has_previous):
    """Các tiếng (tên, giây) của một cảnh, thưa: chỉ khi thật cần (xem SFX_REAL). Tối đa 1 tiếng một cảnh (ghi tay: 2)."""
    if scene.get("_analysis"):
        return [(str(name), 0.0) for name in (scene.get("sfx") or [])[:1]]
    must, auto = [], []
    for item in scene.get("sfx", []) or []:                # kịch bản ghi rõ: luôn dùng
        if isinstance(item, str):
            must.append((SFX_ALIAS.get(item, item), 0.0))
        elif isinstance(item, dict) and item.get("name"):
            must.append((SFX_ALIAS.get(item["name"], item["name"]), float(item.get("at", 0))))
    for layer in scene.get("layers", []):                   # chữ tượng thanh hiện trên hình thì có tiếng đúng chữ đó
        if "word" in layer:
            name = word_sfx(str(layer["word"]))
            if name:
                must.append((name, float(layer.get("start", 0) or 0) + 0.05))
    previous = scene.get("_previous") or {}
    real = text_sfx(scene, japanese_only=True)
    if real in SFX_REAL:
        auto.append((real, 0.15))                           # câu nhắc sự việc có tiếng thật: chuông, gõ cửa, chụp ảnh...
    card = scene.get("compare")
    if isinstance(card, dict):                              # thẻ so sánh bật ra: "jan", bên thắng: đúng / sai
        must.append(("jan", 0.0))
        must.append(("correct" if card.get("winner") == "japan" else "wrong" if card.get("winner") == "other" else "boyon",
                     0.55))
    if scene.get("motion") == "impact" or scene.get("_index") == 0:
        auto.append(("dodon", 0.0))                         # câu chốt; móc câu: tiếng nện ngay giây đầu
    if scene.get("beat") == "twist" and previous.get("beat") != "twist":
        auto.append(("jan", 0.0))
    if scene.get("filter") == "sepia" and previous.get("filter") != "sepia":
        auto.append(("kaisou", 0.0))
    if scene.get("_last") and "hài" in str(scene.get("_genre", "")).lower():
        auto.append(("chanchan", 0.3))
    used = dict(previous.get("_sfx_used", {}))
    recent = set(previous.get("_sfx_names", [])) | set((previous.get("_previous") or {}).get("_sfx_names", []))
    auto_used = previous.get("_sfx_auto", 0)
    budget = SFX_SPARSE_SHARE * (scene.get("_index", 0) + 1) + 1
    picked = list(dict.fromkeys(must))[:2]
    if not picked:
        for name, at in auto:
            if used.get(name, 0) < SFX_SPARSE_MAX and name not in recent and auto_used < budget:
                picked = [(name, at)]
                auto_used += 1
                break
    for name, _ in picked:
        used[name] = used.get(name, 0) + 1
    scene["_sfx_used"], scene["_sfx_auto"] = used, auto_used
    scene["_sfx"] = len(picked)
    scene["_sfx_names"] = [name for name, _ in picked]
    return picked


def read_wav(path):
    import wave
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            return None, 0
        data = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        if w.getnchannels() == 2:
            data = data.reshape(-1, 2).mean(axis=1)
        return data, w.getframerate()


SFX_BANNED = {l.strip() for l in (LIBRARY / "sfx" / "banned.txt").read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.startswith("#")} if (LIBRARY / "sfx" / "banned.txt").exists() else set()   # tiếng bị loại


def sfx_file(name, seed):
    """Tiếng thật tải từ 効果音ラボ (library/sfx/lab/<nhóm>/, nhiều phiên bản, chọn luân phiên theo cảnh);
    nhóm chưa có thì dùng tiếng tạo bằng code library/sfx/<nhóm>.wav."""
    choices = sorted(f for f in (LIBRARY / "sfx" / "lab" / name).glob("*.wav") if f.stem not in SFX_BANNED)
    if choices:
        return choices[seed % len(choices)]
    return LIBRARY / "sfx" / f"{name}.wav"


def mix_sfx(audio, events, length, out, seed=0, ambient=None, offset=0.0):
    """Trộn hiệu ứng âm thanh và tiếng nền (ambient: nhóm amb_*, offset: giây của cảnh trong video, để tiếng nền nối liền
    qua các cảnh) vào giọng đọc, ghi ra out. Không có tiếng nào hoặc lỗi thì trả về file giọng gốc."""
    ambient_file = None
    if ambient and AMBIENT_VOLUME > 0:
        files = sorted((LIBRARY / "sfx" / "lab" / ambient).glob("*.wav"))
        ambient_file = files[sum(map(ord, ambient)) % len(files)] if files else None
    if (not events or SFX_VOLUME <= 0) and not ambient_file:
        return audio
    if not all(sfx_file(name, 0).exists() for name, _ in events):
        subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "tools" / "make_sfx.py")], check=False)
    voice, rate = read_wav(audio)
    if voice is None:
        return audio
    mix = np.zeros(int((length + 0.5) * rate), np.float32)
    mix[: len(voice)] += voice[: len(mix)]
    voice_level = loudness(voice) or 0.1             # cảnh không có giọng: lấy mức giọng thường gặp
    voice_peak = float(np.abs(voice).max()) if len(voice) else 0.5
    if ambient_file:
        bed, bed_rate = read_wav(ambient_file)
        if bed is not None and bed_rate == rate and len(bed):
            index = (int(offset * rate) + np.arange(len(mix))) % len(bed)     # lặp lại, tiếp đúng chỗ cảnh trước dừng
            mix += bed[index] * match_gain(bed, voice_level, AMBIENT_BELOW, voice_peak * 0.2) * AMBIENT_VOLUME
    if SFX_VOLUME <= 0:
        events = []
    limit = 0.95                                    # giọng + hiệu ứng + nền cộng lại có thể vượt đỉnh: hạ cả đoạn cho khỏi méo
    for k, (name, at) in enumerate(events):
        path = sfx_file(name, seed + k)
        if not path.exists():
            continue
        sound, sound_rate = read_wav(path)
        if sound is None or sound_rate != rate:
            continue
        start = int(max(at, 0) * rate)
        piece = sound[: max(len(mix) - start, 0)] * match_gain(sound, voice_level, SFX_BELOW, voice_peak * 0.75) * SFX_VOLUME
        mix[start:start + len(piece)] += piece
    peak = float(np.abs(mix).max()) if len(mix) else 0.0
    if peak > limit:
        mix *= limit / peak
    import wave
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    return out


def render_clip(scene, font_file, audio, clip, previous=None):
    """Vẽ từng khung hình của một cảnh và đẩy thẳng vào ffmpeg cùng giọng đọc.
    previous: khung hình cuối của cảnh trước, để chuyển cảnh trong TRANSITION giây đầu.
    Trả về (độ dài cảnh, khung hình cuối)."""
    frames = round((duration(audio) + scene.get("_pad", PAD) + scene.get("_hold", 0.0)) * FPS)
    length = frames / FPS
    bg, layers = background(scene), load_layers(scene, font_file)
    moving = clip_backgrounds(scene)                       # nền là clip image-to-video thay cho tranh tĩnh
    scene["_mouth"] = mouth_track(audio, frames)          # miệng nhân vật đang nói mở theo tiếng của chính câu này
    kind = scene.get("transition", "cut")
    blend = round(TRANSITION * FPS) if previous is not None and kind != "cut" else 0
    audio = mix_sfx(audio, sfx_events(scene, previous is not None), length, clip.with_name(f"{clip.stem}_mix.wav"),
                    seed=scene["id"] * 7, ambient=scene.get("ambient", ambient_for(scene.get("location"))),
                    offset=scene.get("_clock", 0.0))
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(audio), "-af", f"apad=whole_dur={length}", "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", str(clip)], stdin=subprocess.PIPE)
    frame = None
    for i in range(frames):
        frame = render_frame(scene, moving[min(i, len(moving) - 1)] if moving else bg, layers, i / FPS, length)
        if i < blend:
            frame = transition(kind, previous, frame, (i + 1) / (blend + 1))
        ffmpeg.stdin.write(frame.tobytes())
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError(f"ffmpeg lỗi ở cảnh {scene['id']}")
    return length, frame


def transition(kind, before, after, p):
    """Khung hình chuyển cảnh: before = khung cuối cảnh trước, after = khung hiện tại, p từ 0 đến 1."""
    e = ease_out(p)
    if kind == "fade":
        return Image.blend(before, after, p)
    if kind in ("push_left", "push_right", "push_up", "whip"):
        out = Image.new("RGB", (W, H))
        if kind == "push_up":
            shift = round(H * e)
            out.paste(before, (0, -shift))
            out.paste(after, (0, H - shift))
        else:
            sign = 1 if kind in ("push_left", "whip") else -1
            shift = round(W * e)
            out.paste(before, (-sign * shift, 0))
            out.paste(after, (sign * (W - shift), 0))
        if kind == "whip":                     # lia nhanh: nhòe theo chiều ngang, mạnh nhất ở giữa
            blur = 40 * math.sin(math.pi * p)
            if blur > 1:
                small = out.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.BoxBlur(blur / 8))
                out = Image.blend(out, small.resize((W, H), Image.BILINEAR), 0.7 * math.sin(math.pi * p))
        return out
    if kind == "zoom":                         # khung cũ phóng to và mờ đi, lộ khung mới
        z = 1 + 0.5 * e
        w, h = W / z, H / z
        zoomed = before.resize((W, H), Image.BILINEAR, box=((W - w) / 2, (H - h) / 2, (W + w) / 2, (H + h) / 2))
        return Image.blend(zoomed, after, p)
    if kind == "flash":                        # chớp trắng rồi hiện khung mới
        white = Image.new("RGB", (W, H), "white")
        return Image.blend(before, white, p * 2) if p < 0.5 else Image.blend(white, after, (p - 0.5) * 2)
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    if kind == "wipe":                         # quét chéo: tam giác lớn dần từ góc trái dưới
        edge = (W + H) * e
        d.polygon([(0, H), (edge, H), (0, H - edge)], fill=255)
    elif kind == "iris":                       # vòng tròn mở rộng từ giữa
        r = math.hypot(W, H) / 2 * e
        d.ellipse((W / 2 - r, H * 0.55 - r, W / 2 + r, H * 0.55 + r), fill=255)
    return Image.composite(after, before, mask)


# ---------- phụ đề ----------

def ass_colour(hex_colour):
    r, g, b = hex_colour[1:3], hex_colour[3:5], hex_colour[5:7]
    return f"&H00{b}{g}{r}".upper()


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def wrap(text, size):
    """Ngắt dòng phụ đề tiếng Nhật (libass không tự ngắt vì không có dấu cách): mỗi dòng vừa bề rộng khung,
    các dòng dài gần bằng nhau, ưu tiên ngắt ngay sau dấu câu."""
    if "\n" in text:                                 # người viết tự đặt chỗ ngắt: giữ, chỉ ngắt thêm dòng quá dài
        return r"\N".join(wrap(part, size) for part in text.split("\n"))
    per_line = max(int((W - 2 * VIDEO["subtitle_margin"]) / size), 1)   # chữ Nhật rộng đúng bằng cỡ chữ
    if len(text) <= per_line or (len(text) == per_line + 1 and text[-1] in "、。！？!?…」"):
        return text                                  # dấu câu cuối dòng được tràn ra lề (quy tắc ngắt dòng tiếng Nhật)
    # Chọn cách ngắt cả câu tốt nhất (quy hoạch động): ít dòng, ngắt ở chỗ tự nhiên, các dòng không lệch nhau quá
    n = len(text)
    best = {0: (0.0, [])}
    for i in range(1, n + 1):
        options = []
        for j in range(max(0, i - per_line - 1), i):
            if j not in best:
                continue
            width = i - j
            if width > per_line and not (width == per_line + 1 and text[i - 1] in "、。！？!?…」"):
                continue                            # dấu câu cuối dòng được tràn ra lề, chữ khác thì không
            cost = best[j][0] + 12                  # mỗi dòng thêm bị phạt: ưu tiên ít dòng
            if j:
                cost += break_cost(text, j)
            if i < n:
                cost += (per_line - width) ** 2 * 0.15   # dòng giữa câu quá ngắn trông lệch
            options.append((cost, best[j][1] + [text[j:i]]))
        if options:
            best[i] = min(options)
    return r"\N".join(best[n][1])


PARTICLES = "はがをにでともへのやね"
NO_START = "、。！？!?…ーっゃゅょぁぃぅぇぉッャュョァィゥェォ）」』～"


def kind_of(ch):
    if "\u3040" <= ch <= "\u309f":
        return "hira"
    if "\u30a0" <= ch <= "\u30ff":
        return "kata"
    if "\u4e00" <= ch <= "\u9fff" or ch in "々〆":
        return "kanji"
    return "other"


def break_cost(text, k):
    """Độ "xấu" khi ngắt dòng giữa text[k-1] và text[k]: thấp là chỗ ngắt tự nhiên."""
    a, b = text[k - 1], text[k]
    if b in NO_START or a in "「『（":
        return 100                                  # dòng không mở đầu bằng dấu câu, kana nhỏ; không ngắt sau ngoặc mở
    if a in "、。！？!?…）」":
        return 0                                    # sau dấu câu: tốt nhất
    ka, kb = kind_of(a), kind_of(b)
    if ka == "hira" and a in PARTICLES and kb in ("kanji", "kata"):
        return 2                                    # sau trợ từ, trước từ mới: 席を｜譲らない
    if ka != kb and kb in ("kanji", "kata") and ka != "other":
        return 4                                    # đổi loại chữ sang chữ Hán / Katakana
    if ka == "kanji" and kb == "hira":
        return 30                                   # giữa chữ Hán và đuôi chữ: 握｜る
    if ka == kb == "hira":
        return 20                                   # giữa một cụm Hiragana: 譲らな｜かった
    if ka == kb and ka in ("kanji", "kata"):
        return 25                                   # giữa một từ chữ Hán / Katakana: 突｜然
    return 10


def deepen(colour, factor=0.62):
    """Làm đậm màu speaker (thường là màu pastel) để chữ màu trên viền trắng đọc rõ."""
    colour = colour.lstrip("#")
    r, g, b = (int(colour[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{round(c * factor):02X}" for c in (r, g, b))


TITLE_SECOND_LINE = 0.8                            # dòng 2 tiêu đề nhỏ hơn dòng 1 (như video mẫu 感動の迷言集 / 七歳の手)
TITLE_SIDE = 100                                   # lề trái phải tối thiểu của tiêu đề (px); 40 -> 100: thụt vào
TITLE_TOP = 70                                     # đẩy tiêu đề xuống (px): thanh trên cùng của TikTok che mép trên khung


def title_sizes(title_lines, font_file, band, base=None):
    """Cỡ chữ từng dòng tiêu đề: dòng 1 title_size, các dòng sau nhỏ hơn; dòng nào dài quá bề ngang thì co lại cho vừa
    (đo bằng chính font, tính cả viền), tổng chiều cao không vượt dải đen."""
    base = VIDEO["title_size"] if base is None else base
    try:
        measure = ImageFont.truetype(font_file, 100) if font_file else None
    except OSError:
        measure = None
    # libass: cỡ chữ ASS = chiều cao dòng (ascent + descent) của font, không phải cỡ em như Pillow -> quy đổi
    em = 100 / sum(measure.getmetrics()) if measure else 0.69
    sizes = []
    for k, text in enumerate(title_lines):
        size = base if k == 0 else round(base * TITLE_SECOND_LINE)
        if measure:
            width100 = measure.getlength(text)
        else:                                       # không có font: chữ toàn khổ (Nhật) rộng 1 em, chữ thường ~0,55 em
            width100 = sum(100 if ord(c) > 0x2E7F else 55 for c in text)
        # bề rộng ở cỡ ASS size = width100/100 * em * size, cộng viền hai bên (size/11 mỗi bên) và 4% cho chữ đậm
        fit = (W - 2 * TITLE_SIDE) / (width100 / 100 * em * 1.04 + 2 / 11) if width100 else size
        sizes.append(max(min(size, int(fit)), 36))
    if band and sum(sizes) > band - 20 - TITLE_TOP:  # cao quá phần dải đen dưới thanh TikTok: thu đều cho vừa
        scale = (band - 20 - TITLE_TOP) / sum(sizes)
        sizes = [max(int(s * scale), 36) for s in sizes]
    return sizes


def write_subtitles(script, timings, total, path):
    """Như video mẫu: dải đen trên cùng chứa tiêu đề chữ vàng viền nâu; phụ đề chữ màu viền trắng dày, ngay dưới dải.
    Lời kể (narrator) màu xanh dương; lời thoại (speaker khác) màu của nhân vật, làm đậm."""
    from analysis_profile import video_options
    options = video_options(script, VIDEO)
    font, size = script.get("font", "Arial"), options["subtitle_size"]
    from analysis_profile import enabled
    analysis = enabled(script)
    outline, margin = (4 if analysis else max(round(size / 7), 6)), options["subtitle_margin"]
    band = options.get("title_band", 0)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        "Style: Band,Arial,10,&H00000000,&H00000000,&H00000000,0,1,0,0,7,0,0,0",
    ]
    title_lines = [str(t) for t in script.get("title", []) if str(t).strip()]
    sizes = title_sizes(title_lines, font_path(script), band, base=options["title_size"])
    title_colour = "&H00FFFFFF" if analysis else "&H0042CFFF"
    lines.append(f"Style: Title,{font},{options['title_size']},{title_colour},&H000E1C30,&H80000000,1,1,"
                 f"{max(round(options['title_size'] / 11), 6)},3,8,20,20,"
                 f"{max(round((band - TITLE_TOP - sum(sizes)) / 2), 6) + TITLE_TOP if band else 90}")
    for name, colour in script["speakers"].items():
        text_colour = "#1F2A4D" if analysis else VIDEO.get("narration_colour", "#2747F5") if name == "narrator" else deepen(colour)
        lines.append(f"Style: {name},{font},{size},{ass_colour(text_colour)},&H00FFFFFF,"
                     f"&H64000000,1,1,{outline},2,8,{margin},{margin},{options['subtitle_top']}")
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Text"]
    if band:                                        # dải đen tiêu đề: hình chữ nhật vẽ bằng lệnh vẽ của ASS
        lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Band,{{\\pos(0,0)\\p1}}m 0 0 l {W} 0 {W} {band} 0 {band}{{\\p0}}")
    # mỗi dòng tiêu đề một cỡ chữ riêng (co cho vừa bề ngang), viền theo cỡ chữ
    title = r"\N".join(f"{{\\fs{s}\\bord{max(round(s / 11), 4)}}}{t}" for t, s in zip(title_lines, sizes))
    if title:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(total)},Title,{title}")
    for scene, (start, end) in zip(script["scenes"], timings):
        lines.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},{scene['speaker']},{wrap(scene['text'], size)}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------- nhạc nền (library/bgm, tools/fetch_bgm.py) ----------

BGM_BY_GENRE = [("2ch", "kandou"), ("cảm động", "kandou"), ("gia đình", "kandou"), ("ngụ ngôn", "kandou"),
                ("bài học", "kandou"), ("buồn", "kanashii"), ("hài", "comical"), ("đời thường", "honobono"),
                ("bí ẩn", "ayashii"), ("hồi hộp", "ayashii"), ("kinh dị", "ayashii"), ("tình yêu", "honobono"),
                ("thanh xuân", "honobono"), ("công sở", "serious"), ("xã hội", "serious"), ("trả thù", "serious"),
                ("スカッと", "serious"), ("công lý", "serious")]


def pick_music(script):
    """music.mp3 của video nếu có; không thì bài trong library/bgm/<nhóm> theo thể loại ("bgm" trong kịch bản ghi đè,
    "none" để tắt). Mỗi video một bài cố định (chọn theo tên thư mục)."""
    if Path("music.mp3").exists():
        return Path("music.mp3")
    group = script.get("bgm")
    if group == "none":
        return None
    if group and group.endswith(".mp3") and (LIBRARY / "bgm" / group).exists():   # bài cố định: "comical/retroparty.mp3"
        return LIBRARY / "bgm" / group
    if not group:
        genre = str(script.get("genre", "")).lower()
        group = next((g for word, g in BGM_BY_GENRE if word in genre), "kandou")
    tracks = sorted((LIBRARY / "bgm" / group).glob("*.mp3"))
    if not tracks:
        return None
    return tracks[sum(map(ord, Path.cwd().name)) % len(tracks)]


MUSIC_LOUDER = {"comical": 14, "honobono": 18}   # nhạc hài, ấm áp to hơn (video mẫu 愛彼女弁当: nhạc gần ngang giọng)
MUSIC_BREAK = 0.7                                  # giây tắt nhạc ở đầu cảnh chốt


def music_breaks(script, timings):
    """Khoảng (bắt đầu, kết thúc) tắt nhạc: đầu cảnh chốt (vào twist, cảnh rung / chớp, hoặc "music_stop": true trong
    kịch bản). Học video mẫu 愛彼女弁当: nhạc im bặt ~0,6 giây đúng câu chốt rồi vào lại."""
    out = []
    if script.get("country"):                       # video so sánh: nhạc chạy liền, không tắt (người dùng thấy như khoảng nghỉ)
        return out
    for prev, scene, (start, end) in zip([None] + script["scenes"][:-1], script["scenes"], timings):
        twist = scene.get("beat") == "twist" and (prev or {}).get("beat") != "twist"
        hit = scene.get("motion") in ("shake", "impact") or scene.get("transition") == "flash"
        if scene.get("music_stop") or twist or hit:
            out.append((start, min(start + MUSIC_BREAK, end)))
    return out[:4]                                  # tối đa 4 lần một video, không thì thành vụn


MIN_SECONDS = VIDEO.get("min_seconds", 61.0)     # độ dài tối thiểu của video (giây), [video] min_seconds
NEW_STYLE_MUSIC_BELOW = 13      # dB, cách dựng mới


def music_gain(track, voice_files, group=""):
    """Hệ số âm lượng để nhạc nhỏ hơn giọng đọc music_below_voice dB (đo độ to cả hai)."""
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(track), "-t", "90", "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "-"], capture_output=True).stdout
    music = np.frombuffer(decoded, "<i2").astype(np.float32) / 32768
    voices = [read_wav(f)[0] for f in voice_files]
    voice = np.concatenate([v for v in voices if v is not None]) if voices else np.zeros(1)
    level_music, level_voice = loudness(music), loudness(voice)
    if level_music <= 0 or level_voice <= 0:
        return MUSIC_VOLUME
    below = MUSIC_LOUDER.get(group, VIDEO.get("music_below_voice", 18))
    return level_voice * 10 ** (-below / 20) / level_music


# ---------- chương trình chính ----------

def preview(script):
    """Xuất một ảnh tĩnh cho mỗi cảnh, không cần giọng đọc. Dùng để duyệt bố cục."""
    PREVIEW.mkdir(parents=True, exist_ok=True)
    font_file = font_path(script)
    for scene in script["scenes"]:
        length = 1.5
        frame = render_frame(scene, background(scene), load_layers(scene, font_file), length * 0.6, length)
        frame.save(PREVIEW / f"{scene['id']:03d}.png")
    print(f"Đã xuất {len(script['scenes'])} ảnh vào {PREVIEW.as_posix()}/")


def main():
    script = json.loads(Path("script.json").read_text(encoding="utf-8"))
    from common import summarize_changes
    for line in summarize_changes(normalize_script(script, Path.cwd())):   # gộp các dòng "bỏ null" cho log gọn
        print("  sửa kịch bản:", line)
    from common import asset_problems, missing_script_images
    problems = asset_problems(script, Path.cwd())
    problems += [f"thiếu {p}" for p in missing_script_images(Path.cwd(), script)]
    if problems:
        sys.exit("Chưa đủ nguồn ảnh để dựng; chạy bước lên danh sách ảnh và sinh ảnh:\n  " + "\n  ".join(problems))
    sys.path.insert(0, str(ROOT / "tools"))
    from prepare_effects import prepare
    script = variety.fill(script)                  # điền chuyển động còn trống
    prepare(Path.cwd(), script=script)
    for line in repair(script):                    # tên ảnh, "on" của hiệu ứng, vị trí model đặt sai
        print("  sửa kịch bản:", line)
    problems = check(script)
    if problems:                                   # dừng trước khi dựng, không ra video lỗi hiệu ứng
        sys.exit("Kịch bản có lỗi, sửa rồi chạy lại:\n  " + "\n  ".join(problems))
    for warning in variety.report(script):         # chỉ cảnh báo: chuyển động lặp nhiều cảnh liền
        print("Cảnh báo:", warning)
    if "--preview" in sys.argv:
        return preview(script)
    TMP.mkdir(parents=True, exist_ok=True)
    font_file = font_path(script)
    clips, timings, clock, last = [], [], 0.0, None
    # video phải trên 1 phút (TikTok tính tiền từ 60 giây): thiếu thì cảnh cuối (câu hỏi cho người xem) giữ thêm, không chèn
    # khoảng nghỉ giữa video. Video so sánh đọc nhanh, không tự đọc chậm lại nên hay hụt (048: 57,4 giây).
    from analysis_profile import video_options
    pad = video_options(script, VIDEO)["pad"]
    for scene in script["scenes"]:
        scene["_pad"] = pad
    planned = sum(duration(Path("audio") / f"{s['id']:03d}.wav") + pad for s in script["scenes"])
    script["scenes"][-1]["_hold"] = max(0.0, MIN_SECONDS - planned)
    if script["scenes"][-1]["_hold"]:
        print(f"Giọng + nghỉ {planned:.1f} giây < {MIN_SECONDS}: cảnh cuối giữ thêm {script['scenes'][-1]['_hold']:.1f} giây")
    for previous, scene in zip([None] + script["scenes"][:-1], script["scenes"]):
        scene["_previous"] = previous             # cảnh trước: để gắn tiếng khi đổi bối cảnh, vào twist
        scene["_last"], scene["_genre"] = scene is script["scenes"][-1], script.get("genre", "")
        scene["_clock"] = clock                   # giây bắt đầu cảnh: tiếng nền nối liền qua các cảnh
        scene["_scene_count"] = len(script["scenes"])
        scene["_index"] = script["scenes"].index(scene)
        name = f"{scene['id']:03d}"
        clip = TMP / f"{name}.mp4"
        length, last = render_clip(scene, font_file, Path("audio") / f"{name}.wav", clip, last)
        clips.append(clip)
        timings.append((clock, clock + length))
        clock += length
        print(f"cảnh {name}: {length:.2f}s")

    concat = TMP / "concat.txt"
    concat.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = TMP / "joined.mp4"
    run("-f", "concat", "-safe", 0, "-i", concat, "-c", "copy", joined)

    subs = TMP / "subs.ass"
    write_subtitles(script, timings, clock, subs)
    (Path("work") / "timings.json").write_text(json.dumps(       # giây đầu / cuối từng cảnh: trang web chọn "cảnh đang xem"
        [{"id": s["id"], "start": round(a, 2), "end": round(b, 2)} for s, (a, b) in zip(script["scenes"], timings)]))
    video_filter = f"ass={subs.as_posix()}"
    if font_file:                                  # cho libass tìm font phụ đề; đường dẫn tương đối để tránh "D:" trong filter
        video_filter += f":fontsdir={Path(os.path.relpath(Path(font_file).parent)).as_posix()}"
    common = ["-c:v", "libx264", "-preset", "medium", "-crf", 20, "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", "output.mp4"]
    music = pick_music(script)
    if music:
        gain = music_gain(music, [Path("audio") / f"{s['id']:03d}.wav" for s in script["scenes"]], music.parent.name)
        if script.get("style") == "new":                  # như video mẫu: nhạc nền rõ, ~13 dB dưới giọng (đo 11-14 dB)
            below = MUSIC_LOUDER.get(music.parent.name, VIDEO.get("music_below_voice", 18))
            gain *= 10 ** ((below - NEW_STYLE_MUSIC_BELOW) / 20)
        if script.get("music_quieter"):                   # chỉnh tay từng video: nhạc nhỏ đi thêm N dB (video 048: 4)
            gain *= 10 ** (-float(script["music_quieter"]) / 20)
        breaks = music_breaks(script, timings)
        print(f"Nhạc nền: {music.parent.name}/{music.name}, âm lượng x{gain:.3f}, tắt nhạc ở "
              f"{', '.join(f'{a:.1f}s' for a, _ in breaks) or 'không chỗ nào'}")
        silence = "".join(f",volume=0:enable='between(t,{a:.2f},{b:.2f})'" for a, b in breaks)
        run("-i", joined, "-stream_loop", -1, "-i", music, "-filter_complex",
            f"[0:v]{video_filter}[v];[1:a]volume={gain:.4f}{silence},afade=t=in:d=1.5,"
            f"afade=t=out:st={max(clock - 2.5, 0):.2f}:d=2.5[m];"
            f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "[v]", "-map", "[a]", "-t", clock, *common)
    else:
        run("-i", joined, "-vf", video_filter, *common)
    print(f"Xong: output.mp4 ({clock:.1f}s, {len(clips)} cảnh)")


if __name__ == "__main__":
    main()
