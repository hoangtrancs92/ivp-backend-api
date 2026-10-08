"""Phần dùng chung của các bước: đường dẫn, đọc cấu hình, tên file ảnh nhân vật."""
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # thư mục shorts-pipeline/
CONFIG = ROOT / "config"
SETTINGS = tomllib.loads((CONFIG / "settings.toml").read_text(encoding="utf-8"))   # thông số chỉnh được
LIBRARY = ROOT / "library"
TRIGGER = "irasutoya_style"


def video_dir():
    if len(sys.argv) < 2:
        sys.exit(f"Dùng: python {Path(sys.argv[0]).name} videos/<tên>")
    return Path(sys.argv[1]).resolve()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_script(video):
    return load_json(video / "script.json")


def character_files(scene):
    """(tên nhân vật, tên file) của từng ảnh chủ thể trong một cảnh, đều nằm ở characters/.
    Một nhân vật: 001.png. Nhiều nhân vật: mỗi người một ảnh, 001_father.png, 001_mother.png.
    Cảnh không có nhân vật mà có "object" (đồ vật là chủ thể): (None, 001.png)."""
    names = scene.get("characters", [])
    if not names:
        return [(None, f"{scene['id']:03d}.png")] if scene.get("object") else []
    if len(names) == 1:
        return [(names[0], f"{scene['id']:03d}.png")]
    return [(name, f"{scene['id']:03d}_{name}.png") for name in names]



# ---------- duyệt ảnh bằng mắt (trang web + tools/auto.py) ----------

def background_file(video, location):
    """Ảnh nền của một bối cảnh: riêng của video nếu có, không thì thư viện dùng chung."""
    own = video / "backgrounds" / f"{location}.png"
    return own if own.exists() else LIBRARY / "backgrounds" / f"{location}.png"


def review_items(video, script=None):
    """Mọi ảnh cần duyệt của một video, theo thứ tự cảnh: ảnh nhân vật / đồ vật (kể cả tư thế _alt) rồi ảnh nền.
    Mỗi mục: {"key": đường dẫn tương đối dùng làm khóa, "path": Path, "kind": "character" | "background", "scene": id}."""
    script = script or load_script(video)
    items, seen = [], set()
    for scene in script["scenes"]:
        for _, filename in character_files(scene):
            for name in (filename, f"{Path(filename).stem}_alt.png"):
                path = video / "characters" / name
                if path.exists() and name not in seen:
                    seen.add(name)
                    items.append({"key": f"characters/{name}", "path": path, "kind": "character", "scene": scene["id"]})
    for loc in dict.fromkeys(s["location"] for s in script["scenes"]):
        path = background_file(video, loc)
        if path.exists():
            items.append({"key": f"backgrounds/{loc}.png", "path": path, "kind": "background", "scene": None})
    return items


def image_stamp(video, script=None):
    """Dấu vân tay của bộ ảnh hiện tại: đổi khi có ảnh mới, ảnh vẽ lại hay bị xóa. Duyệt xong thì lưu dấu này."""
    import hashlib
    parts = sorted(f"{i['key']}:{i['path'].stat().st_mtime_ns}" for i in review_items(video, script))
    return hashlib.sha1("|".join(parts).encode()).hexdigest()


def reject_image(video, key):
    """Bỏ một ảnh để vẽ lại: chuyển sang rejected/ (đánh số lần bị loại để make_jobs.py đổi seed).
    Ảnh nhân vật gốc bị bỏ thì bỏ luôn tư thế _alt (vẽ từ ảnh gốc). Ảnh nền nằm ở thư viện chung: chuyển sang
    library/backgrounds/rejected/."""
    kind, _, name = key.partition("/")
    if kind == "characters":
        src, dest_dir = video / "characters" / name, video / "rejected"
    elif kind == "backgrounds":
        loc = Path(name).stem
        src = background_file(video, loc)
        dest_dir = src.parent / "rejected"
    else:
        raise ValueError(f"Ảnh không hợp lệ: {key}")
    if not src.exists():
        return []
    dest_dir.mkdir(parents=True, exist_ok=True)
    tries = sum(1 for f in dest_dir.glob(f"{src.stem}*.png")
                if f.stem == src.stem or f.stem[len(src.stem):].lstrip("_").isdigit())
    src.rename(dest_dir / f"{src.stem}{f'_{tries + 1}' if tries else ''}.png")
    if kind == "characters":
        (video / "cutouts" / name).unlink(missing_ok=True)
    done = [key]
    if kind == "characters" and not src.stem.endswith("_alt"):
        alt = f"characters/{src.stem}_alt.png"
        if (video / alt).exists():
            done += reject_image(video, alt)
    return done


