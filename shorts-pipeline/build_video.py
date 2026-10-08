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
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

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
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


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

def ease_out(p):
    return 1 - (1 - p) ** 3


def overshoot(p):
    """0 → 1, vượt quá 1 một chút rồi về lại, tạo cảm giác bật ra."""
    c = 1.70158
    return 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2


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
        dy = -(1 - ease_out(min(t / 0.45, 1.0))) * 0.6
    elif kind == "slide_left":                 # trượt vào từ bên trái
        dx = -(1 - ease_out(enter)) * 0.8
    elif kind == "slide_right":                # trượt vào từ bên phải
        dx = (1 - ease_out(enter)) * 0.8
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
        p = ease_out(min(t / 0.5, 1.0))
        angle, scale = 360 * (1 - p), max(p, 0.01)
    elif kind == "lean_in":                    # chồm tới gần người xem
        p = ease_out(min(t / 0.6, 1.0))
        scale, dy = 1 + 0.07 * p, 0.015 * p
    elif kind == "rise":                       # trồi lên từ mép dưới khung
        dy = (1 - ease_out(min(t / 0.45, 1.0))) * 0.45
    return dx, dy, scale, angle, alpha


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


def with_shot(scene, layer):
    """Lớp nhân vật chính của cảnh (cutouts/NNN...png) bỏ trống size, at thì lấy theo "shot" của cảnh."""
    image = Path(layer.get("image", ""))
    if image.parent.name != "cutouts" or not image.stem.startswith(f"{scene['id']:03d}"):
        return layer
    shot = SHOTS[scene.get("shot", "full")]
    layer = dict(layer)
    layer.setdefault("size", shot["size"])
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
            items.append({"layer": layer, "img": None, "id": f"effect_{index}", "effect": True, "shape": None,
                          "points": [(0.5, 0.5)], "seed": scene["id"] * 100 + index})
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
        item = {"layer": layer, "img": img, "id": name, "shape": silhouette(img) if "image" in layer else None}
        if scene.get("alt_pose") and "image" in layer:   # tư thế thứ hai: cutouts/003.png -> cutouts/003_alt.png
            alt = Path(layer["image"])
            alt = alt.with_name(f"{alt.stem}_alt{alt.suffix}")
            if Path(alt).exists() or (LIBRARY / alt).exists():
                item["alt"] = fit_height(find(alt), img.height)
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
    return items


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


def background(scene):
    bg = Image.open(find(f"backgrounds/{scene['location']}.png")).convert("RGB")
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
    elif kind == "dutch":                      # nghiêng khung dần (bất an, căng thẳng)
        frame = frame.rotate(4 * ease_out(p), Image.BILINEAR)
        zoom = 1.12
    if zoom == 1.0:
        return frame
    w, h = W / zoom, H / zoom
    left = min(max(cx * W - w / 2, 0), W - w)      # không để khung cắt tràn ra ngoài ảnh
    top = min(max(cy * H - h / 2, 0), H - h)
    return frame.resize((W, H), Image.BILINEAR, box=(left, top, left + w, top + h))


ANIMS = ("none", "bounce", "wobble", "pulse", "pop", "pop_fade", "drop", "slide_left", "slide_right",
         "exit_left", "exit_right", "approach", "recede", "jump",
         "nod", "shake_no", "sway", "tilt", "breathe", "shiver", "hop", "sink", "float", "punch", "spin_in",
         "lean_in", "rise")
MOTIONS = ("zoom_in", "zoom_out", "pan_left", "pan_right", "shake", "none",
           "punch_in", "tilt_up", "tilt_down", "dolly_left", "dolly_right", "focus", "drift", "dutch")
