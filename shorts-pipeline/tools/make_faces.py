"""Ảnh chớp mắt và mấp máy miệng cho nhân vật, để build_video.py cho nhân vật chớp mắt và nói (không cần Kaggle).

  python tools/make_faces.py videos/<tên>               # ảnh còn thiếu của mọi cảnh close / half
  python tools/make_faces.py videos/<tên> --only 2,7    # chỉ vài cảnh (thử)

Với mỗi ảnh nhân vật cutouts/NNN*.png ở cảnh khung close / half (mặt đủ to để thấy):
  cutouts/faces/<tên>_blink.png   mắt nhắm (mọi nhân vật)
  cutouts/faces/<tên>_talk.png    miệng mở (chỉ nhân vật đang nói câu của cảnh, speaker)
Cách làm: đặt ảnh lên nền xanh vuông, nhờ model ảnh (AI_MODEL_IMAGE, mặc định gemini-2.5-flash-image) nhắm mắt / mở
miệng, rồi CHỈ lấy vùng thay đổi ở phần đầu dán lên ảnh gốc (giữ nguyên độ trong suốt). Nhờ vậy ảnh mới khớp từng điểm
ảnh với ảnh gốc, chớp mắt không làm nhân vật giật. Model đổi quá nhiều (vùng thay đổi lớn) thì bỏ, cảnh đó không chớp.
Ảnh đã có thì bỏ qua; xóa file để làm lại. Cấu hình: mục [faces] trong config/settings.toml.
"""
import io
import json
import os
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps")]
import llm                                   # noqa: E402

