"""Tiểu phẩm: dàn cảnh. AI xem ảnh nền từng nơi và chỉ chỗ đứng / ngồi + cỡ của từng vai, để nhân vật "ở trong" bối cảnh
(mèo ngồi trên sofa, chó cạnh ổ chó, người đứng ở cửa) thay vì xếp hàng dưới đáy khung.

  python skit/stage.py skits/<tên>

Mỗi nơi 2 lượt gọi model đọc ảnh (AI_MODEL_REVIEW): 1) ảnh nền có lưới tọa độ -> vị trí {x tâm, y chân, h chiều cao} theo tỉ lệ
khung; 2) ghép thử nhân vật vào nền theo vị trí đó, gửi lại để AI tự sửa (lơ lửng, to nhỏ sai, đè nhau). Ghi skit.json
"blocking": {nơi: {vai: {x, y, h}}}; ảnh ghép thử ở work/blocking_<nơi>.jpg. Đã có thì bỏ qua; lỗi thì skit/build.py xếp hàng.
"""
import io
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "skit")]
from llm import LLMError, chat, json_reply                    # noqa: E402
import build                                                  # noqa: E402  (dùng lại cách đặt nhân vật của bước dựng)

MODEL = os.environ.get("AI_MODEL_REVIEW") or "claude-sonnet-5-5"

PLACE = """Ảnh là nền một cảnh trong video dọc (khung 9:16, có lưới tọa độ: x từ 0 trái -> 1 phải, y từ 0 trên -> 1 dưới).
Nơi: {place}
Hãy dàn cảnh: đặt từng nhân vật dưới đây VÀO bối cảnh này cho tự nhiên, đúng vật / chỗ mà tư thế nói tới (ngồi trên sofa thì đáy
nhân vật nằm trên mặt nệm sofa, đứng thì chân chạm sàn, nằm trên ổ thì nằm trong ổ), đúng phối cảnh (xa thì nhỏ và cao hơn
trong khung, gần thì to và thấp hơn), đúng tỉ lệ thật so với đồ đạc (cửa cao ~2 m, sofa ~0,8 m) và so với nhau.
Nhân vật đứng: chân chạm sàn trống của nền. Nhân vật ngồi có sẵn ghế / bàn vẽ liền trong ảnh: đặt chân ghế / bàn chạm sàn
trống, không chồng lên đồ đạc của nền.
Video là khung DỌC xem trên điện thoại: nhân vật phải đủ lớn để thấy rõ mặt. Người đứng cao ≥ 0.40 khung, người ngồi nửa người
≥ 0.25 khung, thú cưng theo tỉ lệ với người; nếu đặt đúng cỡ so với đồ đạc mà quá nhỏ thì đưa nhân vật lên gần máy quay hơn (y lớn
hơn, phía trước bàn / sofa) thay vì thu nhỏ, có thể xếp người trước người sau. Ưu tiên rõ mặt hơn đúng tỉ lệ đồ đạc.
Ràng buộc: nhân vật không đè lên nhau quá 1/4; đầu không lên phần trên cùng 0.22 của khung (bị dải tiêu đề che); y chân trong
0.5-1.0; cả nhân vật nằm trong khung theo chiều ngang. Ảnh nhân vật là ảnh cắt sát mép, tỉ lệ rộng / cao ghi kèm.

Nhân vật:
{cast}

Trả về đúng một JSON {{"<tên>": {{"x": tâm ngang, "y": đáy ảnh nhân vật (chân / chỗ ngồi), "h": chiều cao ảnh nhân vật theo tỉ lệ
chiều cao khung, "why": "chỗ nào, vì sao"}}}}, không kèm chữ nào khác."""

CHECK = """Đây là ảnh ghép thử nhân vật vào nền theo dàn cảnh bạn vừa đưa (khung có lưới tọa độ như trước). Dàn cảnh hiện tại:
{blocking}
Kiểm tra từng nhân vật: có lơ lửng, chìm vào đồ đạc, to / nhỏ sai so với đồ đạc và người khác, đè nhau, lệch khỏi chỗ đáng ra
phải ở ({wants}) không? Sửa lại cho tự nhiên. Trả về đúng một JSON cùng dạng (đủ mọi nhân vật), không kèm chữ nào khác."""


