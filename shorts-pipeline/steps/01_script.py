"""Bước 1: model AI viết script.json từ một chủ đề. Gọi qua steps/llm.py (cổng chuẩn OpenAI, mặc định ShopAIKey):
cần AI_API_KEY, model chọn bằng AI_MODEL_SCRIPT.

  python steps/01_script.py videos/<tên> "chủ đề truyện"
  python steps/01_script.py videos/<tên> prompt.txt          # chủ đề hoặc cả câu chuyện dài, đọc từ file .txt

Quy tắc viết nằm ở config/script_guide.md (gửi nguyên văn cho model). Model được dùng lại nhân vật, bối cảnh có sẵn
hoặc khai thêm (new_characters, new_locations); thứ mới được ghi vào config/characters.json, config/locations.json
để các bước sau sinh ảnh chuẩn, ảnh nền và các video sau dùng lại.
Đã có script.json thì bỏ qua. Kịch bản có tên nhân vật / bối cảnh không khai báo thì không ghi, báo lỗi để chạy lại.
"""
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from common import CONFIG, LIBRARY, ROOT, load_json, normalize_script, video_dir
from llm import LLMError, chat, json_reply

MODEL = os.environ.get("AI_MODEL_SCRIPT") or os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
RECENT = 6             # số video gần nhất đưa vào phần "Gần đây đã dùng"

# giọng edge-tts cho nhân vật mới, theo loại giọng model chọn
VOICES = {
    "man": ("ja-JP-KeitaNeural", "+0%", "-5Hz"),
    "young_man": ("ja-JP-KeitaNeural", "+5%", "+5Hz"),
    "old_man": ("ja-JP-KeitaNeural", "-8%", "-20Hz"),
    "boy": ("ja-JP-KeitaNeural", "+10%", "+30Hz"),
    "woman": ("ja-JP-NanamiNeural", "+0%", "-5Hz"),
    "young_woman": ("ja-JP-NanamiNeural", "+5%", "+10Hz"),
    "old_woman": ("ja-JP-NanamiNeural", "-8%", "-20Hz"),
    "girl": ("ja-JP-NanamiNeural", "+10%", "+40Hz"),
}
BACKGROUND = "irasutoya_style, background illustration of {desc}, flat colors, simple shapes, no people, no text"
NAME = re.compile(r"[a-z][a-z0-9_]{1,39}")

