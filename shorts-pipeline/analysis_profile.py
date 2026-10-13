"""Cách dựng riêng cho video phân tích Nhật Bản và các nước khác."""
from pathlib import Path


def enabled(script):
    return script.get("story_mode") == "kaigai" or script.get("edit_profile") == "comparison_analysis"


def apply(script):
    """Một tiêu điểm mỗi cảnh; không tự thêm gói phản ứng của video tiểu phẩm."""
    if not enabled(script):
        return script
    script["bgm"] = "serious"
    script["music_quieter"] = max(float(script.get("music_quieter") or 0), 7.0)
    for index, scene in enumerate(script.get("scenes", [])):
        scene["_analysis"] = True
        scene["_dialogue"] = scene.get("speaker") not in (None, "narrator")
        for key in ("focus", "punchline", "music_stop", "alt_pose", "filter", "_emotion_fx"):
            scene.pop(key, None)
        scene["transition"] = "cut"
        scene["motion"] = "none" if scene.get("compare") or scene.get("photo") else (
            "zoom_in" if scene.get("beat") in ("hook", "reveal") else "none")
        # Chỉ gắn một tiếng nhẹ tại vài mốc, không tiếng thắng/thua cho mọi bảng.
        scene["sfx"] = ["jan"] if scene.get("beat") == "reveal" and index % 6 == 0 else []
        layers = [l for l in scene.get("layers", []) if l.get("image")
                  and Path(l["image"]).parent.name != "stickers"]
        subjects = [l for l in layers if Path(l["image"]).parent.name == "cutouts"]
        photo_ready = scene.get("photo") and (Path("photos") / f"{scene['id']:03d}.jpg").is_file()
        if scene.get("compare") or photo_ready:
            layers = [l for l in layers if l not in subjects]
        elif len(subjects) > 1:
            host = next((l for l in subjects if l.get("id") == scene.get("speaker")), subjects[0])
            layers = [l for l in layers if l not in subjects or l is host]
        for layer in layers:
            layer.pop("path", None)
            layer.pop("over", None)
            layer["anim"] = "none"
            if layer in subjects:
                layer.update(at=[0.5, 0.65], size=0.46)
        scene["layers"] = layers
        if isinstance(scene.get("compare"), dict):
            scene["compare"]["style"] = "analysis"
    return script


def video_options(script, defaults):
    if not enabled(script):
        return defaults
    return {**defaults, "title_size": 86, "title_band": 220, "subtitle_size": 76,
            "subtitle_top": 260, "subtitle_margin": 70, "pad": 0.18}
