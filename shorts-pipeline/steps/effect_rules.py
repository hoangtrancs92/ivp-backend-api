"""Loại hiệu ứng và điểm neo dùng chung cho viết kịch bản, chuẩn bị và dựng."""
import math

KINDS = {
    "aura": (True, "#FFD84A"), "rays": (True, "#FFE07A"), "sparkles": (True, "#FFF6C8"),
    "hearts": (True, "#FF6F91"), "tears": (True, "#7CCBFF"), "speed_lines": (False, "#1E1E28"),
    "flash": (False, "#FFFFFF"), "gloom": (False, "#1B2240"), "confetti": (False, None),
    "rain": (False, "#A8C8E8"), "sweat": (True, "#9ED8F5"), "anger": (True, "#E53935"),
    "shock_lines": (True, "#3A3F8F"), "dizzy": (True, "#FFD54A"), "idea": (True, "#FFE45C"),
    "sigh": (True, "#FFFFFF"), "murmur": (False, "#FF8A1E"), "shiver": (True, "#586480"),
}


def valid_anchor(box):
    """[tâm thân x,y, rộng,cao, tâm đầu x,y, bán kính đầu theo chiều rộng ảnh]."""
    if not isinstance(box, list) or len(box) != 7:
        return False
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in box):
        return False
    cx, cy, w, h, hx, hy, hr = box
    return (0 <= cx <= 1 and 0 <= cy <= 1 and 0 < w <= 1 and 0 < h <= 1
            and 0 <= hx <= 1 and 0 <= hy <= 1 and 0.01 <= hr <= 0.5)


def required_anchors(scene):
    """Nhân vật cần xác định trên tranh cả cảnh. Hiệu ứng toàn khung không cần neo."""
    if not scene.get("full"):
        return []
    targets = []
    names = scene.get("characters") or []
    default = scene.get("speaker") if scene.get("speaker") in names else names[0] if len(names) == 1 else "__subject"
    for layer in scene.get("layers", []):
        kind = layer.get("effect")
        if kind in KINDS and (KINDS[kind][0] or (kind == "murmur" and layer.get("on"))):
            targets.append(layer.get("on") or default)
    return list(dict.fromkeys(targets))


def project_anchor(box, source_size, output_size, shift=0):
    """Cùng phép fit/crop và dịch ảnh với place_full; hiệu ứng được vẽ trước máy quay."""
    sw, sh = source_size
    W, H = output_size
    scale = max(W / sw, H / sh)
    ox, oy = (sw * scale - W) / 2, (sh * scale - H) / 2
    cx, cy, w, h, hx, hy, hr = box
    return (cx * sw * scale - ox, cy * sh * scale - oy + shift, w * sw * scale, h * sh * scale,
            hx * sw * scale - ox, hy * sh * scale - oy + shift, hr * sw * scale)
