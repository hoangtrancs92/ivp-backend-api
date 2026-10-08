"""Dựng video dọc theo lớp: nền + nhân vật + đạo cụ + sticker + chữ, mỗi lớp chuyển động riêng.

Chạy trong thư mục của video (cần ffmpeg và ffprobe trong PATH, và Pillow):
  python ../../build_video.py             dựng output.mp4
  python ../../build_video.py --preview   chỉ xuất một ảnh tĩnh cho mỗi cảnh vào scenes/ để duyệt bố cục

Đầu vào:
  script.json                 kịch bản, mỗi cảnh có danh sách "layers"
  backgrounds/<location>.png  ảnh nền
  cutouts/, props/            nhân vật và đạo cụ đã tách nền
  audio/001.wav               giọng đọc từng cảnh
  music.mp3                   nhạc nền (không bắt buộc)
File không có trong thư mục video thì tìm trong ../../library/ (nền và sticker dùng chung).

Một lớp trong "layers" được đặt bằng tên, không cần tọa độ:
  {"id": "father", "image": "cutouts/001.png", "size": "large", "path": ["off_left", "center"], "anim": "bounce"}
  {"id": "beer", "image": "props/beer.png", "size": "medium", "at": "father.hand_left", "anim": "wobble"}
  {"image": "props/ice.png", "size": "tiny", "path": ["off_left", "father.above", "beer.top"], "over": 1.0}
  {"word": "キンキンで", "at": "father.beside_right", "vertical": true, "anim": "pop_fade", "start": 0.4}
at:    tên vị trí trong SLOTS, hoặc "<id lớp khác>.<điểm neo>", hoặc [x, y] theo tỉ lệ khung hình
path:  danh sách các vị trí như trên; lớp đi qua lần lượt trong "over" giây rồi mới chạy anim
size:  tên trong SIZES, hoặc chiều cao theo tỉ lệ khung hình
anim:  none | bounce | wobble | pulse | pop | pop_fade | drop | slide_left | slide_right
motion: (cả khung hình) zoom_in | zoom_out | pan_left | pan_right | shake | none
filter: none | sepia
"""
import json
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
PAD = 0.15           # giây nghỉ sau mỗi câu
MUSIC_VOLUME = 0.12  # nhạc nền so với giọng đọc
LIBRARY = Path("../../library")

# Vị trí có tên: tâm của lớp theo tỉ lệ khung hình (x, y)
SLOTS = {
    "center": (0.50, 0.70), "left": (0.28, 0.72), "right": (0.72, 0.72),
    "top": (0.50, 0.40), "top_left": (0.20, 0.40), "top_right": (0.80, 0.40), "bottom": (0.50, 0.86),
    "off_left": (-0.35, 0.72), "off_right": (1.35, 0.72), "off_top": (0.50, -0.25), "off_bottom": (0.50, 1.25),
}
# Kích thước có tên: chiều cao của lớp so với khung hình
SIZES = {"tiny": 0.07, "small": 0.15, "medium": 0.24, "large": 0.42, "huge": 0.50}
TMP = Path("build_tmp")


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
    return dx, dy, scale, angle, alpha


def word_image(layer, font_file):
    """Vẽ chữ tượng thanh thành một ảnh trong suốt, để xử lý như mọi lớp ảnh khác."""
    size = layer.get("size", 64)
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


def anchor(centre, img, name):
    """Điểm neo trên một lớp khác, tính từ vị trí dừng và kích thước của lớp đó."""
    (cx, cy), w, h = centre, img.width / W, img.height / H
    top = cy - h / 2
    return {
        "center": (cx, cy), "top": (cx, top), "bottom": (cx, cy + h / 2),
        "left": (cx - w / 2, cy), "right": (cx + w / 2, cy),
        "above": (cx, top - 0.08), "head": (cx, top + 0.18 * h),
        "beside_left": (cx - w / 2 - 0.08, top + 0.20 * h), "beside_right": (cx + w / 2 + 0.08, top + 0.20 * h),
        "hand_left": (cx - 0.38 * w, top + 0.62 * h), "hand_right": (cx + 0.38 * w, top + 0.62 * h),   # ước lượng
    }[name]


def resolve(place, placed):
    """Đổi một vị trí viết bằng tên thành tọa độ (x, y)."""
    if not isinstance(place, str):
        return tuple(place)
    if place in SLOTS:
        return SLOTS[place]
    target, name = place.split(".")
    return anchor(*placed[target], name)       # KeyError nếu lớp kia chưa được đặt


def load_layers(scene, font_file):
    """Nạp ảnh của từng lớp, thu về đúng kích thước và tính các điểm trên đường đi. Làm một lần mỗi cảnh."""
    items = []
    for layer in scene.get("layers", []):
        if "word" in layer:
            img = word_image(layer, font_file)
        else:
            img = Image.open(find(layer["image"])).convert("RGBA")
            size = layer.get("size", "medium")
            target = round(SIZES.get(size, size) * H)
            img = img.resize((max(round(img.width * target / img.height), 1), target), Image.LANCZOS)
        name = layer.get("id") or Path(layer.get("image", "word")).stem
        items.append({"layer": layer, "img": img, "id": name})

    placed, waiting = {}, list(items)          # một lớp có thể neo vào lớp khai báo sau nó
    while waiting:
        before = len(waiting)
        for item in list(waiting):
            places = item["layer"].get("path") or [item["layer"].get("at", "center")]
            try:
                item["points"] = [resolve(place, placed) for place in places]
            except KeyError:
                continue
            placed[item["id"]] = (item["points"][-1], item["img"])
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
    if zoom == 1.0:
        return frame
    w, h = W / zoom, H / zoom
    left = min(max(cx * W - w / 2, 0), W - w)      # không để khung cắt tràn ra ngoài ảnh
    top = min(max(cy * H - h / 2, 0), H - h)
    return frame.resize((W, H), Image.BILINEAR, box=(left, top, left + w, top + h))