CONF = {"enabled": True, "shots": ["close", "half"], "workers": 4,
        **tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8")).get("faces", {})}
MODEL = CONF.get("model") or os.environ.get("AI_MODEL_IMAGE") or "gemini-2.5-flash-image"
KEY = (0, 200, 60)            # nền xanh đặc khi gửi model
HEAD = 0.5                    # phần thân (dưới nửa này) dùng để căn ảnh mới khớp ảnh gốc
PROMPTS = {
    "blink": "Edit this flat illustration: close the character's eyes, as in the middle of a natural blink (eyelids "
             "closed, drawn as short curved lines in the same line style). Change NOTHING else: same face, mouth, "
             "hair, eyebrows, body, clothes, colors, position and size, same plain green background.",
    "talk": "Edit this flat illustration: open the character's mouth a little, as if in the middle of saying a word "
            "(small open mouth, same drawing style, keep the same expression). Change NOTHING else: same eyes, hair, "
            "face shape, body, clothes, colors, position and size, same plain green background.",
}


def square_on_key(cut):
    """Ảnh cắt nền (RGBA) đặt giữa ô vuông nền xanh. Trả về (ảnh vuông RGB, vị trí dán)."""
    side = max(cut.size) + 40
    canvas = Image.new("RGB", (side, side), KEY)
    at = ((side - cut.width) // 2, (side - cut.height) // 2)
    canvas.paste(cut, at, cut)
    return canvas, at


def best_shift(base, new, mask, reach=8):
    """Độ lệch (dx, dy) nhỏ nhất khớp ảnh mới với ảnh gốc, so ở phần thân (ngoài vùng đầu), trên ảnh thu nhỏ một nửa."""
    a, b = base[::2, ::2].astype(np.int16), new[::2, ::2].astype(np.int16)
    m = mask[::2, ::2]
    best, shift, r = None, (0, 0), reach // 2
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            moved = np.roll(np.roll(b, dy, 0), dx, 1)
            err = np.abs(moved - a).sum(axis=2)[m].mean()
            if best is None or err < best:
                best, shift = err, (dx * 2, dy * 2)
    return shift


# Dải nhận thay đổi, theo chiều cao vùng da mặt (từ trán dưới tóc tới cằm): ảnh chớp mắt chỉ lấy dải mắt, ảnh nói chỉ lấy
# dải miệng. Model hay đổi luôn chỗ khác (nói thì đổi cả mắt, chớp thì đổi cả miệng) -> phần đó bị bỏ, mặt không nhảy.
BANDS = {"blink": (0.10, 0.58), "talk": (0.60, 1.06)}
MAX_BAND_CHANGE = 0.30        # thay đổi > 30% vùng mặt: model vẽ lại cả mặt, bỏ


def face_box(rgb, alpha, top, bottom):
    """Khung vùng da mặt (x0, y0, x1, y1): mảng màu da lớn nhất trong phần đầu của nhân vật. None nếu không thấy."""
    from scipy import ndimage
    r, g, b = (rgb[:, :, k].astype(int) for k in range(3))
    skin = (r > 190) & (g > 120) & (g < 230) & (b > 80) & (b < 205) & (r - b > 30) & (alpha > 128)
    skin[:top] = False
    skin[bottom:] = False
    labels, count = ndimage.label(ndimage.binary_closing(skin, iterations=3))
    if not count:
        return None
    sizes = ndimage.sum(skin, labels, range(1, count + 1))
    ys, xs = np.nonzero(labels == int(np.argmax(sizes)) + 1)
    if len(ys) < 400:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()


def blink_local(cut):
    """Mắt nhắm vẽ bằng code (không gọi AI): mắt kiểu Irasutoya là chấm đen tròn trên da -> tô màu da lên chấm, vẽ
    một nét cong. Khớp tuyệt đối với ảnh gốc, không đụng lông mày, mũi. None nếu không thấy hai mắt dạng chấm
    (mắt đã nhắm ^ ^, kính râm, nhìn nghiêng...)."""
    from scipy import ndimage
    from PIL import ImageDraw
    rgb = np.asarray(cut.convert("RGB")).astype(int)
    alpha = np.asarray(cut)[:, :, 3]
    box = face_box(rgb.astype(np.uint8), alpha, 0, int(cut.height * 0.75))
    if box is None:
        return None
    fx0, fy0, fx1, fy1 = box
    fw, fh = fx1 - fx0, fy1 - fy0
    dark = (rgb.sum(axis=2) < 200) & (alpha > 128)
    region = np.zeros_like(dark)
    # vùng mắt: giữa mặt, bỏ hai mép (tóc mai cũng là mảng tối đặc, đứng ngang nhau như đôi mắt)
    top = int(fy0 + fh * 0.25)
    region[top:int(fy0 + fh * 0.62), int(fx0 + fw * 0.14):int(fx1 - fw * 0.14)] = True
    labels, count = ndimage.label(dark & region)
    eyes = []
    for k, sl in enumerate(ndimage.find_objects(labels), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = (labels[sl] == k).sum()
        if sl[0].start <= top:                  # dính lên mép trên vùng mắt: tóc, không phải mắt
            continue
        # chấm mắt: không quá nhỏ / lớn so với mặt, gần tròn hoặc bầu dục đứng, đặc (không phải lông mày, gọng kính)
        if not (fw * fh * 0.0008 < area < fw * fh * 0.03) or not (0.45 < w / h < 1.8) or area / (w * h) < 0.55:
            continue
        eyes.append((sl, k))
    eyes.sort(key=lambda e: -(labels[e[0]] == e[1]).sum())
    centre = (fx0 + fx1) / 2
    if len(eyes) >= 2:
        pair = sorted(eyes[:2], key=lambda e: e[0][1].start)
        ya, yb = ((e[0][0].start + e[0][0].stop) / 2 for e in pair)
        if abs(ya - yb) > fh * 0.08:          # hai chấm không ngang nhau: không phải đôi mắt
            return None
    elif len(eyes) == 1 and abs((eyes[0][0][1].start + eyes[0][0][1].stop) / 2 - centre) > fw * 0.12:
        pair = eyes                           # mặt đang nháy một mắt: chỉ còn một mắt chấm, lệch về một bên
    else:
        return None
    out = cut.copy()
    draw = ImageDraw.Draw(out)
    skin = np.median(rgb[int(fy0 + fh * 0.6):int(fy0 + fh * 0.75), fx0 + fw // 3:fx1 - fw // 3].reshape(-1, 3), axis=0)
    line = tuple(int(c) for c in np.median(rgb[dark & region].reshape(-1, 3), axis=0)) + (255,)
    for sl, k in pair:
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        mask = ndimage.binary_dilation(labels[sl] == k, iterations=2)
        patch = np.asarray(out)[y0 - 2:y1 + 2, x0 - 2:x1 + 2].copy() if y0 >= 2 and x0 >= 2 else None
        if patch is None:
            return None
        big = np.zeros(patch.shape[:2], bool)
        big[2:-2, 2:-2] = mask[:patch.shape[0] - 4, :patch.shape[1] - 4]
        big = ndimage.binary_dilation(big, iterations=1)
        patch[big, :3] = skin
        out.paste(Image.fromarray(patch), (x0 - 2, y0 - 2))
        w, h = x1 - x0, y1 - y0
        thick = max(2, round(h * 0.22))
        cy = y0 + h * 0.55
        draw.arc((x0 - w * 0.15, cy - h * 0.35, x1 + w * 0.15, cy + h * 0.45), 200, 340, fill=line, width=thick)
    return out


def make_variant(cut_path, kind):
    """Ảnh biến thể (RGBA, cùng cỡ ảnh gốc) hoặc None nếu model đổi quá nhiều."""
    cut = Image.open(cut_path).convert("RGBA")
    if kind == "blink":                         # chớp mắt: vẽ bằng code, không gọi AI
        return blink_local(cut), 0.0
    square, (x0, y0) = square_on_key(cut)
    buf = io.BytesIO()
    square.save(buf, "PNG")
    data = llm.edit_image(buf.getvalue(), PROMPTS[kind], MODEL)
    new = Image.open(io.BytesIO(data)).convert("RGB").resize(square.size, Image.LANCZOS)
    base = np.asarray(square).copy()
    out = np.asarray(new).copy()
    h, w = base.shape[:2]
    body = np.zeros((h, w), bool)
    body[int(y0 + cut.height * HEAD):y0 + cut.height, x0:x0 + cut.width] = True
    dx, dy = best_shift(base, out, body)
    out = np.roll(np.roll(out, dy, 0), dx, 1)
    # vùng thay đổi: chênh lệch màu lớn, chỉ trong nửa trên của nhân vật, nằm trên phần không trong suốt
    alpha = np.zeros((h, w), np.uint8)
    alpha[y0:y0 + cut.height, x0:x0 + cut.width] = np.asarray(cut)[:, :, 3]
    diff = np.abs(out.astype(np.int16) - base.astype(np.int16)).sum(axis=2) > 60
    box = face_box(base, alpha, y0, int(y0 + cut.height * 0.75))
    if box is None:
        return None, 1.0
    fx0, fy0, fx1, fy1 = box
    lo, hi = BANDS[kind]
    band = np.zeros((h, w), bool)
    band[int(fy0 + (fy1 - fy0) * lo):int(fy0 + (fy1 - fy0) * hi), fx0:fx1 + 1] = True
    changed = diff & band & (alpha > 128)
    share = changed.sum() / max((fx1 - fx0) * (fy1 - fy0), 1)
    if changed.sum() < 20 or share > MAX_BAND_CHANGE:
        return None, share
    mask = Image.fromarray((changed * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(
        ImageFilter.GaussianBlur(2))
    blended = Image.composite(Image.fromarray(out), square, mask)
    rgb = blended.crop((x0, y0, x0 + cut.width, y0 + cut.height))
    result = rgb.convert("RGBA")
    result.putalpha(cut.getchannel("A"))
    return result, share


def wanted(video):
    """(ảnh cutout, loại) cần tạo: blink cho mọi nhân vật ở cảnh close / half, talk cho nhân vật đang nói."""
    from common import character_variants, load_script
    script = load_script(video)
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    jobs = []
    sys.path.insert(0, str(ROOT))
    import variety
    voice = variety.main_voice(script)             # lời kể của giọng kể chính: không cần ảnh miệng mở
    for sc in script.get("scenes", []):
        if only and sc["id"] not in only:
            continue
        if sc.get("shot", "full") not in CONF["shots"] or not sc.get("characters"):
            continue
        speaker = sc.get("speaker", "")
        for who, filename in character_variants(sc):
            path = video / "cutouts" / filename
            if not path.exists():
                continue
            jobs.append((path, "blink"))
            if CONF.get("talk", True) and variety.is_dialogue(sc, voice) and who == speaker:
                jobs.append((path, "talk"))
    faces = video / "cutouts" / "faces"           # .skip: lần trước model đổi quá nhiều, không thử lại (đỡ tốn tiền)
    return [(p, k) for p, k in dict.fromkeys(jobs)
            if not (faces / f"{p.stem}_{k}.png").exists() and not (faces / f"{p.stem}_{k}.skip").exists()]


def main():
    video = Path(sys.argv[1]).resolve()
    if not CONF.get("enabled", True):
        return print("Mắt, miệng: đang tắt ([faces] enabled = false).")
    jobs = wanted(video)
    if not jobs:
        return print("Mắt, miệng: đủ ảnh, bỏ qua.")
    out = video / "cutouts" / "faces"
    out.mkdir(parents=True, exist_ok=True)
    print(f"Mắt, miệng: {len(jobs)} ảnh bằng {MODEL} ({CONF['workers']} luồng)", flush=True)

    def one(job):
        path, kind = job
        try:
            img, share = make_variant(path, kind)
        except llm.LLMError as e:
            return f"  {path.stem} {kind}: lỗi {str(e)[:120]}"
        if img is None:
            (out / f"{path.stem}_{kind}.skip").write_text(f"{share:.3f}")
            why = "không thấy mắt dạng chấm" if kind == "blink" else f"model đổi {share:.0%} vùng mặt"
            return f"  {path.stem} {kind}: bỏ ({why})"
        img.save(out / f"{path.stem}_{kind}.png")
        return f"  {path.stem} {kind}: xong" + (f" (đổi {share:.1%} vùng mặt)" if kind == "talk" else " (vẽ bằng code)")

    with ThreadPoolExecutor(CONF["workers"]) as pool:
        for line in pool.map(one, jobs):
            print(line, flush=True)


if __name__ == "__main__":
    main()
