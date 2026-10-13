"""Tiểu phẩm, bước 1: AI viết kịch bản tiểu phẩm (một bối cảnh, leo thang) theo skit/guide.md.

  python skit/write.py skits/<tên> "ý tưởng"        (hoặc đường dẫn file .txt chứa ý tưởng)
  python skit/write.py skits/<tên> --extend <giây>  đọc thật vẫn ngắn hơn 60 giây: AI viết thêm vào skit.json đã có
  python skit/write.py skits/<tên> --direct         lượt "đạo diễn": AI lên kế hoạch dựng (grade, fx, bigword, sfx,
                                                    góc máy, dấu cảm xúc) cho kịch bản đã viết, KHÔNG đổi lời thoại

Ghi skits/<tên>/skit.json. Đã có thì bỏ qua. AI_MODEL_SCRIPT, AI_BASE_URL, AI_API_KEY như steps/llm.py.
Chức năng riêng, không đụng pipeline truyện kể (videos/).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "steps"))
from llm import LLMError, chat, json_reply   # noqa: E402

MODEL = os.environ.get("AI_MODEL_SCRIPT") or "claude-sonnet-5-5"
VOICES = json.loads((ROOT / "config" / "voicevox_voices.json").read_text(encoding="utf-8"))["voices"]
FORMATS = ("loop", "list", "incident", "story", "misunderstanding", "interview", "reaction", "free")
DIRECTED = ("shot", "fx", "bigword", "sfx", "sfx_at", "mark", "glow", "size", "emphasis", "stack")   # trường lượt đạo diễn được sửa
FX = ("zoom_punch", "shake", "flash", "invert", "focus_lines", "gloom_lines", "sparkle_bg", "speed_lines", "spotlight",
      "freeze", "blackout", "split")
GRADES = ("none", "retro", "warm", "cool", "night")          # bỏ "noir": đen trắng cả video làm mất màu Irasutoya (skit-006)
MARKS = ("gloom", "sweat", "anger", "sparkle", "shock", "none")
EXPRESSIONS = ("normal", "happy", "shocked", "angry", "sad", "panic", "smug", "crying", "embarrassed", "thinking",
               "disgusted", "sleepy")
TONES = ("normal", "happy", "excited", "angry", "sad", "crying", "whisper", "scared", "calm")
SIZES = ("small", "normal", "big", "shout")

PROMPT = """Viết một TIỂU PHẨM hài tiếng Nhật cho video TikTok dọc, theo quy tắc ở cuối (bắt buộc).

Ý tưởng người dùng:
<<<
{idea}
>>>
{forced}
Giọng VOICEVOX có thể chọn (tên, giới tính, tuổi, chất giọng):
{voices}

Trả về đúng một JSON, không kèm chữ nào khác:
{{
  "title": ["dòng 1 ngắn gây tò mò", "dòng 2"],
  "format": "loop | list | incident | story | misunderstanding | interview | reaction | free",
  "structure": ["chỉ khi format là free: 3-6 nhịp tự thiết kế"],
  "grade": "none | noir | retro | warm | cool | night",
  "sets": {{"main": "bối cảnh tiếng Anh: nơi, giờ, đồ đạc đặc trưng"}},
  "cast": {{"sk_<tên>": {{"look": "ngoại hình tiếng Anh", "pose": "tư thế chung tiếng Anh", "voice": "<tên giọng>",
            "colour": "#RRGGBB", "height": 1.0, "place": "chỗ trong cảnh tiếng Anh", "slot": "left|center|right", "set": "main", "copies": 1, "expressions": ["normal", "..."],
            "poses": {{"<tên_tư_thế>": "tư thế khác tiếng Anh"}}}}}},
  "lines": [{{"speaker": "sk_<tên>", "text": "câu tiếng Nhật", "tone": "normal", "size": "normal", "emphasis": [],
             "expression": {{}}, "pose": {{}}, "mark": {{}}, "shot": "wide", "stack": false, "chapter": null, "insert": null,
             "silent": false, "glow": false, "fx": [], "bigword": null, "sfx": null, "sfx_at": "start"}}]
}}

