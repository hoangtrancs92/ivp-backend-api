"""Cho Claude duyệt ảnh thay người. Chạy trong thư mục của video, cần biến môi trường ANTHROPIC_API_KEY.

  python ../../review.py images           duyệt characters/ sau bước 3; ảnh hỏng chuyển sang rejected/
  python ../../review.py layout           duyệt scenes/ sau bước 5; ghi đề xuất sửa vào review/layout.json
  python ../../review.py layout --apply   như trên, và ghi luôn layers đã sửa vào script.json

Kết quả chi tiết nằm trong review/images.json và review/layout.json.
"""
import base64
import io
import json
import os
import sys
from pathlib import Path

import anthropic
from PIL import Image

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
PASS_SCORE = 4          # ảnh dưới điểm này bị loại
CHARACTERS = Path("../../config/characters.json")

IMAGE_PROMPT = """Đây là ảnh nhân vật cho một video truyện ngắn nét phẳng, nền trắng.
Ảnh phải thể hiện: {expected}

Chấm ảnh từ 1 đến 5 theo các tiêu chí: đúng nhân vật và trang phục như mô tả; đúng hành động và cảm xúc;
cơ thể không lỗi (thừa thiếu tay chân, ngón tay, mặt méo); chỉ có một nhân vật, thấy trọn người;
nền trắng sạch, không có chữ hay vật thể lạ.
Chỉ trả về JSON: {{"score": <1-5>, "problems": ["..."]}}"""

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


def ask(image_path, prompt):
    """Gửi một ảnh kèm câu hỏi cho Claude, nhận về JSON."""
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((768, 768))                      # ảnh nhỏ là đủ để duyệt, và tốn ít token hơn
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    reply = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=2000,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.b64encode(buf.getvalue()).decode()}},
            {"type": "text", "text": prompt}]}])
    text = reply.content[0].text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    return json.loads(text)


def review_images(script):
    characters = json.loads(CHARACTERS.read_text(encoding="utf-8"))
    Path("rejected").mkdir(exist_ok=True)
    results = {}
    for scene in script["scenes"]:
        path = Path("characters") / f"{scene['id']:03d}.png"
        if not path.exists() or not scene.get("characters"):
            continue
        who = "; ".join(characters[name]["prompt"] for name in scene["characters"])
        expected = f"{who}. Hành động: {scene['action']}. Cảm xúc: {scene['emotion']}."
        result = ask(path, IMAGE_PROMPT.format(expected=expected))
        results[path.name] = result
        if result["score"] < PASS_SCORE:
            path.rename(Path("rejected") / path.name)      # bước 3 thấy thiếu file sẽ sinh lại
        print(f"{path.name}: {result['score']}/5 {'; '.join(result['problems'])}")
    return results


def review_layout(script, apply):
    results = {}
    for scene in script["scenes"]:
        path = Path("scenes") / f"{scene['id']:03d}.png"
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
    results = review_images(script) if mode == "images" else review_layout(script, "--apply" in sys.argv)
    Path("review").mkdir(exist_ok=True)
    (Path("review") / f"{mode}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    bad = sum(1 for r in results.values() if r.get("score", 5) < PASS_SCORE or r.get("ok") is False)
    print(f"Đã duyệt {len(results)} ảnh, {bad} ảnh cần xử lý. Chi tiết: review/{mode}.json")


if __name__ == "__main__":
    main()
