"""Khai báo ảnh dùng chung của luồng tiểu phẩm, không gọi AI hoặc Kaggle."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACE = {"normal": "calm neutral", "happy": "big happy smiling", "shocked": "shocked, wide-eyed, mouth open",
        "angry": "angry, furrowed brows, shouting", "sad": "sad, teary", "panic": "panicked, sweating, mouth wide open",
        "smug": "smug, confident grin", "crying": "crying with tears streaming",
        "embarrassed": "embarrassed, blushing, awkward smile", "thinking": "thinking, puzzled, eyes looking up",
        "disgusted": "disgusted, grimacing", "sleepy": "sleepy, half-closed eyes, yawning"}


def normalize_assets(skit):
    """Bổ sung biểu cảm được dùng trong lời; báo các tham chiếu không thể tạo ảnh."""
    changes, problems = [], []
    cast = skit.get("cast") or {}
    for name, spec in cast.items():
        if not re.fullmatch(r"sk_[a-z0-9_]+", name):
            problems.append(f"nhân vật '{name}': tên phải dạng sk_<tiếng Anh>")
        spec["expressions"] = list(dict.fromkeys(["normal", *(spec.get("expressions") or [])]))
        spec["poses"] = spec.get("poses") or {}
        for pose in spec["poses"]:
            if not re.fullmatch(r"[a-z0-9_]+", pose):
                problems.append(f"{name}: tên tư thế '{pose}' không hợp lệ")
        for expr in spec["expressions"]:
            if expr not in FACE:
                problems.append(f"{name}: biểu cảm '{expr}' chưa có mô tả")
        if not spec.get("look") or not spec.get("pose"):
            problems.append(f"{name}: thiếu look hoặc pose để sinh ảnh")
        if skit.get("sets") and spec.get("set") not in (None, *skit["sets"]):
            problems.append(f"{name}: set '{spec['set']}' chưa được khai báo")
    for index, line in enumerate(skit.get("lines") or [], 1):
        if line.get("speaker") not in cast:
            problems.append(f"câu {index}: speaker '{line.get('speaker')}' không có trong cast")
        for name, expr in (line.get("expression") or {}).items():
            if name not in cast or expr not in FACE:
                problems.append(f"câu {index}: biểu cảm '{name}: {expr}' không hợp lệ")
            elif expr not in cast[name]["expressions"]:
                cast[name]["expressions"].append(expr)
                changes.append(f"{name}: bổ sung biểu cảm '{expr}' theo câu {index}")
        for name, pose in (line.get("pose") or {}).items():
            if name not in cast or (pose != "default" and pose not in cast[name]["poses"]):
                problems.append(f"câu {index}: tư thế '{name}: {pose}' chưa có mô tả")
        for field in ("enter", "exit"):
            if line.get(field) and line[field] not in cast:
                problems.append(f"câu {index}: {field} '{line[field]}' không có trong cast")
    return changes, problems


def character_states(spec):
    return list(dict.fromkeys(["normal", *(spec.get("expressions") or []),
                               *(f"pose_{p}" for p in spec.get("poses") or {})]))


def character_files(skit):
    for name, spec in skit["cast"].items():
        for state in character_states(spec):
            for suffix in ("", "_talk"):
                yield f"{name}_{state}{suffix}.png"


def missing_images(folder, skit, cutouts=False):
    """Mọi biến thể đã khai báo, nền và tranh chèn phải có trước khi bước tiếp."""
    missing = []
    for filename in character_files(skit):
        paths = [folder / "cutouts" / filename]
        if not cutouts:
            paths.append(folder / "characters" / filename)
        if not any(p.is_file() for p in paths):
            missing.append(f"{'cutouts' if cutouts else 'characters'}/{filename}")
    backgrounds = set((skit.get("backgrounds") or {}).values())
    if not backgrounds and skit.get("background"):
        backgrounds.add(skit["background"])
    backgrounds |= set((skit.get("inserts") or {}).values())
    backgrounds |= {spec.get("image", name) for name, spec in (skit.get("scenes") or {}).items()}
    for name in backgrounds:
        if not (ROOT / "library" / "backgrounds" / f"{name}.png").is_file():
            missing.append(f"backgrounds/{name}.png")
    for index, line in enumerate(skit.get("lines") or [], 1):
        if line.get("insert") and line["insert"] not in (skit.get("inserts") or {}):
            missing.append(f"câu {index}: tranh chèn chưa được lên danh sách, chạy skit/jobs.py")
    return sorted(set(missing))