TRANSITIONS = ("cut", "fade", "push_left", "push_right", "push_up", "whip", "zoom", "flash", "wipe", "iris")
ANCHORS = ("center", "top", "bottom", "left", "right", "above", "head", "beside_left", "beside_right",
           "hand_left", "hand_right")


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
        ids, seen = set(), set()
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
                if kind not in effects.KINDS:
                    bad(f"hiệu ứng '{kind}' không có; có: {', '.join(effects.KINDS)}")
                elif effects.KINDS[kind][0] and layer.get("on") not in ids:
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
        if item.get("effect"):
            effects.draw(frame, layer["effect"], local, life, effect_box(item, moves, lookup), (W, H),
                         layer.get("colour"), seed=item["seed"])
            continue
        _, (px, py), scale, angle, alpha = moves[item["id"]]
        img = item["img"]
        if "alt" in item and int(local / ALT_INTERVAL) % 2:   # hai tư thế luân phiên
            img = item["alt"]
        if scale != 1.0:
            img = img.resize((max(round(img.width * scale), 1), max(round(img.height * scale), 1)), Image.BILINEAR)
        if angle:
            img = img.rotate(angle, Image.BICUBIC, expand=True)
        if alpha < 1.0:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a: round(a * alpha)))
        frame.paste(img, (round(px * W - img.width / 2), round(py * H - img.height / 2)), img)
    if scene.get("filter") == "sepia":
        frame = ImageOps.colorize(ImageOps.grayscale(frame), "#2B1D0E", "#F3E3C3")
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
SFX_EFFECT = {"flash": "dodon", "speed_lines": "don", "gloom": "gaan", "tears": "tear",
              "sparkles": "kiran", "hearts": "kiran", "confetti": "fanfare", "aura": "aura", "rays": "shakin"}
SFX_STICKER = {"exclaim": "bikkuri", "question": "hatena", "sweat": "hyu", "gloom": "shoboon", "tear": "tear",
               "anger": "don", "lines": "gaan", "heart": "kiran", "spark": "pikon", "sparkle": "kiran"}
# chỉ gắn tiếng cho chuyển động có chủ ý (kịch bản ghi); kiểu nhún variety.py tự chọn thì im lặng (video 009: quá nhiều ボヨン)
SFX_ANIM = {"punch": "don", "jump": "boyon", "spin_in": "warp"}
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


