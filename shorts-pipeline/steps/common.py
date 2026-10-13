"""Phần dùng chung của các bước: đường dẫn, đọc cấu hình, tên file ảnh nhân vật."""
import json
import sys
import tomllib
from pathlib import Path
from render_rules import normalize_motion, render_problems

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
    script = load_json(video / "script.json")
    normalize_script(script, video)
    return script


def character_files(scene):
    """(tên nhân vật, tên file) của từng ảnh chủ thể trong một cảnh, đều nằm ở characters/.
    Một nhân vật: 001.png. Nhiều nhân vật: mỗi người một ảnh, 001_father.png, 001_mother.png.
    Cảnh không có nhân vật mà có "object" (đồ vật là chủ thể): (None, 001.png)."""
    if scene.get("full") or scene.get("phone"):   # cách dựng mới: tranh vẽ cả cảnh (full/NNN.png); màn hình điện thoại vẽ code
        return []
    names = scene.get("characters", [])
    if not names:
        if not scene.get("object"):
            return []
        images = [Path(l.get("image", "")) for l in scene.get("layers", [])]
        images = [p for p in images if p.parent.as_posix() == "cutouts" and p.suffix == ".png"]
        return [(None, images[0].name if len(images) == 1 else f"{scene['id']:03d}.png")]
    files = []
    prefix = f"{scene['id']:03d}"
    for name in names:
        default = f"{prefix}.png" if len(names) == 1 else f"{prefix}_{name}.png"
        # Giữ đường dẫn lớp đã khai báo, kể cả ảnh một người khi cảnh được bổ sung người thứ hai.
        explicit = [Path(layer.get("image", "")) for layer in scene.get("layers", [])
                    if layer.get("id") == name]
        own = [p.name for p in explicit if p.parent.as_posix() == "cutouts" and p.suffix == ".png"]
        files.append((name, own[0] if own else default))
    return files


def character_variants(scene):
    """Danh sách ảnh chủ thể và tư thế phụ dùng chung cho sinh ảnh, kiểm tra và duyệt."""
    variants = []
    for name, filename in character_files(scene):
        variants.append((name, filename))
        pose = scene.get("alt_pose")
        if isinstance(pose, dict):
            pose = pose.get(name)
        if pose:
            variants.append((name, f"{Path(filename).stem}_alt.png"))
    return variants


def image_requirements(script):
    """(loại, cảnh, đường dẫn chính, đường dẫn thay thế) của mọi ảnh bắt buộc."""
    for scene in script["scenes"]:
        sid = scene["id"]
        if scene.get("full"):
            yield "full", sid, f"full/{sid:03d}.png", ()
            continue
        yield "background", sid, f"backgrounds/{scene['location']}.png", ()
        for _, filename in character_variants(scene):
            yield "character", sid, f"characters/{filename}", (f"cutouts/{filename}",)


def missing_script_images(video, script=None):
    script = script if script is not None else load_script(video)
    missing = []
    for _, _, path, alternatives in image_requirements(script):
        if not any((video / p).is_file() or (LIBRARY / p).is_file() for p in (path, *alternatives)):
            missing.append(path)
    return sorted(set(missing))


