"""Xác định điểm neo hiệu ứng trên ảnh full đã sinh; lưu tọa độ theo ảnh gốc và kiểm tra cache."""
import hashlib
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "steps"))
from common import load_script  # noqa: E402
from effect_rules import required_anchors, valid_anchor  # noqa: E402


def source_stamp(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate(scene, path, targets):
    from llm import chat, json_reply
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((768, 1366), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=92)
    cast = json.loads((ROOT / "config/characters.json").read_text(encoding="utf-8"))
    prompt = (
        "Locate subjects in this actual illustration for precise animated overlays. Do not invent positions. "
        "Return a JSON object keyed by each requested subject. Each value is exactly seven numbers normalized "
        "to the ORIGINAL full image: [body_center_x, body_center_y, visible_body_width, visible_body_height, "
        "face_center_x, face_center_y, face_radius_as_fraction_of_IMAGE_WIDTH]. "
        "The face center is the midpoint between the eyes and mouth, not the top of the hair. "
        "Face radius covers the face, excluding long hair. Body bounds cover the visible subject, excluding furniture. "
        "__subject means the dominant foreground person. Identify other names using context and descriptions below. "
        "If a requested subject cannot be identified, return null for that subject. Never use a sticker, word or "
        "background person as the main subject.\n"
        + json.dumps({"targets": targets, "characters": scene.get("characters"), "speaker": scene.get("speaker"),
                      "descriptions": {name: cast.get(name, {}).get("prompt", "") for name in targets},
                      "text": scene.get("text"), "action": scene.get("action")}, ensure_ascii=False))
    reply = json_reply(chat(prompt, os.environ.get("AI_MODEL_REVIEW") or "claude-sonnet-5-5",
                            image=buffer.getvalue(), max_tokens=2500))
    if not isinstance(reply, dict) or any(not valid_anchor(reply.get(name)) for name in targets):
        raise ValueError(f"cảnh {scene['id']}: không xác định chắc chắn được điểm neo nhân vật {targets}")
    return {name: reply[name] for name in targets}


def prepare(video, locator=locate, script=None, strict=False):
    script_path = video / "script.json"
    stored = json.loads(script_path.read_text(encoding="utf-8"))
    script = load_script(video) if script is None else script
    changed = False
    for scene in script["scenes"]:
        warning = scene.get('effect_anchor_warning')
        if warning and scene.get('full'):
            path = video / 'full' / f"{scene['id']:03d}.png"
            if warning['source'] != source_stamp(path):
                scene.setdefault('layers', []).extend(warning['layers'])
                original = next(sc for sc in stored['scenes'] if sc['id'] == scene['id'])
                original['layers'] = scene['layers']
                original.pop('effect_anchor_warning', None)
                scene.pop('effect_anchor_warning', None)
        targets = required_anchors(scene)
        if not targets:
            continue
        path = video / "full" / f"{scene['id']:03d}.png"
        stamp = source_stamp(path)
        anchors = scene.get("effect_anchors") or {}
        if scene.get("effect_anchors_source") != stamp:
            anchors = {}
        missing = [name for name in targets if not valid_anchor(anchors.get(name))]
        if missing:
            error = None
            for attempt in range(2):
                try:
                    anchors.update(locator(scene, path, missing))
                    if all(valid_anchor(anchors.get(name)) for name in missing):
                        break
                    error = ValueError(f"cảnh {scene['id']}: tọa độ hiệu ứng không hợp lệ")
                except ValueError as exc:
                    error = exc
                print(f"  cảnh {scene['id']}: dò neo lần {attempt + 1}/2 chưa đạt: {error}", flush=True)
            unresolved = [name for name in targets if not valid_anchor(anchors.get(name))]
            if unresolved:
                if strict:
                    raise ValueError(f"cảnh {scene['id']}: không xác định được neo {unresolved}") from error
                # Chỉ bỏ overlay không đặt được, giữ tranh và các hiệu ứng còn lại.
                # Lưu bản gốc để thử lại khi người dùng thay ảnh.
                from effect_rules import required_anchors as needs
                kept, skipped = [], []
                for layer in scene.get('layers', []):
                    probe = dict(scene, layers=[layer])
                    (skipped if any(n in unresolved for n in needs(probe)) else kept).append(layer)
                scene['layers'] = kept
                original = next(sc for sc in stored['scenes'] if sc['id'] == scene['id'])
                original['layers'] = kept
                original['effect_anchor_warning'] = {'source': stamp, 'layers': skipped,
                                                     'reason': str(error)}
                scene['effect_anchor_warning'] = original['effect_anchor_warning']
                anchors = {n: b for n, b in anchors.items() if valid_anchor(b)}
                targets = [n for n in targets if n not in unresolved]
                print(f"  CẢNH BÁO cảnh {scene['id']}: bỏ {len(skipped)} hiệu ứng phụ không xác định được neo {unresolved}; giữ ảnh cảnh.", flush=True)
            if any(not valid_anchor(anchors.get(name)) for name in targets):
                raise ValueError(f"cảnh {scene['id']}: tọa độ hiệu ứng không hợp lệ")
            print(f"  điểm neo hiệu ứng cảnh {scene['id']}: {', '.join(missing)}", flush=True)
        if missing or scene.get("effect_anchors_source") != stamp:
            scene["effect_anchors"] = anchors
            scene["effect_anchors_source"] = stamp
            changed = True
            original = next(sc for sc in stored["scenes"] if sc["id"] == scene["id"])
            original["effect_anchors"] = anchors
            original["effect_anchors_source"] = stamp
            # Lưu sau từng cảnh; chạy lại không phân tích lại các ảnh đã xong.
            script_path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    return changed


def main():
    if len(sys.argv) != 2:
        sys.exit("Dùng: python tools/prepare_effects.py videos/<tên>")
    try:
        changed = prepare(Path(sys.argv[1]).resolve())
    except Exception as error:
        sys.exit(f"Không chuẩn bị được vị trí hiệu ứng: {error}")
    print("Điểm neo hiệu ứng: " + ("đã cập nhật" if changed else "đủ, dùng tọa độ đã lưu"))


if __name__ == "__main__":
    main()
