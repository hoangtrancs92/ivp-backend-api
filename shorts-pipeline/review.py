"""Cho model AI chấm ảnh. Chạy trong thư mục của video. Gọi qua steps/llm.py (cổng chuẩn OpenAI,
mặc định ShopAIKey): cần AI_API_KEY, model chọn bằng AI_MODEL_REVIEW (phải đọc được ảnh).

  python <dự án>/review.py images --only characters/001.png,backgrounds/kitchen.png
                                            chấm các ảnh người duyệt đã chọn trên web; ảnh dưới ngưỡng bị bỏ để vẽ lại
  python <dự án>/review.py images --all     chấm mọi ảnh của video (dùng tay)
  python <dự án>/review.py layout           duyệt work/preview/ sau bước 5; ghi đề xuất sửa vào review/layout.json
  python <dự án>/review.py layout --apply   như trên, và ghi luôn layers đã sửa vào script.json

Ngưỡng đạt: biến môi trường REVIEW_PASS_SCORE (mặc định 3 trên 5). Kết quả nằm trong review/images.json, review/layout.json.
Từ 2026-10-08 quy trình tự động không cho AI chấm hết ảnh nữa (quá khắt khe, tốn giờ GPU vẽ lại): người duyệt bằng mắt
trên trang web, chỉ gửi ảnh nghi ngờ cho AI.
"""
import io
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / "steps"))
from llm import chat, json_reply   # noqa: E402

MODEL = os.environ.get("AI_MODEL_REVIEW") or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
PASS_SCORE = int(os.environ.get("REVIEW_PASS_SCORE", "3"))   # ảnh dưới điểm này bị bỏ để vẽ lại
CHARACTERS = Path(__file__).resolve().parent / "config" / "characters.json"
LOCATIONS = Path(__file__).resolve().parent / "config" / "locations.json"

LAYOUT_PROMPT = """Đây là ảnh xem trước một cảnh của video dọc. Tiêu đề và phụ đề nằm ở 30% phía trên, không có trong ảnh này.
Các lớp của cảnh, theo thứ tự vẽ:
{layers}

Kiểm tra: có lớp nào che mặt nhân vật; lớp nào tràn ra ngoài khung hoặc lấn lên 30% phía trên;
đạo cụ đang cầm có nằm gần tay không; các nhân vật có chồng lên nhau không; sticker và chữ có nằm cạnh đầu nhân vật không.
Nếu cần sửa, trả về toàn bộ danh sách layers đã sửa. Chỉ được đổi các trường at, path, size và thứ tự lớp.
Giá trị hợp lệ của at và path: {places}; hoặc "<id>.<điểm neo>" với điểm neo thuộc {anchors}; hoặc [x, y] từ 0 đến 1.
Giá trị hợp lệ của size: tiny, small, medium, large, huge.
Chỉ trả về JSON: {{"ok": <true|false>, "problems": ["..."], "layers": [...]}}"""

PLACES = "center, left, right, top, top_left, top_right, bottom, off_left, off_right, off_top, off_bottom"
ANCHORS = "center, top, bottom, left, right, above, head, beside_left, beside_right, hand_left, hand_right"


GUIDE = Path(__file__).resolve().parent / "config" / "review_guide.md"
REFS = Path(__file__).resolve().parent / "config" / "refs"
FAIL_AT = 2             # một tiêu chí bắt buộc (★ trong config/review_guide.md) từ mức này trở xuống thì vẽ lại