PROMPT = """Viết kịch bản cho một video TikTok dọc, kể truyện ngắn bằng tiếng Nhật.

Đề tài người dùng nhập (có thể là một câu ngắn hoặc cả câu chuyện):
<<<
{topic}
>>>

Thể loại, góc kể, cấu trúc, độ dài, độ đa dạng: theo quy tắc ở cuối yêu cầu này (bắt buộc).

Nhân vật có sẵn ("narrator" chỉ là giọng kể, không xuất hiện trong ảnh). Dùng lại khi hợp; cần ai khác thì khai trong "new_characters":
{characters}

Bối cảnh có sẵn. Dùng lại khi hợp; cần nơi khác hoặc thời điểm, thời tiết khác thì khai trong "new_locations":
{locations}

Gần đây đã dùng (các video trước, tránh lặp lại để video này trông khác):
{recent}

Sticker có sẵn (đường dẫn dùng trong layers): {stickers}

Trả về đúng một đối tượng JSON, không kèm chữ nào khác, theo schema:
{{
  "title": ["dòng tiêu đề 1", "dòng tiêu đề 2"],
  "genre": "thể loại đã chọn (mục 0 quy tắc)",
  "font": "Noto Sans CJK JP", "font_file": "fonts/NotoSansCJKjp-Black.otf",
  "new_characters": {{"<tên_mới>": {{"prompt": "ngoại hình tiếng Anh", "voice": "man|woman|old_man|old_woman|boy|girl|young_man|young_woman", "colour": "#RRGGBB"}}}},
  "new_locations": {{"<tên_mới>": "mô tả tiếng Anh: nơi chốn, thời gian trong ngày, thời tiết, mùa, đồ vật đặc trưng"}},
  "speakers": {{"<tên speaker>": "<màu hex lấy từ colour của nhân vật>"}},
  "scenes": [{{
    "id": 1, "beat": "setup | rise1 | rise2 | rise3 | twist | ending",
    "text": "câu thoại tiếng Nhật", "speaker": "narrator",
    "characters": ["father"], "action": "tiếng Anh, tư thế và hành động, gồm cả đồ vật đang cầm (vd holding a glass beer mug)",
    "emotion": "tiếng Anh, một hai từ, cụ thể",
    "object": null,
    "shot": "full | half | close",
    "location": "dining_room", "filter": "none",
    "alt_pose": null,
    "layers": [ ... ]
  }}]
}}
"new_characters" và "new_locations" để {{}} nếu không cần thêm.

Quy tắc kỹ thuật cho layers (thứ tự là thứ tự vẽ). Mỗi lớp là MỘT trong 3 dạng, đúng tên khóa như sau
(khóa ảnh luôn là "image", không dùng "src", "file", "path" cho ảnh; "path" chỉ dùng cho đường đi):
  ảnh:     {{"id": "father", "image": "cutouts/001.png"}}            có thể thêm at, size, anim, path, over, start, duration
  chữ:     {{"word": "ドン", "size": 70, "vertical": true, "at": "top_right"}}
  hiệu ứng: {{"effect": "rays", "on": "father"}}
- Ảnh chủ thể: "cutouts/NNN.png" nếu cảnh có một nhân vật hoặc chỉ có đồ vật, "cutouts/NNN_<tên>.png" nếu nhiều nhân vật
  (NNN là id 3 chữ số). Đặt "id" bằng tên nhân vật (hoặc "objects") để lớp khác neo vào.
- Sticker: {{"image": "<đường dẫn trong danh sách sticker trên>", "at": "father.beside_right", "size": "tiny"}}.
- at / path: center, left, right, top, top_left, top_right, bottom, floor, floor_left, floor_right,
  off_left, off_right, off_top, off_bottom; hoặc "<id>.<điểm neo>" với điểm neo: center, top, bottom, left, right,
  above, head, beside_left, beside_right, hand_left, hand_right.
- size: tiny, small, medium, large, huge, hoặc số (chiều cao so với khung hình).
- anim, motion, transition: để trống thì bước dựng tự chọn cho đa dạng; chỉ ghi khi có chủ ý (xem mục 6 quy tắc).
  anim: nod, shake_no, sway, tilt, breathe, shiver, hop, sink, float, punch, spin_in, lean_in, rise, bounce, jump,
  pulse, approach, recede, exit_left, exit_right, slide_left, slide_right, drop, pop, pop_fade, none.
  Có thể thêm "start", "duration" (giây), "over" cho path.
- motion: punch_in, focus, dutch, drift, dolly_left, dolly_right, tilt_up, tilt_down, zoom_in, zoom_out, pan_left,
  pan_right, shake, none. transition: cut, fade, push_left, push_right, push_up, whip, zoom, flash, wipe, iris.
  filter: none hoặc sepia.

Quy tắc viết kịch bản (bắt buộc theo, kể cả thể loại, nhân vật, bối cảnh, shot, đồ vật, bố cục, sticker, chuyển động, độ đa dạng):

{guide}"""


def recent_usage(current):
    """Tóm tắt các video gần nhất đã dùng thể loại, nhân vật, bối cảnh nào, để model tránh lặp."""
    scripts = sorted((p for p in (ROOT / "videos").glob("*/script.json") if p.parent != current),
                     key=lambda p: p.stat().st_mtime, reverse=True)[:RECENT]
    if not scripts:
        return "(chưa có video nào)"
    genres, chars, locs, emotions = Counter(), Counter(), Counter(), Counter()
    titles = []
    for p in scripts:
        try:
            s = load_json(p)
        except ValueError:
            continue
        titles.append(" ".join(s.get("title", [])))
        genres[s.get("genre", "cảm động gia đình")] += 1
        for scene in s.get("scenes", []):
            chars.update(scene.get("characters", []))
            locs[scene.get("location", "")] += 1
            emotions[scene.get("emotion", "")] += 1
    top = lambda c, n: ", ".join(f"{k} ({v})" for k, v in c.most_common(n) if k)   # noqa: E731
    return (f"- Tiêu đề: {' / '.join(titles)}\n- Thể loại: {top(genres, 5)}\n"
            f"- Nhân vật dùng nhiều: {top(chars, 8)}\n- Bối cảnh dùng nhiều (số cảnh): {top(locs, 10)}\n"
            f"- Cảm xúc dùng nhiều: {top(emotions, 8)}")