def sfx_events(scene, has_previous):
    """Các tiếng (tên, giây) của một cảnh: ghi tay trong "sfx" của cảnh, cộng với tiếng tự gắn theo chuyển cảnh,
    rung khung, hiệu ứng, chữ tượng thanh và sticker. Tối đa 3 tiếng, mỗi tên một lần."""
    events = []
    for item in scene.get("sfx", []) or []:
        if isinstance(item, str):
            events.append((SFX_ALIAS.get(item, item), 0.0))
        elif isinstance(item, dict) and item.get("name"):
            events.append((SFX_ALIAS.get(item["name"], item["name"]), float(item.get("at", 0))))
    kind = scene.get("transition", "cut")
    previous = scene.get("_previous") or {}
    if has_previous and kind in SFX_TRANSITION:
        events.append((SFX_TRANSITION[kind], 0.0))
    elif has_previous and previous.get("location") not in (None, scene.get("location")):
        events.append(("whoosh", 0.0))            # đổi bối cảnh bằng cắt thẳng / mờ: vẫn có tiếng lướt
    if scene.get("beat") == "twist" and previous.get("beat") != "twist":
        events.append(("jan", 0.0))               # vào cú twist: ジャン!
    if scene.get("motion") in ("shake", "punch_in"):
        events.append(("don", 0.0))               # ドン
    if scene.get("_last") and "hài" in str(scene.get("_genre", "")).lower():
        events.append(("chanchan", 0.3))          # kết video hài: チャンチャン
    if scene.get("filter") == "sepia" and previous.get("filter") != "sepia":
        events.append(("kaisou", 0.0))            # vào đoạn hồi tưởng
    for layer in scene.get("layers", []):
        start = float(layer.get("start", 0) or 0)
        image = Path(str(layer.get("image", "")))
        if "effect" in layer and layer["effect"] in SFX_EFFECT:
            events.append((SFX_EFFECT[layer["effect"]], start))
        elif image.parent.name == "stickers":
            if image.stem in SFX_STICKER:
                events.append((SFX_STICKER[image.stem], start + 0.05))
        elif "word" in layer:
            name = word_sfx(str(layer["word"]))
            if name:
                events.append((name, start + 0.05))
        elif layer.get("path"):
            events.append(("swish", start))         # nhân vật / đồ vật bay vào khung
        elif layer.get("anim") in SFX_ANIM and layer.get("_auto_anim") is not True:
            events.append((SFX_ANIM[layer["anim"]], start))
    chosen, seen = [], set()
    manual = len(scene.get("sfx", []) or [])
    for k, (name, at) in enumerate(events):
        if name in seen:
            continue
        seen.add(name)
        chosen.append((k >= manual, SFX_PRIORITY.index(name) if name in SFX_PRIORITY else 99, name, at))
    chosen.sort()                                   # tiếng ghi tay trước, rồi theo độ ưu tiên
    picked = [(name, at) for _, _, name, at in chosen]
    # không lặp cùng một tiếng trong 3 cảnh liền (video 009: ガーン 7 lần, ドン 6 lần); tiếng chuyển cảnh đổi bối cảnh vẫn giữ
    recent = set((previous or {}).get("_sfx_names", [])) | set(((previous or {}).get("_previous") or {}).get("_sfx_names", []))
    picked = [e for k, e in enumerate(picked) if k < manual or e[0] == "whoosh" or e[0] not in recent]
    strong = [e for e in picked if e[0] in SFX_STRONG]
    # thưa: mỗi cảnh 1 tiếng, cao trào (tiếng mạnh) được 2; cảnh trước vừa có tiếng thì cảnh này chỉ kêu nếu là tiếng mạnh
    emotional = bool(scene.get("_emotion_fx"))      # bất ngờ, khóc, khoe...: tiếng là một phần của phản ứng
    if (previous or {}).get("_sfx") and not strong and manual == 0 and not emotional:
        picked = []
    picked = picked[:2] if strong else picked[:1]
    # giới hạn cả video: mỗi tiếng tối đa 3 lần, tổng ~45% số cảnh (đếm dồn qua các cảnh trước, cao trào được ưu tiên)
    used = dict((previous or {}).get("_sfx_used", {}))
    total = sum(used.values())
    count = scene.get("_scene_count", 40)
    budget = SFX_SHARE * (scene.get("_index", count - 1) + 1) + 1   # chia đều theo tiến độ video: không dồn hết vào nửa đầu
    keep = []
    for k, (name, at) in enumerate(picked):
        if k >= manual and used.get(name, 0) >= SFX_MAX_PER_NAME.get(name, 4):
            continue
        if (k >= manual and total + len(keep) >= budget and scene.get("beat") not in ("twist", "climax")
                and not emotional):
            continue
        keep.append((name, at))
    picked = keep
    for name, _ in picked:
        used[name] = used.get(name, 0) + 1
    scene["_sfx_used"] = used
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


def sfx_file(name, seed):
    """Tiếng thật tải từ 効果音ラボ (library/sfx/lab/<nhóm>/, nhiều phiên bản, chọn luân phiên theo cảnh);
    nhóm chưa có thì dùng tiếng tạo bằng code library/sfx/<nhóm>.wav."""
    choices = sorted((LIBRARY / "sfx" / "lab" / name).glob("*.wav"))
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
    frames = round((duration(audio) + PAD) * FPS)
    length = frames / FPS
    bg, layers = background(scene), load_layers(scene, font_file)
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
        frame = render_frame(scene, bg, layers, i / FPS, length)
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
TITLE_SIDE = 40                                    # lề trái phải tối thiểu của tiêu đề (px)