def asset_problems(script, video):
    """Lỗi không thể giải quyết bằng sinh ảnh: lớp thiếu nguồn, trùng file, tên chưa khai báo."""
    known = set(load_json(CONFIG / "characters.json")) | set(script.get("new_characters") or {})
    problems, ids, owners = render_problems(script), set(), {}
    for scene in script["scenes"]:
        sid = scene["id"]
        if sid in ids:
            problems.append(f"cảnh {sid}: id cảnh bị trùng")
        ids.add(sid)
        needs_full = scene.get("full") and not (video / "full" / f"{sid:03d}.png").is_file()
        missing_subjects = {n for n, f in character_files(scene)
                            if not (video / "characters" / f).is_file() and not (video / "cutouts" / f).is_file()}
        for name in scene.get("characters", []):
            if name not in known and (needs_full or name in missing_subjects):
                problems.append(f"cảnh {sid}: nhân vật '{name}' chưa có mô tả trong cấu hình")
        files = character_files(scene)
        for name, filename in files:
            if filename in owners and owners[filename] != name:
                problems.append(f"cảnh {sid}: file '{filename}' được khai cho nhiều chủ thể khác nhau")
            owners[filename] = name
        filenames = [f for _, f in files]
        if len(set(filenames)) != len(filenames):
            problems.append(f"cảnh {sid}: nhiều nhân vật dùng chung một file ảnh")
        planned = {f"cutouts/{f}" for _, f in character_variants(scene)}
        for layer in scene.get("layers", []):
            image = layer.get("image")
            if image and image.startswith("cutouts/") and (scene.get("full") or scene.get("phone")):
                continue  # Những lớp này được bỏ khi dựng tranh cả cảnh / điện thoại.
            if image and image.startswith("cutouts/"):
                owner = Path(image).stem[4:].removesuffix("_alt")
                if owner in known and layer.get("id") in known and owner != layer["id"]:
                    problems.append(f"cảnh {sid}: lớp '{layer['id']}' đang dùng ảnh của '{owner}'")
            if image and image.startswith("cutouts/") and image not in planned \
                    and not (video / image).is_file() and not (LIBRARY / image).is_file():
                problems.append(f"cảnh {sid}: {image} chưa có và không có nguồn sinh; kiểm tra characters và layers")
            elif image and not image.startswith("cutouts/"):
                runtime = ((scene.get("compare") and image == f"compare/{sid:03d}.png")
                           or (scene.get("phone") and image == f"phone/{sid:03d}.png")
                           or (scene.get("photo") and image.startswith("photos/")))
                if not runtime and not (video / image).is_file() and not (LIBRARY / image).is_file():
                    problems.append(f"cảnh {sid}: ảnh '{image}' chưa có và không có bước tạo ảnh này")
    return problems



# ---------- duyệt ảnh bằng mắt (trang web + tools/auto.py) ----------

def background_file(video, location):
    """Ảnh nền của một bối cảnh: riêng của video nếu có, không thì thư viện dùng chung."""
    own = video / "backgrounds" / f"{location}.png"
    return own if own.exists() else LIBRARY / "backgrounds" / f"{location}.png"


def review_items(video, script=None):
    """Mọi ảnh cần duyệt của một video, theo thứ tự cảnh: ảnh nhân vật / đồ vật (kể cả tư thế _alt) rồi ảnh nền.
    Mỗi mục: {"key": đường dẫn tương đối dùng làm khóa, "path": Path, "kind": "character" | "background", "scene": id}."""
    script = load_script(video) if script is None else script
    normalize_script(script, video)
    items, seen = [], set()
    for scene in script["scenes"]:
        for _, filename in character_variants(scene):
            path = video / "characters" / filename
            if not path.exists():
                path = video / "cutouts" / filename
            if path.exists() and filename not in seen:
                seen.add(filename)
                items.append({"key": f"characters/{filename}", "path": path, "kind": "character", "scene": scene["id"]})
        full = video / "full" / f"{scene['id']:03d}.png"      # cách dựng mới: tranh vẽ cả cảnh
        if scene.get("full") and full.exists():
            items.append({"key": f"full/{full.name}", "path": full, "kind": "character", "scene": scene["id"]})
        photo = video / "photos" / f"{scene['id']:03d}.jpg"      # ảnh thật Pexels (steps/fetch_photos.py)
        if scene.get("photo") and photo.exists():
            items.append({"key": f"photos/{photo.name}", "path": photo, "kind": "photo", "scene": scene["id"]})
    for loc in dict.fromkeys(s["location"] for s in script["scenes"] if not s.get("full")):
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
    if kind == "photos":                       # ảnh Pexels: ghi id ảnh bị bỏ, fetch_photos.py lấy kết quả tìm kiếm kế tiếp
        src = video / "photos" / Path(name).name
        if not src.exists():
            return []
        credits_file, rejected_file = video / "photos" / "credits.json", video / "photos" / "rejected_ids.json"
        credits = json.loads(credits_file.read_text(encoding="utf-8")) if credits_file.exists() else {}
        rejected = json.loads(rejected_file.read_text(encoding="utf-8")) if rejected_file.exists() else []
        if src.name in credits:
            rejected.append(credits.pop(src.name)["id"])
        rejected_file.write_text(json.dumps(rejected), encoding="utf-8")
        credits_file.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
        (video / "rejected").mkdir(exist_ok=True)
        src.replace(video / "rejected" / f"photo_{src.stem}_{len(rejected)}.jpg")
        (video / "photos" / f"{src.stem}_card.png").unlink(missing_ok=True)
        return [key]
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