def render_frame(scene, bg, layers, t, length):
    frame = bg.copy()
    for item in layers:
        layer, img, points = item["layer"], item["img"], item["points"]
        local = t - layer.get("start", 0.0)
        life = layer.get("duration", length - layer.get("start", 0.0))
        if local < 0 or local > life:
            continue
        travel = layer.get("over", 0.8) if len(points) > 1 else 0.0
        px, py = along(points, min(local / travel, 1.0) if travel else 1.0)
        dx, dy, scale, angle, alpha = animate(layer.get("anim", "none"), max(local - travel, 0.0), life)
        if scale != 1.0:
            img = img.resize((max(round(img.width * scale), 1), max(round(img.height * scale), 1)), Image.BILINEAR)
        if angle:
            img = img.rotate(angle, Image.BICUBIC, expand=True)
        if alpha < 1.0:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda a: round(a * alpha)))
        x = round((px + dx) * W - img.width / 2)
        y = round((py + dy) * H - img.height / 2)
        frame.paste(img, (x, y), img)
    if scene.get("filter") == "sepia":
        frame = ImageOps.colorize(ImageOps.grayscale(frame), "#2B1D0E", "#F3E3C3")
    return camera(frame, scene.get("motion", "none"), t / length, t)


def render_clip(scene, font_file, audio, clip):
    """Vẽ từng khung hình của một cảnh và đẩy thẳng vào ffmpeg cùng giọng đọc."""
    frames = round((duration(audio) + PAD) * FPS)
    length = frames / FPS
    bg, layers = background(scene), load_layers(scene, font_file)
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(audio), "-af", f"apad=whole_dur={length}", "-frames:v", str(frames),
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ar", "48000", "-ac", "2", str(clip)], stdin=subprocess.PIPE)
    for i in range(frames):
        ffmpeg.stdin.write(render_frame(scene, bg, layers, i / FPS, length).tobytes())
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError(f"ffmpeg lỗi ở cảnh {scene['id']}")
    return length


# ---------- phụ đề ----------

def ass_colour(hex_colour):
    r, g, b = hex_colour[1:3], hex_colour[3:5], hex_colour[5:7]
    return f"&H00{b}{g}{r}".upper()


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_subtitles(script, timings, total, path):
    font = script.get("font", "Arial")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        f"Style: Title,{font},92,&H0066D9FF,&H00000000,&H00000000,1,1,8,0,8,40,40,90",
    ]
    for name, colour in script["speakers"].items():
        lines.append(f"Style: {name},{font},72,&H00FFFFFF,{ass_colour(colour)},&H00000000,1,1,9,0,8,70,70,470")
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Text"]
    title = r"\N".join(script.get("title", []))
    if title:
        lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,{title}")
    for scene, (start, end) in zip(script["scenes"], timings):
        text = scene["text"].replace("\n", r"\N")
        lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},{scene['speaker']},{text}")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------- chương trình chính ----------

def preview(script):
    """Xuất một ảnh tĩnh cho mỗi cảnh, không cần giọng đọc. Dùng để duyệt bố cục."""
    Path("scenes").mkdir(exist_ok=True)
    font_file = script.get("font_file")
    for scene in script["scenes"]:
        length = 1.5
        frame = render_frame(scene, background(scene), load_layers(scene, font_file), length * 0.6, length)
        frame.save(Path("scenes") / f"{scene['id']:03d}.png")
    print(f"Đã xuất {len(script['scenes'])} ảnh vào scenes/")


def main():
    script = json.loads(Path("script.json").read_text(encoding="utf-8"))
    if "--preview" in sys.argv:
        return preview(script)
    TMP.mkdir(exist_ok=True)
    clips, timings, clock = [], [], 0.0
    for scene in script["scenes"]:
        name = f"{scene['id']:03d}"
        clip = TMP / f"{name}.mp4"
        length = render_clip(scene, script.get("font_file"), Path("audio") / f"{name}.wav", clip)
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
    video_filter = f"ass={subs.as_posix()}"
    common = ["-c:v", "libx264", "-preset", "medium", "-crf", 20, "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", "output.mp4"]
    if Path("music.mp3").exists():
        run("-i", joined, "-stream_loop", -1, "-i", "music.mp3", "-filter_complex",
            f"[0:v]{video_filter}[v];[1:a]volume={MUSIC_VOLUME}[m];"
            f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "[v]", "-map", "[a]", "-t", clock, *common)
    else:
        run("-i", joined, "-vf", video_filter, *common)
    print(f"Xong: output.mp4 ({clock:.1f}s, {len(clips)} cảnh)")


if __name__ == "__main__":
    main()