Quy tắc:
{guide}"""

LONGER = """

---
Bản tiểu phẩm vừa viết chỉ khoảng {seconds} giây, NGẮN hơn yêu cầu (ít nhất 60 giây, nhắm 65-75 giây).
Viết lại TOÀN BỘ, giữ nhân vật, bối cảnh, tiêu đề; thêm 1-2 vòng / mục leo thang nữa và câu chốt cuối; 45-55 câu.
Trả về JSON đầy đủ như trên. Bản cũ:
{skit}"""

SHORTER = """

---
Bản tiểu phẩm vừa viết khoảng {seconds} giây, DÀI hơn yêu cầu (60-80 giây cho video ngắn, nhắm 70).
Viết lại TOÀN BỘ, giữ nhân vật, bối cảnh, tiêu đề, móc câu đầu và cú chốt; bỏ vòng / mục / đoạn yếu nhất, gộp câu thừa; 40-50 câu.
Trả về JSON đầy đủ như trên. Bản cũ:
{skit}"""

EXTEND = """Đây là một TIỂU PHẨM tiếng Nhật đã viết. Đọc thật bằng VOICEVOX chỉ được {seconds} giây, cần ÍT NHẤT 60 giây (nhắm 64).
Viết thêm khoảng {more} câu: thêm 1-2 vòng / mục leo thang mới ĐẶT TRƯỚC cú chốt cuối, giữ nguyên mọi câu cũ, nhân vật
(không thêm nhân vật, không thêm biểu cảm ngoài danh sách đã có), bối cảnh, tiêu đề. Trả về JSON ĐẦY ĐỦ (mọi câu cũ + câu mới),
cùng dạng, không kèm chữ nào khác.

Quy tắc:
{guide}

Bản hiện tại:
{skit}"""

DIRECT = """Bạn là ĐẠO DIỄN DỰNG của một tiểu phẩm hài tiếng Nhật dạng video dọc (nhân vật kiểu Irasutoya đứng trên sân
khấu, chữ thoại theo người nói). Kịch bản đã viết xong; việc của bạn là lên kế hoạch DỰNG cho từng câu để tăng tiếng cười:
nhịp, bất ngờ, đối lập, gài và trả; câu 1 phải giữ người xem ngay khung đầu (mục "Giữ chân người xem"). Hãy sáng tạo: mỗi tiểu phẩm một phong cách dựng riêng hợp nội dung, không công thức.

Được sửa ở từng câu: "shot", "fx", "bigword", "sfx", "sfx_at", "mark", "glow", "size", "emphasis", "stack". Ở cấp video: "grade".
KHÔNG được đổi: "text", "speaker", "tone", "expression", "pose", "insert", "silent", số câu, thứ tự câu, "cast", "sets", "title".
Quy tắc các trường ở dưới (mục "Cách dựng" là trọng tâm).

Trả về đúng một JSON {{"grade": "...", "lines": [{{"shot": ..., "fx": [...], "bigword": ..., "sfx": ..., "sfx_at": ...,
"mark": {{...}}, "glow": ..., "size": ..., "emphasis": [...], "stack": ...}}, ...]}} với ĐÚNG {count} phần tử theo thứ tự câu,
không kèm chữ nào khác.

Quy tắc:
{guide}

Kho tiếng hiệu ứng (効果音ラボ). Với "sfx": trước hết tự nghĩ khoảnh khắc đó cần đúng tiếng gì (đừng để danh sách dẫn dắt
chọn chỗ đặt tiếng); rồi tra danh sách này: có tên khớp đúng nghĩa thì chép ĐÚNG tên (không thêm số); không có tên nào thật khớp
thì ghi mô tả tiếng Nhật cụ thể của tiếng cần (hệ thống tự tìm), đừng chép một tên chỉ gần nghĩa:
{sounds}

