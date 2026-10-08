"""Sửa vài cảnh của video đã xong bằng model ảnh (qua cổng AI), có xem trước. Không dùng Kaggle.

Bước 1, vẽ bản sửa (chưa đụng vào video):
  SHORTS_FIX='{"scenes": {"2": "tay cầm lon bị dị dạng"}}' python tools/fix_scenes.py videos/<tên> --edit
  SHORTS_FIX='{"images": {"002.png": "giữ lon bia"}}'       ...  --edit     # vẽ lại một ảnh đã có bản sửa
  Mỗi ảnh characters/NNN*.png của cảnh (kể cả nhiều nhân vật, tư thế _alt) -> bản sửa work/fix/<tên ảnh>, giữ ~90% giống
  ảnh cũ. Thoát mã 3: chờ người xem trên trang web (ảnh cũ | ảnh mới; Dùng / Vẽ lại / Bỏ).
Bước 2, áp dụng:
  SHORTS_FIX='{"apply": ["002.png"]}' python tools/fix_scenes.py videos/<tên> --apply
  Ảnh được chọn thay vào characters/ (ảnh cũ vào rejected/fix_<giờ>/), tách nền lại, dựng lại video
  (bản cũ: work/output_truoc_sua.mp4). Bản sửa không dùng bị bỏ.

AI_MODEL_IMAGE: model sửa ảnh (mặc định gemini-2.5-flash-image); AI_BASE_URL, AI_API_KEY như steps/llm.py.
Tiến trình cho trang web: work/fix_progress.json. Danh sách bản sửa: work/fix/state.json.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "tools")]
import llm                                   # noqa: E402
from common import image_stamp              # noqa: E402
from PIL import Image                        # noqa: E402

MODEL = os.environ.get("AI_MODEL_IMAGE") or "gemini-2.5-flash-image"
WAITING = 3     # mã thoát: bản sửa đã xong, chờ người xem (giống tools/auto.py)
PROMPT = (
    "Edit this illustration. Fix only what looks wrong: deformed or extra hands, fingers, arms, legs, broken anatomy, "
    "melted or malformed objects. {context}{note}"
    "The result must be anatomically correct: two arms, each with one natural hand with five fingers. If an extra hand "
    "or arm is the problem, remove the extra one cleanly. Keep a held object when it can be held naturally. "
    "Keep everything else as identical as possible (about 90% the same image): the same character, face, expression, "
    "hairstyle, clothes and colors, the same pose and framing, "
    "the same flat Irasutoya-style line art and shading, and the same plain solid {key} background filling the whole "
    "image. No text, no new objects, no shadows on the background."
)


def background_name(path):
    """Tên màu nền chroma của ảnh (lấy ở góc) để dặn model giữ nguyên, bước tách nền mới cắt đúng."""
    r, g, b = Image.open(path).convert("RGB").getpixel((2, 2))
    return "green" if g > r and g > b else "blue" if b > r and b > g else "magenta"


def scene_files(video, scene_id):
    """Ảnh nhân vật / đồ vật của một cảnh: NNN.png, NNN_<tên>.png, NNN_alt.png (không lẫn cảnh NNNx)."""
    stem = f"{int(scene_id):03d}"
    return [f for f in sorted((video / "characters").glob(f"{stem}*.png"))
            if f.stem[:3] == stem and (len(f.stem) == 3 or f.stem[3] == "_")]


def scene_context(scene):
    """Cảnh muốn thể hiện gì (theo kịch bản): để model biết tư thế, đồ vật nào là đúng khi sửa."""
    parts = [f"{k}: {scene[k]}" for k in ("action", "emotion") if scene.get(k)]
    return f"Intended scene ({', '.join(parts)}). " if parts else ""


def translate(note):
    """Ghi chú của người xem đưa thẳng cho model ảnh (Gemini hiểu tiếng Việt). Trước đây dịch qua model chữ, nhưng
    model đó lỗi trên cổng (claude-sonnet-5-5 "no available channel") làm mỗi lần sửa chờ thử lại ~50 giây."""
    note = " ".join(note.split())
    return f"The viewer's request (in Vietnamese, follow it exactly): \"{note}\". " if note else ""


class Fix:
    """Thư mục work/fix (bản sửa + state.json) và work/fix_progress.json của một video."""

    def __init__(self, video):
        self.video = video
        self.dir = video / "work" / "fix"
        self.state_file = self.dir / "state.json"
        self.items = json.loads(self.state_file.read_text(encoding="utf-8")).get("items", {}) \
            if self.state_file.exists() else {}
        self.progress = {"total": 0, "done": 0, "phase": "ai", "current": "", "started": time.time(), "scenes": []}

    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"items": self.items}, ensure_ascii=False, indent=1), encoding="utf-8")

    def report(self, **change):
        self.progress.update(change)
        (self.video / "work").mkdir(exist_ok=True)
        (self.video / "work" / "fix_progress.json").write_text(json.dumps(self.progress, ensure_ascii=False),
                                                                 encoding="utf-8")


def edit(video, request):
    """Vẽ bản sửa cho các cảnh / ảnh được yêu cầu, lưu vào work/fix/, không đụng vào ảnh của video."""
    fix = Fix(video)
    script = json.loads((video / "script.json").read_text(encoding="utf-8"))
    scenes = {int(sc["id"]): sc for sc in script.get("scenes", [])}
    todo = []                                   # (scene id, file ảnh gốc, ghi chú)
    for sid, note in (request.get("scenes") or {}).items():
        files = scene_files(video, sid)
        if not files:
            print(f"cảnh {sid}: không có ảnh nhân vật / đồ vật (cảnh chỉ có nền), bỏ qua", flush=True)
        todo += [(int(sid), f, note or "") for f in files]
    for name, note in (request.get("images") or {}).items():
        f = video / "characters" / Path(name).name
        if f.exists():
            todo.append((int(f.stem[:3]), f, note if note is not None else fix.items.get(f.name, {}).get("note", "")))
    if not todo:
        sys.exit("Không có ảnh nào để sửa.")
    fix.report(total=len(todo), scenes=sorted({sid for sid, _, _ in todo}))
    hints = {}
    for k, (sid, f, note) in enumerate(todo):
        fix.report(current=f"cảnh {sid} · {f.name}")
        print(f"cảnh {sid}: sửa {f.name} bằng {MODEL}" + (f" ({note.strip()})" if note.strip() else ""), flush=True)
        if note not in hints:
            hints[note] = translate(note)
        prompt = PROMPT.format(context=scene_context(scenes.get(sid, {})), note=hints[note], key=background_name(f))
        try:
            data = llm.edit_image(f.read_bytes(), prompt, MODEL)
        except llm.LLMError as e:
            sys.exit(f"cảnh {sid}: {e}")
        fix.dir.mkdir(parents=True, exist_ok=True)
        with Image.open(f) as original:
            size = original.size
        Image.open(io.BytesIO(data)).convert("RGB").resize(size, Image.LANCZOS).save(fix.dir / f.name)
        old = fix.items.get(f.name, {})
        fix.items[f.name] = {"scene": sid, "note": note, "tries": old.get("tries", 0) + 1, "updated": time.time()}
        fix.save()
        fix.report(done=k + 1)
    fix.report(phase="review", current="")
    print(f"Đã vẽ {len(todo)} bản sửa. Xem và chọn trên trang web (Dùng / Vẽ lại / Bỏ).", flush=True)
    sys.exit(WAITING)


def apply(video, names):
    """Thay ảnh đã chọn vào video, bỏ các bản sửa còn lại, tách nền và dựng lại."""
    fix = Fix(video)
    names = [Path(n).name for n in names if (fix.dir / Path(n).name).exists()]
    backup = video / "rejected" / time.strftime("fix_%Y%m%d-%H%M%S")
    fix.progress.update(scenes=sorted({int(fix.items.get(n, {}).get("scene", n[:3])) for n in names}),
                        total=len(names), done=len(names))
    for name in names:
        target = video / "characters" / name
        backup.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.copy2(target, backup / name)
        shutil.copy2(fix.dir / name, target)
        (video / "cutouts" / name).unlink(missing_ok=True)      # tách nền lại từ ảnh mới
        print(f"dùng bản sửa: {name}", flush=True)
    shutil.rmtree(fix.dir, ignore_errors=True)                   # bản sửa không chọn: bỏ
    if not names:
        print("Không áp dụng ảnh nào; đã bỏ các bản sửa.", flush=True)
        return
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"}
    fix.report(phase="cutouts")
    if subprocess.run([sys.executable, "steps/04_cutouts.py", str(video.relative_to(ROOT))], cwd=ROOT, env=env).returncode:
        sys.exit("Lỗi ở bước tách nền.")
    approved = video / "review" / "approved.json"          # ảnh đã đổi: cập nhật dấu duyệt để Chạy tiếp không hỏi lại
    if approved.exists():
        data = json.loads(approved.read_text(encoding="utf-8"))
        approved.write_text(json.dumps({**data, "stamp": image_stamp(video), "note": f"{data.get('note', '')} · "
                                        f"AI sửa {len(names)} ảnh"}, ensure_ascii=False), encoding="utf-8")
    if (video / "output.mp4").exists():
        shutil.copy2(video / "output.mp4", video / "work" / "output_truoc_sua.mp4")
    for phase, args in (("preview", [ROOT / "build_video.py", "--preview"]), ("build", [ROOT / "build_video.py"])):
        fix.report(phase=phase)
        if subprocess.run([sys.executable, *map(str, args)], cwd=video, env=env).returncode:
            sys.exit("Lỗi khi dựng lại video.")
    fix.report(phase="done")
    print(f"Xong: dựng lại {video / 'output.mp4'} với {len(names)} ảnh đã sửa; ảnh cũ ở {backup.relative_to(video)}",
          flush=True)


def main():
    video = Path(sys.argv[1]).resolve()
    request = json.loads(os.environ.get("SHORTS_FIX") or "{}")
    if "--apply" in sys.argv:
        return apply(video, request.get("apply") or [])
    if request and not any(k in request for k in ("scenes", "images")):
        request = {"scenes": request}           # dạng cũ: {id cảnh: ghi chú}
    edit(video, request)


if __name__ == "__main__":
    main()