def grid(img):
    """Ảnh kèm lưới tọa độ 0.1 để AI đọc vị trí."""
    img = img.convert("RGB").copy()
    d = ImageDraw.Draw(img)
    w, h = img.size
    for k in range(1, 10):
        x, y = w * k / 10, h * k / 10
        d.line((x, 0, x, h), fill=(255, 0, 80), width=1)
        d.line((0, y, w, y), fill=(255, 0, 80), width=1)
        d.text((x + 3, 3), f"{k / 10:.1f}", fill=(255, 0, 80))
        d.text((3, y + 3), f"{k / 10:.1f}", fill=(255, 0, 80))
    return img


def jpeg(img, width=720):
    img = img.convert("RGB")
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return buf.getvalue()


def valid(plan, members):
    out = {}
    for n in members:
        b = plan.get(n) if isinstance(plan, dict) else None
        if isinstance(b, dict) and all(isinstance(b.get(v), (int, float)) for v in ("x", "y", "h")):
            out[n] = {"x": round(min(max(b["x"], 0.0), 1.0), 3), "y": round(min(max(b["y"], 0.4), 1.05), 3),
                      "h": round(min(max(b["h"], 0.05), 0.9), 3), "why": str(b.get("why", ""))[:200]}
    return out


def preview(skit, raw, key, blocking):
    """Toàn cảnh ghép thử (ảnh gốc mỗi vai, biểu cảm thường) theo dàn cảnh."""
    trial = dict(skit, blocking={key: blocking})
    view = build.stage_view(trial, raw, key)
    img = view.bg.convert("RGBA")
    for inst in view.instances:
        pic = view.image(inst[0], "normal")
        img.alpha_composite(pic, (round(view.x[inst] - pic.width / 2), round(view.feet[inst] - pic.height)))
    return img


def main():
    folder = Path(sys.argv[1]).resolve()
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    cast = skit["cast"]
    sets = skit.get("sets") or {"main": skit.get("location", "")}
    done = skit.get("blocking") or {}
    raw = build.load_raw(folder, cast)
    for key, place in sets.items():
        members = [n for n in cast if cast[n].get("set", key) == key or len(sets) == 1]
        if not members or set(done.get(key, {})) >= set(members):
            continue
        bg = build.stage_view(skit, raw, key).bg
        lines = []
        for n in members:
            c, img = cast[n], raw[(n, "normal")]
            lines.append(f"- {n}: {c.get('look', '')[:160]}; tư thế: {c.get('pose', '')}; chỗ: {c.get('place') or 'tùy cảnh'}; "
                         f"cao ~{build.rel_height(c):.2f} lần người lớn; bản sao: {c['copies']}; ảnh rộng/cao = "
                         f"{img.width / img.height:.2f}")
        print(f"Dàn cảnh '{key}' bằng {MODEL}...", flush=True)
        try:
            plan = valid(json_reply(chat(PLACE.format(place=place, cast="\n".join(lines)), MODEL, image=jpeg(grid(bg)),
                                         max_tokens=3000)), members)
            if plan:
                trial = preview(skit, raw, key, plan)
                fixed = valid(json_reply(chat(CHECK.format(blocking=json.dumps(plan, ensure_ascii=False),
                                                           wants="; ".join(f"{n}: {cast[n].get('place') or cast[n].get('pose', '')}"
                                                                           for n in members)),
                                              MODEL, image=jpeg(grid(trial)), max_tokens=3000)), members)
                plan.update(fixed)
        except (LLMError, ValueError) as e:
            print(f"  lỗi dàn cảnh '{key}': {e} (dựng sẽ xếp hàng)", flush=True)
            continue
        if not plan:
            print(f"  '{key}': AI không trả vị trí hợp lệ (dựng sẽ xếp hàng)", flush=True)
            continue
        done[key] = plan
        (folder / "work").mkdir(exist_ok=True)
        preview(skit, raw, key, plan).convert("RGB").save(folder / "work" / f"blocking_{key}.jpg", quality=88)
        for n, b in plan.items():
            print(f"  {n}: x {b['x']:.2f}, chân {b['y']:.2f}, cao {b['h']:.2f} ({b['why']})", flush=True)
    skit["blocking"] = done
    (folder / "skit.json").write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