def title_sizes(title_lines, font_file, band):
    """Cỡ chữ từng dòng tiêu đề: dòng 1 title_size, các dòng sau nhỏ hơn; dòng nào dài quá bề ngang thì co lại cho vừa
    (đo bằng chính font, tính cả viền), tổng chiều cao không vượt dải đen."""
    base = VIDEO["title_size"]
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
    if band and sum(sizes) > band - 20:             # cao quá dải đen: thu đều cho vừa
        scale = (band - 20) / sum(sizes)
        sizes = [max(int(s * scale), 36) for s in sizes]
    return sizes


def write_subtitles(script, timings, total, path):
    """Như video mẫu: dải đen trên cùng chứa tiêu đề chữ vàng viền nâu; phụ đề chữ màu viền trắng dày, ngay dưới dải.
    Lời kể (narrator) màu xanh dương; lời thoại (speaker khác) màu của nhân vật, làm đậm."""
    font, size = script.get("font", "Arial"), VIDEO["subtitle_size"]
    outline, margin = max(round(size / 7), 6), VIDEO["subtitle_margin"]   # viền trắng dày như video mẫu
    band = VIDEO.get("title_band", 0)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        "Style: Band,Arial,10,&H00000000,&H00000000,&H00000000,0,1,0,0,7,0,0,0",
    ]
    title_lines = [str(t) for t in script.get("title", []) if str(t).strip()]
    sizes = title_sizes(title_lines, font_path(script), band)
    lines.append(f"Style: Title,{font},{VIDEO['title_size']},&H0042CFFF,&H000E1C30,&H80000000,1,1,"
                 f"{max(round(VIDEO['title_size'] / 11), 6)},3,8,20,20,"
                 f"{max(round((band - sum(sizes)) / 2), 6) if band else 90}")
    for name, colour in script["speakers"].items():
        text_colour = VIDEO.get("narration_colour", "#2747F5") if name == "narrator" else deepen(colour)
        lines.append(f"Style: {name},{font},{size},{ass_colour(text_colour)},&H00FFFFFF,"
                     f"&H64000000,1,1,{outline},2,8,{margin},{margin},{VIDEO['subtitle_top']}")
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
    if not group:
        genre = str(script.get("genre", "")).lower()
        group = next((g for word, g in BGM_BY_GENRE if word in genre), "kandou")
    tracks = sorted((LIBRARY / "bgm" / group).glob("*.mp3"))
    if not tracks:
        return None
    return tracks[sum(map(ord, Path.cwd().name)) % len(tracks)]


MUSIC_LOUDER = {"comical": 11, "honobono": 15}   # nhạc hài, ấm áp to hơn (video mẫu 愛彼女弁当: nhạc gần ngang giọng)
MUSIC_BREAK = 0.7                                  # giây tắt nhạc ở đầu cảnh chốt


def music_breaks(script, timings):
    """Khoảng (bắt đầu, kết thúc) tắt nhạc: đầu cảnh chốt (vào twist, cảnh rung / chớp, hoặc "music_stop": true trong
    kịch bản). Học video mẫu 愛彼女弁当: nhạc im bặt ~0,6 giây đúng câu chốt rồi vào lại."""
    out = []
    for prev, scene, (start, end) in zip([None] + script["scenes"][:-1], script["scenes"], timings):
        twist = scene.get("beat") == "twist" and (prev or {}).get("beat") != "twist"
        hit = scene.get("motion") == "shake" or scene.get("transition") == "flash"
        if scene.get("music_stop") or twist or hit:
            out.append((start, min(start + MUSIC_BREAK, end)))
    return out[:4]                                  # tối đa 4 lần một video, không thì thành vụn


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
    for line in summarize_changes(normalize_script(script)):   # gộp các dòng "bỏ null" cho log gọn
        print("  sửa kịch bản:", line)
    script = variety.fill(script)                  # điền chuyển động còn trống
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