Kịch bản:
{skit}"""

MAX_ESTIMATE = 84                            # ước > 84 giây thì viết lại ngắn hơn (đọc thật thường thấp hơn ước ~5%)
CHARS_PER_SECOND, GAP = 7.5, 0.12            # ước độ dài khi đọc nhanh (VOICEVOX tốc độ tiểu phẩm), kiểm lại sau khi đọc thật


def estimate(skit):
    lines = skit.get("lines") or []
    return sum(len(str(l.get("text", ""))) for l in lines) / CHARS_PER_SECOND + len(lines) * GAP


def clean(skit):
    """Sửa chỗ model viết lệch để các bước sau chạy chắc; trả về danh sách lỗi không sửa được."""
    problems = []
    cast = skit.get("cast") or {}
    sets = skit.get("sets") if isinstance(skit.get("sets"), dict) and skit.get("sets") else {}
    if not sets:
        sets = {"main": str(skit.get("location") or "a simple room")}
    skit["sets"] = {re.sub(r"[^a-z0-9_]", "_", str(k).lower()) or "main": str(v) for k, v in list(sets.items())[:2]}
    skit["location"] = next(iter(skit["sets"].values()))
    skit["grade"] = skit.get("grade") if skit.get("grade") in GRADES else "none"
    if os.environ.get("SKIT_FORMAT") in FORMATS:            # người dùng chọn khuôn trên trang web
        skit["format"] = os.environ["SKIT_FORMAT"]
    skit["format"] = skit.get("format") if skit.get("format") in FORMATS else "free"     # khuôn lạ model tự đặt: coi là tự do
    if skit["format"] == "free":
        beats = skit.get("structure") if isinstance(skit.get("structure"), list) else []
        skit["structure"] = [str(b) for b in beats if str(b).strip()][:6]
    else:
        skit.pop("structure", None)
    for name in list(cast):
        c = cast[name]
        if not re.fullmatch(r"sk_[a-z0-9_]+", name):
            problems.append(f"tên nhân vật '{name}' phải dạng sk_<tiếng Anh>")
        c["expressions"] = [e for e in dict.fromkeys(["normal", *c.get("expressions", [])]) if e in EXPRESSIONS][:6]
        c["copies"] = max(1, min(int(c.get("copies") or 1), 6))
        if c.get("voice") not in VOICES:
            c["voice"] = next(iter(VOICES))
        c.setdefault("slot", "center")
        try:
            c["height"] = round(min(max(float(c.get("height") or 1.0), 0.1), 1.4), 2)
        except (TypeError, ValueError):
            c["height"] = 1.0
        c["place"] = str(c.get("place") or "")[:160]
        poses = c.get("poses") if isinstance(c.get("poses"), dict) else {}
        c["poses"] = {re.sub(r"[^a-z0-9_]", "_", str(k).lower()): str(v) for k, v in list(poses.items())[:4] if str(v).strip()}
        if c.get("set") not in skit["sets"]:
            c["set"] = next(iter(skit["sets"]))
        c.setdefault("pose", "standing, facing forward")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(c.get("colour", ""))):
            c["colour"] = "#1E5AA8"
    for k, line in enumerate(skit.get("lines") or []):
        if line.get("speaker") not in cast:
            problems.append(f"câu {k + 1}: speaker '{line.get('speaker')}' không có trong cast")
        line["tone"] = line.get("tone") if line.get("tone") in TONES else "normal"
        line["size"] = line.get("size") if line.get("size") in SIZES else "normal"
        line["emphasis"] = [w for w in (line.get("emphasis") or []) if isinstance(w, str) and w in str(line.get("text", ""))]
        exp = line.get("expression") if isinstance(line.get("expression"), dict) else {}
        line["expression"] = {n: e for n, e in exp.items() if n in cast and e in EXPRESSIONS}
        line["shot"] = str(line.get("shot") or "wide")
        pose = line.get("pose") if isinstance(line.get("pose"), dict) else {}
        line["pose"] = {n: q for n, q in pose.items() if n in cast and (q == "default" or q in cast[n]["poses"])}
        mark = line.get("mark") if isinstance(line.get("mark"), dict) else {}
        line["mark"] = {n: m for n, m in mark.items() if n in cast and m in MARKS}
        line["insert"] = str(line["insert"]).strip() if isinstance(line.get("insert"), str) and line["insert"].strip() else None
        line["silent"] = bool(line.get("silent"))
        line["glow"] = bool(line.get("glow"))
        fx = line.get("fx") if isinstance(line.get("fx"), list) else [line["fx"]] if isinstance(line.get("fx"), str) else []
        line["fx"] = [f for f in fx if f in FX and (f != "split" or len(skit["sets"]) > 1)][:2]
        for key in ("bigword", "sfx"):
            line[key] = str(line[key]).strip() if isinstance(line.get(key), str) and line[key].strip() else None
        line["sfx_at"] = "end" if line.get("sfx_at") == "end" else "start"
    from assets import normalize_assets
    _, asset_errors = normalize_assets(skit)
    return problems + asset_errors


def extend(folder, seconds):
    out = folder / "skit.json"
    old = json.loads(out.read_text(encoding="utf-8"))
    more = max(6, round((64 - seconds) * len(old["lines"]) / max(seconds, 1)) + 2)
    print(f"Tiểu phẩm {seconds:.0f} giây, nhờ {MODEL} viết thêm ~{more} câu...", flush=True)
    try:
        skit = json_reply(chat(EXTEND.format(seconds=round(seconds), more=more, skit=json.dumps(old, ensure_ascii=False),
                                             guide=(ROOT / "skit" / "guide.md").read_text(encoding="utf-8")),
                               MODEL, max_tokens=24000))
    except (LLMError, ValueError) as e:
        sys.exit(f"Không viết thêm được: {e}")
    skit["cast"] = old["cast"]                     # giữ nhân vật (ảnh đã / sắp vẽ theo cast cũ)
    for key in ("title", "format", "grade", "location", "sets", "background", "backgrounds", "inserts", "sounds"):
        if key in old:
            skit[key] = old[key]
    problems = clean(skit)
    if problems or len(skit.get("lines") or []) <= len(old["lines"]):
        sys.exit("Bản viết thêm có lỗi hoặc không dài hơn:\n  " + "\n  ".join(problems[:10]))
    out.write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi {out}: {len(old['lines'])} -> {len(skit['lines'])} câu")


def direct(folder):
    """Lượt đạo diễn: chỉ ghi các trường dựng; lời thoại và mọi thứ cần ảnh / giọng giữ nguyên."""
    out = folder / "skit.json"
    skit = json.loads(out.read_text(encoding="utf-8"))
    if skit.get("directed"):
        return print("Đã có kế hoạch dựng, bỏ qua.")
    view = {"title": skit["title"], "format": skit.get("format"), "sets": skit.get("sets"),
            "cast": {n: {k: c.get(k) for k in ("look", "pose", "poses", "set", "copies", "expressions")} for n, c in skit["cast"].items()},
            "lines": skit["lines"]}
    print(f"Lên kế hoạch dựng bằng {MODEL}...", flush=True)
    try:
        sys.path.insert(0, str(ROOT / "skit"))
        from sounds import compact                  # danh mục gọn ~1.800 tên tiếng trong kho
        plan = json_reply(chat(DIRECT.format(count=len(skit["lines"]), skit=json.dumps(view, ensure_ascii=False),
                                             sounds=compact()[0],
                                             guide=(ROOT / "skit" / "guide.md").read_text(encoding="utf-8")),
                               MODEL, max_tokens=24000))
    except (LLMError, ValueError) as e:
        sys.exit(f"Không lên được kế hoạch dựng: {e}")
    lines = plan.get("lines") if isinstance(plan, dict) else None
    if not isinstance(lines, list) or len(lines) != len(skit["lines"]):
        sys.exit(f"Kế hoạch dựng sai số câu ({len(lines or [])} / {len(skit['lines'])}).")
    for line, new in zip(skit["lines"], lines):
        if isinstance(new, dict):
            line.update({k: new[k] for k in DIRECTED if k in new})
    skit["grade"] = plan.get("grade", skit.get("grade"))
    problems = clean(skit)
    if problems:
        sys.exit("Kế hoạch dựng có lỗi:\n  " + "\n  ".join(problems[:10]))
    skit["directed"] = True
    out.write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    used = [f for l in skit["lines"] for f in l["fx"]]
    print(f"Kế hoạch dựng: grade {skit['grade']}, {len(used)} kỹ xảo ({', '.join(sorted(set(used)))}), "
          f"{sum(bool(l['bigword']) for l in skit['lines'])} chữ tượng thanh, {sum(bool(l['sfx']) for l in skit['lines'])} tiếng")


def main():
    folder = Path(sys.argv[1]).resolve()
    out = folder / "skit.json"
    if "--direct" in sys.argv:
        return direct(folder)
    if len(sys.argv) > 3 and sys.argv[2] == "--extend":
        return extend(folder, float(sys.argv[3]))
    if out.exists():
        return print("Đã có skit.json, bỏ qua.")
    idea = sys.argv[2]
    if idea.endswith(".txt") and Path(idea).is_file():
        idea = Path(idea).read_text(encoding="utf-8").strip()
    fmt = os.environ.get("SKIT_FORMAT", "")
    forced = f"\nKhuôn bắt buộc: {fmt} (xem mục \"Chọn một khuôn\").\n" if fmt in FORMATS else ""
    prompt = PROMPT.format(idea=idea, forced=forced, guide=(ROOT / "skit" / "guide.md").read_text(encoding="utf-8"),
                           voices="\n".join(f"- {n}: {v['gender']}, {v['age']}; {v['desc']}" for n, v in VOICES.items()))
    print(f"Viết tiểu phẩm bằng {MODEL}...", flush=True)
    skit, ask = None, prompt
    for attempt in range(3):
        try:
            reply = json_reply(chat(ask, MODEL, max_tokens=24000))
        except LLMError as e:
            sys.exit(str(e))
        except ValueError:
            if skit:
                break
            sys.exit(f"{MODEL} không trả về JSON hợp lệ. Thử lại hoặc chọn model khác.")
        # giữ bản gần khoảng 64-82 giây nhất (đủ 60 giây khi đọc thật, không quá dài cho video ngắn)
        if skit is None or abs(estimate(reply) - 72) < abs(estimate(skit) - 72):
            skit = reply
        seconds = estimate(skit)
        print(f"  {len(skit.get('lines', []))} câu, ước {seconds:.0f} giây", flush=True)
        if 64 <= seconds <= MAX_ESTIMATE or attempt == 2:
            break
        retry = SHORTER if seconds > MAX_ESTIMATE else LONGER
        ask = prompt + retry.format(seconds=round(seconds), skit=json.dumps(skit, ensure_ascii=False))
    problems = clean(skit)
    if problems:
        (folder / "work").mkdir(parents=True, exist_ok=True)
        (folder / "work" / "skit_rejected.json").write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit("Tiểu phẩm có lỗi:\n  " + "\n  ".join(problems[:10]) + "\nBấm Chạy tiếp để viết lại.")
    out.write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Đã ghi {out}: {len(skit['lines'])} câu, {len(skit['cast'])} nhân vật, khuôn {skit.get('format')}")


if __name__ == "__main__":
    main()