def guide_section(title):
    """Một mục của config/review_guide.md (từ "## <title>" tới mục sau); trả về (câu hỏi, các tiêu chí bắt buộc ★)."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(f"## {title}")
    end = text.find("\n## ", start + 3)
    body = text[text.index("\n", start) + 1: end if end > 0 else None].strip()
    required = re.findall(r"^- (\w+) ★", body, re.M)
    return body, required


def jpeg(path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((768, 768))                      # ảnh nhỏ là đủ để duyệt, và tốn ít token hơn
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def ask(image_path, prompt, reference=None):
    """Gửi ảnh (kèm ảnh chuẩn nhân vật đứng trước nếu có) và câu hỏi cho model, nhận về JSON.
    Trả lời hỏng 2 lần thì coi như ảnh đạt để không chặn cả video."""
    images = ([jpeg(reference)] if reference else []) + [jpeg(image_path)]
    for attempt in range(2):
        text = chat(prompt, MODEL, images=images, max_tokens=4000)
        try:
            result = json_reply(text)
            result["problems"] = [str(x) for x in result.get("problems") or []]
            result["fix"] = str(result.get("fix") or "").strip()
            redraw = result.get("redraw")
            if isinstance(redraw, str):
                redraw = redraw.strip().lower() in ("true", "yes", "1")
            if redraw is not None:
                result["redraw"] = bool(redraw)
            checks = result.get("checks") or {}
            result["checks"] = {k: int(v) for k, v in checks.items() if str(v).strip().isdigit()}
            if "score" in result:
                result["score"] = int(result["score"])
            return result
        except (ValueError, TypeError):
            print(f"  {image_path.name}: {MODEL} trả lời không phải JSON, hỏi lại", flush=True)
    return {"score": PASS_SCORE, "checks": {}, "problems": ["model không chấm được, tạm cho qua"]}


def decide(result, required):
    """Điểm hiển thị (trung bình các tiêu chí) và kết luận: vẽ lại khi một tiêu chí bắt buộc <= FAIL_AT.
    Model chỉ trả "score" kiểu cũ thì so với PASS_SCORE."""
    checks = result.get("checks") or {}
    if checks:
        score = round(sum(checks.values()) / len(checks), 1)
        failed = [k for k in required if checks.get(k, 5) <= FAIL_AT]
        if result.get("redraw") is False:          # model thấy người xem lướt qua không nhận ra lỗi: cho qua
            failed = []
        return score, ("vẽ lại" if failed else "đạt"), failed
    score = result.get("score", PASS_SCORE)
    return score, ("đạt" if score >= PASS_SCORE else "vẽ lại"), []


SHOTS = {"full": "toàn thân", "half": "nửa người từ thắt lưng", "close": "cận mặt và vai"}


def review_images(script, only=None):
    """Chấm các ảnh trong `only` (khóa dạng characters/001.png, backgrounds/kitchen.png), hoặc mọi ảnh nếu only là None,
    theo tiêu chí trong config/review_guide.md. Ảnh nhân vật được so với ảnh chuẩn (config/refs/<tên>_front.png).
    Ảnh trượt bị bỏ (common.reject_image) để make_jobs.py vẽ lại bằng seed khác."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "steps"))
    from common import character_files, reject_image, review_items
    video = Path.cwd()
    characters = json.loads(CHARACTERS.read_text(encoding="utf-8"))
    locations = json.loads(LOCATIONS.read_text(encoding="utf-8"))
    guides = {k: guide_section(k) for k in ("Nhân vật", "Đồ vật", "Ảnh nền")}
    old = Path("review") / "images.json"
    results = json.loads(old.read_text(encoding="utf-8")) if old.exists() else {}
    scenes = {sc["id"]: sc for sc in script["scenes"]}
    for item in review_items(video, script):
        if only is not None and item["key"] not in only:
            continue
        path, key = item["path"], item["key"]
        if not path.exists():                      # vd 004_alt.png đã bị bỏ cùng 004.png ở lượt chấm trước trong vòng này
            continue
        old_result = results.get(key, {})
        if only is None and old_result.get("verdict") == "đạt" and old_result.get("mtime") == path.stat().st_mtime_ns:
            continue
        reference = None
        if item["kind"] == "background":
            loc = Path(key).stem
            kind, expected = "Ảnh nền", locations.get(loc, loc)
        else:
            scene = scenes[item["scene"]]
            name = next((n for n, f in character_files(scene) if Path(key).stem.removesuffix("_alt") == Path(f).stem), None)
            if name:
                shot = SHOTS.get(scene.get("shot", "full"), scene.get("shot", "full"))
                expected = (f"Nhân vật: {characters[name]['prompt']}. Hành động: {scene.get('action', '')}. "
                            f"Cảm xúc: {scene.get('emotion', '')}. Khung hình: {shot}.")
                if key.endswith("_alt.png") and scene.get("alt_pose"):
                    pose = scene["alt_pose"]
                    expected += f" Tư thế thứ hai: {pose.get(name) if isinstance(pose, dict) else pose}."
                kind = "Nhân vật"
                ref = REFS / f"{name}_front.png"
                reference = ref if ref.exists() else None
            else:
                kind, expected = "Đồ vật", scene.get("object") or scene.get("action", "")
        prompt, required = guides[kind]
        if kind == "Nhân vật" and reference is None:   # chưa có ảnh chuẩn: chấm theo mô tả, không so ảnh 1
            prompt = prompt.replace("Ảnh 1 là ẢNH CHUẨN", "(Không có ảnh chuẩn; so với mô tả.) Ảnh 1 là ẢNH CHUẨN") \
                .replace("Ảnh 2 là ẢNH CẦN CHẤM", "Ảnh duy nhất là ẢNH CẦN CHẤM")
        expected = re.sub(r"[「『\"“][^」』\"”]{1,40}[」』\"”]", "(chữ, không chấm)", expected)   # nội dung chữ: không chấm
        result = ask(path, prompt.replace("{expected}", expected), reference)
        score, verdict, failed = decide(result, required)
        results[key] = {**result, "score": score, "verdict": verdict, "failed": failed, "pass_score": PASS_SCORE,
                        "mtime": path.stat().st_mtime_ns}
        if verdict == "vẽ lại":
            reject_image(video, key)
        detail = ", ".join(f"{k} {v}" for k, v in result.get("checks", {}).items())
        print(f"{key}: {score}/5 → {verdict}{' (' + ', '.join(failed) + ')' if failed else ''}. [{detail}] "
              f"{'; '.join(result['problems'])}", flush=True)
    return results