def normalize_script(script, video=None):
    """Chuẩn hóa kịch bản model viết: trường để null (vd "shot": null ở cảnh chỉ có đồ vật) coi như bỏ trống để dùng
    mặc định; "characters": null thành []; rồi chuẩn hóa layers. Sửa trực tiếp script, trả về danh sách thay đổi."""
    changes = []
    for scene in script.get("scenes", []):
        if "full_scene" in scene:
            scene.setdefault("full", bool(scene["full_scene"]))
            del scene["full_scene"]
            changes.append(f"cảnh {scene.get('id')}: full_scene -> full")
        if script.get("style") == "new" and "full" not in scene and not scene.get("phone"):
            scene["full"] = True
            changes.append(f"cảnh {scene.get('id')}: style new, dùng tranh cả cảnh (full)")
        for key in [k for k, v in scene.items() if v is None and k in OPTIONAL_KEYS]:
            del scene[key]
            changes.append(f"cảnh {scene.get('id')}: bỏ \"{key}\": null")
        if scene.get("characters") is None:
            scene["characters"] = []
        if not isinstance(scene.get("text"), str):   # cảnh không lời (thẻ so sánh, clip minh họa; video 045): chuỗi rỗng
            scene["text"] = ""
        if scene.get("shot") not in (None, "full", "half", "close"):
            changes.append(f"cảnh {scene.get('id')}: shot '{scene['shot']}' không hợp lệ, dùng full")
            scene["shot"] = "full"
        for layer in scene.get("layers") or []:
            if isinstance(layer, dict):
                for key in [k for k, v in layer.items() if v is None]:
                    del layer[key]
    changes += normalize_layers(script)
    changes += normalize_subject_layers(script, video)
    return changes + normalize_motion(script)