def add_new(script, characters, locations):
    """Ghi nhân vật, bối cảnh mới model khai vào config/. Tên trùng thứ có sẵn thì giữ bản có sẵn. Trả về danh sách đã thêm."""
    added = []
    lock = CONFIG / ".config.lock"
    for _ in range(50):                         # nhiều người cùng tạo video: lần lượt từng người sửa file
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL)
            break
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 60:
                lock.unlink(missing_ok=True)
            time.sleep(0.2)
    else:
        sys.exit("config/ đang bị khóa quá lâu, thử lại.")
    try:
        characters.update(load_json(CONFIG / "characters.json"))     # đọc lại: có thể vừa có người thêm
        locations.update(load_json(CONFIG / "locations.json"))
        for name, spec in (script.get("new_characters") or {}).items():
            if name in characters or not NAME.fullmatch(name) or not isinstance(spec, dict) or not spec.get("prompt"):
                continue
            engine, rate, pitch = VOICES.get(spec.get("voice"), VOICES["woman"])
            colour = spec.get("colour") if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(spec.get("colour"))) else "#81C784"
            characters[name] = {"prompt": spec["prompt"].strip(), "lora": None,
                                "voice": {"engine": "edge", "name": engine, "rate": rate, "pitch": pitch}, "colour": colour}
            added.append(f"nhân vật {name}")
        for name, desc in (script.get("new_locations") or {}).items():
            if name in locations or not NAME.fullmatch(name) or not isinstance(desc, str) or not desc.strip():
                continue
            desc = re.sub(r"^\s*(irasutoya_style,\s*)?(background illustration of\s*)?", "", desc.strip())
            locations[name] = BACKGROUND.format(desc=desc.rstrip(". "))
            added.append(f"bối cảnh {name}")
        if added:
            for path, data in ((CONFIG / "characters.json", characters), (CONFIG / "locations.json", locations)):
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(path)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
    return added