def review_layout(script, apply):
    results = {}
    for scene in script["scenes"]:
        path = Path("work") / "preview" / f"{scene['id']:03d}.png"
        if not path.exists():
            continue
        layers = json.dumps(scene.get("layers", []), ensure_ascii=False, indent=1)
        result = ask(path, LAYOUT_PROMPT.format(layers=layers, places=PLACES, anchors=ANCHORS))
        results[path.name] = result
        if not result["ok"] and apply and result.get("layers"):
            scene["layers"] = result["layers"]
        print(f"{path.name}: {'ổn' if result['ok'] else 'cần sửa: ' + '; '.join(result['problems'])}")
    if apply:
        Path("script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main():
    mode = sys.argv[1]
    script = json.loads(Path("script.json").read_text(encoding="utf-8"))
    for scene in script["scenes"] if script.get("style") == "new" else []:
        scene["full_scene"] = True                 # cách dựng mới: mỗi cảnh một tranh trọn
    if mode == "images":
        if "--only" in sys.argv:
            only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        elif "--all" in sys.argv:
            only = None
        else:   # bản tools/auto.py cũ gọi kiểu này để AI chấm hết: đã bỏ, chuyển sang duyệt bằng mắt trên web
            print("Đã chuyển sang duyệt ảnh bằng mắt trên trang web. Bấm \"Chạy tiếp\" để tới màn hình duyệt ảnh.")
            sys.exit(3)
        results = review_images(script, only)
    else:
        results = review_layout(script, "--apply" in sys.argv)
    Path("review").mkdir(exist_ok=True)
    (Path("review") / f"{mode}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = sum(1 for r in results.values() if r.get("verdict") == "vẽ lại" or r.get("ok") is False)
    print(f"Đã chấm {len(results)} ảnh, {bad} ảnh cần vẽ lại. Chi tiết: review/{mode}.json")


if __name__ == "__main__":
    main()