# ---------- chuẩn hóa layers model AI viết lệch tên khóa ----------

IMAGE_ALIASES = ("src", "file", "img", "image_path", "url", "sticker", "picture", "source")
WORD_ALIASES = ("text", "onomatopoeia", "sfx")


OPTIONAL_KEYS = ("shot", "filter", "motion", "transition", "anim", "at", "size", "path", "alt_pose", "object",
                 "start", "duration", "over", "colour", "on", "ambient", "sfx")


def normalize_script(script):
    """Chuẩn hóa kịch bản model viết: trường để null (vd "shot": null ở cảnh chỉ có đồ vật) coi như bỏ trống để dùng
    mặc định; "characters": null thành []; rồi chuẩn hóa layers. Sửa trực tiếp script, trả về danh sách thay đổi."""
    changes = []
    for scene in script.get("scenes", []):
        for key in [k for k, v in scene.items() if v is None and k in OPTIONAL_KEYS]:
            del scene[key]
            changes.append(f"cảnh {scene.get('id')}: bỏ \"{key}\": null")
        if scene.get("characters") is None:
            scene["characters"] = []
        if scene.get("shot") not in (None, "full", "half", "close"):
            changes.append(f"cảnh {scene.get('id')}: shot '{scene['shot']}' không hợp lệ, dùng full")
            scene["shot"] = "full"
        for layer in scene.get("layers") or []:
            if isinstance(layer, dict):
                for key in [k for k, v in layer.items() if v is None]:
                    del layer[key]
    return changes + normalize_layers(script)


def normalize_layers(script):
    """Model khác nhau đặt tên khóa khác nhau ({"src": ...} thay vì {"image": ...}). Đổi về tên build_video.py hiểu,
    sửa trực tiếp script và trả về danh sách thay đổi (để in ra)."""
    changes = []
    for scene in script.get("scenes", []):
        layers = []
        for layer in scene.get("layers") or []:
            if not isinstance(layer, dict):
                changes.append(f"cảnh {scene.get('id')}: bỏ lớp không hợp lệ {layer!r}")
                continue
            if "image" not in layer and "effect" not in layer and "word" not in layer:
                key = next((k for k in IMAGE_ALIASES if isinstance(layer.get(k), str)), None)
                if key is None and isinstance(layer.get("path"), str) and layer["path"].endswith(".png"):
                    key = "path"                  # "path" vốn là đường đi (danh sách điểm); chuỗi .png thì là ảnh
                if key:
                    layer["image"] = layer.pop(key)
                    changes.append(f"cảnh {scene.get('id')}: '{key}' → 'image'")
                else:
                    key = next((k for k in WORD_ALIASES if isinstance(layer.get(k), str)), None)
                    if key:
                        layer["word"] = layer.pop(key)
                        changes.append(f"cảnh {scene.get('id')}: '{key}' → 'word'")
            if "image" in layer and isinstance(layer["image"], str):
                image = layer["image"].replace("\\", "/")
                if image.startswith("library/stickers/"):
                    image = image[len("library/"):]
                layer["image"] = image
            if not any(k in layer for k in ("image", "word", "effect")):
                changes.append(f"cảnh {scene.get('id')}: bỏ lớp không có ảnh, chữ hay hiệu ứng {layer}")
                continue
            layers.append(layer)
        scene["layers"] = layers
    return changes


def summarize_changes(changes):
    """Gộp các thay đổi kiểu 'cảnh N: bỏ "x": null' thành một dòng; giữ nguyên các thay đổi khác."""
    nulls, others = {}, []
    for c in changes:
        if c.endswith(": null") and ": bỏ " in c:
            key = c.split(": bỏ ", 1)[1].split(":")[0].strip('"')
            nulls[key] = nulls.get(key, 0) + 1
        else:
            others.append(c)
    if nulls:
        others.insert(0, "bỏ các trường để null (dùng mặc định): " + ", ".join(f'"{k}" ×{n}' for k, n in nulls.items()))
    return others