def main():
    video = video_dir()
    if len(sys.argv) < 3:
        sys.exit('Dùng: python steps/01_script.py videos/<tên> "chủ đề truyện"')
    out = video / "script.json"
    if out.exists():
        return print("Đã có script.json, bỏ qua.")

    topic = sys.argv[2]
    if topic.endswith(".txt") and Path(topic).is_file():   # trang web ghi đề tài vào file: dài bao nhiêu cũng được
        topic = Path(topic).read_text(encoding="utf-8").strip()
    characters = load_json(CONFIG / "characters.json")
    locations = load_json(CONFIG / "locations.json")
    stickers = sorted(f"stickers/{p.name}" for p in (LIBRARY / "stickers").glob("*.png"))
    prompt = PROMPT.format(
        topic=topic,
        characters=json.dumps({k: {"prompt": v["prompt"], "colour": v["colour"]} for k, v in characters.items()},
                              ensure_ascii=False, indent=1),
        locations=json.dumps({k: BACKGROUND_DESC.sub("", v).replace(", flat colors, simple shapes, no people, no text", "")
                              for k, v in locations.items()}, ensure_ascii=False, indent=1),
        recent=recent_usage(video),
        stickers=", ".join(stickers) or "(chưa có)",
        guide=(CONFIG / "script_guide.md").read_text(encoding="utf-8"))   # quy tắc mở rộng, sửa trong file đó

    print(f"Viết kịch bản bằng {MODEL}...", flush=True)
    script, ask = None, prompt
    for attempt in range(1 + LENGTH_RETRIES):
        text = ""
        try:
            text = chat(ask, MODEL, max_tokens=32000)
            reply = json_reply(text)
        except LLMError as e:
            sys.exit(str(e))
        except ValueError:
            if script:                              # lần viết dài thêm hỏng: giữ bản trước
                break
            sys.exit(f"{MODEL} không trả về JSON hợp lệ. Thử lại hoặc chọn model khác. Đầu câu trả lời: {text[:300]}")
        if script is None or length(reply) > length(script):
            script = reply
        scenes, chars, seconds = length(script)
        print(f"  độ dài: {scenes} cảnh, {chars} ký tự lời, ước khoảng {seconds:.0f} giây", flush=True)
        if scenes >= MIN_SCENES and seconds >= MIN_SECONDS:
            break
        if attempt < LENGTH_RETRIES:
            print("  ngắn quá, nhờ model viết dài thêm...", flush=True)
            ask = prompt + LONGER.format(scenes=scenes, seconds=round(seconds),
                                         script=json.dumps(script, ensure_ascii=False))
    else:
        print(f"  CẢNH BÁO: kịch bản vẫn ngắn hơn {MIN_SECONDS} giây sau {LENGTH_RETRIES} lần viết thêm.")
    if length(script)[2] > MAX_SECONDS:
        print(f"  CẢNH BÁO: kịch bản ước {length(script)[2]:.0f} giây, dài hơn {MAX_SECONDS} giây.")

    from common import summarize_changes
    for line in summarize_changes(normalize_script(script)):   # gộp các dòng "bỏ null" cho log gọn
        print("  sửa kịch bản:", line)
    added = add_new(script, characters, locations)
    problems = []
    for scene in script["scenes"]:
        problems += [f"cảnh {scene['id']}: không có nhân vật '{n}'" for n in scene.get("characters", []) if n not in characters]
        if scene["location"] not in locations:
            problems.append(f"cảnh {scene['id']}: không có bối cảnh '{scene['location']}'")
        if scene["speaker"] not in characters:
            problems.append(f"cảnh {scene['id']}: speaker '{scene['speaker']}' không có giọng trong characters.json")
    for a in added:
        print("  thêm", a)
    if problems:                                # không ghi kịch bản hỏng: lần chạy sau viết lại
        (video / "work").mkdir(exist_ok=True)
        (video / "work" / "script_rejected.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit("Kịch bản dùng tên chưa khai báo:\n  " + "\n  ".join(problems[:10]) + "\nBấm Chạy tiếp để viết lại.")
    script.pop("new_characters", None)
    script.pop("new_locations", None)
    out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    locs = Counter(s["location"] for s in script["scenes"])
    print(f"Đã ghi {out}: {len(script['scenes'])} cảnh, thể loại {script.get('genre', '?')}, "
          f"{len(locs)} bối cảnh ({', '.join(f'{k} {v}' for k, v in locs.most_common())})")


BACKGROUND_DESC = re.compile(r"^irasutoya_style, background illustration of ")

# Độ dài bắt buộc: 80-100 giây (quá 105 giây chỉ cảnh báo). Ước theo tốc độ đọc tiếng Nhật đã tăng 1,2 lần (~8 ký tự/giây) cộng khoảng nghỉ mỗi cảnh.
MIN_SCENES, MIN_SECONDS, MAX_SECONDS, LENGTH_RETRIES = 45, 80, 105, 2
CHARS_PER_SECOND, GAP_PER_SCENE = 8.0, 0.35
LONGER = """

---
Bản kịch bản bạn vừa viết chỉ có {scenes} cảnh (ước {seconds} giây), NGẮN HƠN yêu cầu 80-100 giây (50-60 cảnh).
Viết lại TOÀN BỘ kịch bản cho đủ 50-60 cảnh: giữ cốt truyện, nhân vật, tiêu đề; thêm một nấc truyện, cảnh phản ứng, cảnh chèn
đồ vật, hồi tưởng, nền cảm xúc; tách câu dài thành 2-3 cảnh với hình khác nhau. Mỗi câu vẫn ngắn (6-14 ký tự).
Trả về JSON đầy đủ cùng định dạng như trên. Bản cũ:
{script}"""


def length(script):
    """(số cảnh, số ký tự lời, số giây ước tính) của kịch bản."""
    scenes = script.get("scenes") or []
    chars = sum(len(str(s.get("text", ""))) for s in scenes)
    return len(scenes), chars, chars / CHARS_PER_SECOND + len(scenes) * GAP_PER_SCENE

if __name__ == "__main__":
    main()