def normalize_subject_layers(script, video=None):
    """Đồng bộ nhân vật và lớp ảnh trước mọi bước; chỉ sửa khi xác định được chủ thể."""
    changes = []
    known = set(load_json(CONFIG / "characters.json")) | set(script.get("new_characters") or {})
    claimed = {}
    for scene in script.get("scenes", []):
        for layer in scene.get("layers", []):
            image = Path(layer.get("image", ""))
            if image.parent.as_posix() == "cutouts":
                owner = layer.get("id")
                if owner not in (scene.get("characters") or []):
                    names = scene.get("characters") or []
                    owner = names[0] if len(names) == 1 else None
                claimed.setdefault(image.name, set()).add(owner)
    for scene in script.get("scenes", []):
        if scene.get("full") or scene.get("phone"):
            continue
        prefix = f"{scene['id']:03d}_"
        names = scene.setdefault("characters", [])
        names[:] = list(dict.fromkeys(names))
        for layer in scene.get("layers", []):
            image = Path(layer.get("image", ""))
            if image.parent.as_posix() != "cutouts":
                continue
            if image.stem.startswith(prefix):
                name = image.stem[len(prefix):]
                if name not in known:
                    name = layer.get("id")
            elif image.name == f"{scene['id']:03d}.png":
                name = layer.get("id")
            else:
                continue
            if name in known and name not in names:
                names.append(name)
                changes.append(f"cảnh {scene['id']}: bổ sung '{name}' vào characters theo layers")
        layers = scene.setdefault("layers", [])
        cut = [l for l in layers if Path(l.get("image", "")).parent.as_posix() == "cutouts"]
        expected = {n: f"cutouts/{scene['id']:03d}.png" if len(names) == 1
                    else f"cutouts/{scene['id']:03d}_{n}.png" for n in names}
        for name, filename in list(expected.items()):
            if claimed.get(Path(filename).name, set()) - {name}:
                expected[name] = f"cutouts/{scene['id']:03d}_{name}.png"
        if len(names) > 1 and len(cut) == 1:
            tail = Path(cut[0]["image"]).stem[len(prefix):]
            if all(n in tail for n in names):
                old = cut[0]
                places = ["floor_left", "floor_right"] + ["floor"] * len(names)
                layers[layers.index(old):layers.index(old) + 1] = [
                    {**{k: v for k, v in old.items() if k not in ("id", "image", "at", "path")},
                     "id": n, "image": expected[n], "at": places[i]} for i, n in enumerate(names)]
                changes.append(f"cảnh {scene['id']}: tách lớp gộp thành {len(names)} lớp nhân vật")
                cut = [l for l in layers if Path(l.get("image", "")).parent.as_posix() == "cutouts"]
        for layer in cut:
            image = Path(layer["image"])
            tail = image.stem[4:]
            match = [n for n in names if n == layer.get("id")] or [n for n in names if tail and n.endswith(tail)]
            if len(match) != 1:
                continue
            name = match[0]
            if tail in known and tail != name:
                continue  # Hai khai báo mâu thuẫn: báo lỗi, không đoán ảnh thuộc người nào.
            # Đường dẫn đúng được giữ lại; ảnh tái sử dụng từ cảnh khác chỉ giữ khi file có thật.
            own = image.name in (f"{scene['id']:03d}.png", f"{scene['id']:03d}_{name}.png")
            exists = video is not None and ((video / image).is_file() or (LIBRARY / image).is_file())
            if not own and not exists and image.stem[:3] == f"{scene['id']:03d}":
                layer["image"] = expected[name]
                changes.append(f"cảnh {scene['id']}: {image.as_posix()} -> {expected[name]}")
        # Nhân vật có khai báo nhưng model quên lớp ảnh vẫn cần được đặt vào cảnh.
        used = {l.get("id") for l in cut}
        used |= {n for n, f in character_files(scene) if any(l.get("image") == f"cutouts/{f}" for l in cut)}
        for name in names:
            if name not in used:
                layers.append({"id": name, "image": expected[name]})
                changes.append(f"cảnh {scene['id']}: bổ sung lớp ảnh '{name}'")
        if not names and scene.get("object"):
            target = f"cutouts/{scene['id']:03d}.png"
            if claimed.get(Path(target).name, set()) - {None, "object"}:
                target = f"cutouts/{scene['id']:03d}_object.png"
            if not cut:
                layers.append({"id": "object", "image": target})
                changes.append(f"cảnh {scene['id']}: bổ sung lớp ảnh đồ vật")
            elif len(cut) == 1 and cut[0]["image"] != target:
                image = cut[0]["image"]
                if video is None or not ((video / image).is_file() or (LIBRARY / image).is_file()):
                    cut[0]["image"] = target
                    changes.append(f"cảnh {scene['id']}: {image} -> {target} (đồ vật)")
    return changes


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
            if isinstance(layer.get("path"), str):    # "path": "off_left" (một điểm): đi vào từ đó tới chỗ đứng của lớp
                layer["path"] = [layer["path"], layer.get("at", "center")]
                changes.append(f"cảnh {scene.get('id')}: 'path' một điểm → {layer['path']}")
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
