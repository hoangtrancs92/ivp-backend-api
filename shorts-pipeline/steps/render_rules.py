"""Các giá trị dựng được hỗ trợ, dùng chung cho kịch bản và bộ dựng."""
from pathlib import Path
try:
    from .effect_rules import KINDS, valid_anchor
except ImportError:
    from effect_rules import KINDS, valid_anchor
ANIMS = ("none", "bounce", "wobble", "pulse", "pop", "pop_fade", "drop", "slide_left", "slide_right",
         "exit_left", "exit_right", "approach", "recede", "jump",
         "nod", "shake_no", "sway", "tilt", "breathe", "shiver", "hop", "sink", "float", "punch", "spin_in",
         "lean_in", "rise", "squash", "jelly", "puff", "deflate", "stretch_up", "snap")
MOTIONS = ("zoom_in", "zoom_out", "pan_left", "pan_right", "shake", "none",
           "punch_in", "tilt_up", "tilt_down", "dolly_left", "dolly_right", "focus", "drift", "dutch",
           "build", "impact", "talk_in")
TRANSITIONS = ("cut", "fade", "push_left", "push_right", "push_up", "whip", "zoom", "flash", "wipe", "iris")
ANIM_ALIASES = {"dash_in_right": "slide_right", "dash_in_left": "slide_left", "recoil": "recede"}

# Tranh cả cảnh không có chủ thể cắt rời để animate; dùng chuyển động máy gần ý gốc.
CAMERA_EQUIVALENTS = {"breathe": "drift", "sway": "drift", "float": "drift", "tilt": "dutch",
                      "sink": "tilt_down", "deflate": "zoom_out", "rise": "tilt_up", "drop": "tilt_down",
                      "approach": "zoom_in", "lean_in": "zoom_in", "recede": "zoom_out",
                      "slide_left": "pan_left", "exit_left": "pan_left",
                      "slide_right": "pan_right", "exit_right": "pan_right",
                      "shiver": "shake", "shake_no": "shake", "puff": "punch_in", "punch": "punch_in",
                      "snap": "impact"}


def normalize_motion(script):
    changes = []
    for scene in script.get("scenes", []):
        motion = scene.get("motion")
        if motion in ANIM_ALIASES:
            scene["motion"] = ANIM_ALIASES[motion]
            changes.append(f"cảnh {scene['id']}: motion '{motion}' -> '{scene['motion']}'")
            motion = scene["motion"]
        if motion in ANIMS and motion not in MOTIONS:
            subjects = [l for l in scene.get("layers", []) if str(l.get("image", "")).startswith("cutouts/")]
            if subjects and not (scene.get("full") or scene.get("phone")):
                # Ưu tiên người đang nói; giữ anim đã khai riêng cho từng lớp.
                target = next((l for l in subjects if l.get("id") == scene.get("speaker")), subjects[0])
                target.setdefault("anim", motion)
                del scene["motion"]
                changes.append(f"cảnh {scene['id']}: motion '{motion}' là chuyển động chủ thể; dùng anim, máy quay tự chọn")
            else:
                camera = CAMERA_EQUIVALENTS.get(motion, "drift")
                scene["motion"] = camera
                changes.append(f"cảnh {scene['id']}: motion '{motion}' -> '{camera}' cho máy quay")
        for layer in scene.get("layers", []):
            anim = layer.get("anim")
            if anim in ANIM_ALIASES:
                layer["anim"] = ANIM_ALIASES[anim]
                changes.append(f"cảnh {scene['id']}: anim '{anim}' -> '{layer['anim']}'")
                anim = layer["anim"]
            if anim in MOTIONS and anim not in ANIMS:
                scene.setdefault("motion", anim)
                del layer["anim"]
                changes.append(f"cảnh {scene['id']}: anim '{anim}' là chuyển động máy quay; chuyển về motion")
    return changes


def render_problems(script):
    problems = []
    for scene in script.get("scenes", []):
        for name, box in (scene.get("effect_anchors") or {}).items():
            if not valid_anchor(box):
                problems.append(f"cảnh {scene['id']}: điểm neo hiệu ứng '{name}' không hợp lệ")
        for key, allowed in (("motion", MOTIONS), ("transition", TRANSITIONS)):
            if key in scene and scene[key] not in allowed:
                problems.append(f"cảnh {scene['id']}: {key} '{scene[key]}' không được hỗ trợ; có: {', '.join(allowed)}")
        for layer in scene.get("layers", []):
            kind = layer.get("effect")
            if kind and kind not in KINDS:
                group = kind.removeprefix("fx_")
                directory = Path(__file__).resolve().parent.parent / "library" / "fx" / group
                if not directory.is_dir() or not any(p.suffix.lower() in (".mp4", ".mov", ".webm") for p in directory.iterdir()):
                    problems.append(f"cảnh {scene['id']}: hiệu ứng '{kind}' không được hỗ trợ")
            if (scene.get("full") or scene.get("phone")) and str(layer.get("image", "")).startswith("cutouts/"):
                continue
            if "anim" in layer and layer["anim"] not in ANIMS:
                problems.append(f"cảnh {scene['id']}: anim '{layer['anim']}' không được hỗ trợ; có: {', '.join(ANIMS)}")
    return problems
