"""Tạo videos/<tên>/jobs.json từ script.json: mọi ảnh còn thiếu để dựng video. Không gọi Claude.

  python tools/make_jobs.py videos/<tên>

Các loại job, phân biệt bằng tiền tố tên (tools/run_kaggle.py dùng tiền tố này để chép ảnh về đúng chỗ):
  bg_<bối cảnh>      ảnh nền, prompt từ config/locations.json, LoRA và cỡ từ [background]  -> library/backgrounds/
  ref_<nhân vật>     ảnh chuẩn nhân vật đứng thẳng, chỉ tạo khi config/refs/ chưa có         -> config/refs/<nhân vật>_front.png
  ch_<cảnh>          ảnh chủ thể của một cảnh                                                 -> characters/<cảnh>.png
                     - có nhân vật: sinh từ ảnh chuẩn, đồ vật nhân vật cầm vẽ luôn trong ảnh (ghi trong "action"),
                       khung hình theo "shot" (full / half / close, mục [shots] của config/settings.toml)
                     - không có nhân vật: đồ vật là chủ thể, mô tả trong "object"
  ch_<cảnh>_alt      tư thế thứ hai (cảnh có "alt_pose"), sửa từ ảnh gốc của cảnh          -> characters/<cảnh>_alt.png
Ảnh nào đã có thì không tạo job. Ảnh nền và ảnh chuẩn dùng chung cho mọi video.
Muốn sinh lại một ảnh: xóa file ảnh đó rồi chạy lại lệnh này.
"""
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "steps"))
from common import TRIGGER, character_files   # noqa: E402

CAST = "{trigger}, {look}, standing straight facing forward, arms down, calm neutral face, full body, white background"
SCENE = ("{trigger}, the same person as in the reference image, wearing exactly the same clothes, colors and "
         "accessories as in the reference image, {look}, {action}, {emotion} face, {framing}, "
         "only this one person and the items in their hands, no furniture, no seat, no door, no window, no wall, "
         "no pole, no strap, no counter, {background}")
OBJECT = ("{trigger}, simple flat cartoon clip art illustration of {desc}, thick clean outlines, flat colors, minimal detail, "
          "cute simple shapes, not a photo, not realistic, not 3D, no texture, no people, {background}")
ALT = ("{trigger}, change only the pose: {pose}. keep the same character, face, hairstyle, accessories, clothes, "
       "held objects, colors, size, position, framing and background unchanged")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    video = Path(sys.argv[1]).resolve()
    settings = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))
    bg, shots = settings["background"], settings["shots"]
    key = settings["cutout"]["key_prompt"]     # nền màu đặc để tách nền theo màu (áo trắng, bọt bia không bị khoét)
    characters = load(ROOT / "config" / "characters.json")
    locations = load(ROOT / "config" / "locations.json")
    script = load(video / "script.json")
    from common import normalize_script
    from common import summarize_changes
    for line in summarize_changes(normalize_script(script)):   # gộp các dòng "bỏ null" cho log gọn
        print("  sửa kịch bản:", line)
    refs = ROOT / "config" / "refs"

    wrong = [s["id"] for s in script["scenes"] if s.get("shot", "full") not in shots]
    if wrong:
        sys.exit(f"Cảnh {wrong}: \"shot\" phải là một trong {list(shots)}")
    old = [s["id"] for s in script["scenes"] if s.get("props")]
    if old:
        sys.exit(f"Cảnh {old} còn trường \"props\". Đồ vật giờ vẽ luôn trong ảnh: ghi vào \"action\" "
                 f"(vd \"holding a glass beer mug\"), hoặc \"object\" nếu cảnh không có nhân vật. Xem README.md.")

    def have(*paths):
        return any(p.exists() for p in paths)

    backgrounds, cast, scenes, alts = [], {}, [], []
    fixes = corrections(video)                  # câu sửa khi vẽ lại (AI chấm, ghi chú người duyệt)

    def fixed(prompt, key):
        """Đặt câu sửa ngay sau từ khóa phong cách: phần đầu prompt được model coi trọng hơn."""
        fix = fixes.get(key)
        if not fix:
            return prompt
        head = f"{TRIGGER}, "
        return f"{head}{fix}, {prompt[len(head):]}" if prompt.startswith(head) else f"{fix}, {prompt}"
    for loc in sorted({s["location"] for s in script["scenes"]}):
        if have(ROOT / "library" / "backgrounds" / f"{loc}.png", video / "backgrounds" / f"{loc}.png"):
            continue
        if loc not in locations:
            sys.exit(f"Thiếu prompt bối cảnh '{loc}' trong config/locations.json")
        job = {"name": f"bg_{loc}", "prompt": fixed(locations[loc], f"backgrounds/{loc}.png"), "lora": bg["lora"],
               "width": bg["width"], "height": bg["height"], "fix": fixes.get(f"backgrounds/{loc}.png", "")}
        rejected = sum(1 for f in (ROOT / "library" / "backgrounds" / "rejected").glob(f"{loc}*.png")
                       if f.stem == loc or f.stem[len(loc):].lstrip("_").isdigit())
        if rejected:                                   # ảnh nền bị bỏ khi duyệt: đổi seed để không vẽ lại y hệt
            job["seed"] = settings["generation"]["seed"] + 1000 * rejected
        backgrounds.append(job)

    for scene in script["scenes"]:
        for k, (name, filename) in enumerate(character_files(scene)):
            stem = Path(filename).stem
            # ảnh bị loại (review.py chuyển sang rejected/) thì đổi seed, không sinh lại y hệt ảnh cũ
            seed = scene["id"] * 10 + k + 1000 * len(list((video / "rejected").glob(f"{stem}*.png")))
            base_new = not have(video / "characters" / filename, video / "cutouts" / filename)
            if base_new and name is None:                  # cảnh chỉ có đồ vật
                scenes.append({"name": f"ch_{stem}", "seed": seed, "fix": fixes.get(f"characters/{filename}", ""),
                               "prompt": fixed(OBJECT.format(trigger=TRIGGER, desc=scene["object"],
                                                             background=key_for(scene["object"])),
                                               f"characters/{filename}")})
            elif base_new:
                if name not in characters or not characters[name].get("prompt"):
                    sys.exit(f"Cảnh {scene['id']}: nhân vật '{name}' không có mô tả trong config/characters.json")
                look = characters[name]["prompt"]
                # "ref": dùng chung ảnh chuẩn với nhân vật khác (vd mẹ mặc áo bệnh nhân dùng ảnh chuẩn của mẹ)
                owner = characters[name].get("ref", name)
                ref = refs / f"{owner}_front.png"
                if not ref.exists() and owner not in cast:  # ảnh chuẩn sinh cùng lần chạy, cảnh dùng bằng "@ref_..."
                    cast[owner] = {"name": f"ref_{owner}",
                                   "prompt": CAST.format(trigger=TRIGGER, look=characters[owner]["prompt"])}
                scenes.append({"name": f"ch_{stem}", "seed": seed, "fix": fixes.get(f"characters/{filename}", ""),
                               "refs": [f"ref__{ref.name}" if ref.exists() else f"@ref_{owner}"],
                               "prompt": fixed(SCENE.format(trigger=TRIGGER, look=look, action=scene["action"],
                                                            emotion=scene["emotion"],
                                                            framing=shots[scene.get("shot", "full")]["prompt"],
                                                            background=key_for(look, scene["action"])),
                                                f"characters/{filename}")})

            # tư thế thứ hai: sửa từ ảnh gốc của chính cảnh này để nhân vật và vị trí giữ nguyên
            pose = alt_pose(scene, name)
            if not pose or have(video / "characters" / f"{stem}_alt.png", video / "cutouts" / f"{stem}_alt.png"):
                continue
            if base_new:
                base = f"@ch_{stem}"                               # ảnh gốc sinh cùng lần chạy
            elif (video / "characters" / filename).exists():
                base = f"char__{filename}"                         # ảnh gốc đã có ở characters/
            else:
                print(f"  bỏ qua {stem}_alt: cần characters/{filename} (ảnh gốc nền trắng) để sửa ra tư thế thứ hai")
                continue
            alts.append({"name": f"ch_{stem}_alt", "seed": seed + 500, "refs": [base],
                         "fix": fixes.get(f"characters/{stem}_alt.png", ""),
                         "prompt": fixed(ALT.format(trigger=TRIGGER, pose=pose), f"characters/{stem}_alt.png")})

    # mỗi job đứng sau job nó tham chiếu: ảnh chuẩn -> ảnh cảnh -> tư thế thứ hai (quy tắc của run_kaggle.py)
    jobs = list(cast.values()) + scenes + alts + backgrounds
    (video / "jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{video.name}/jobs.json: {len(jobs)} job ({len(cast)} ảnh chuẩn, {len(scenes)} ảnh cảnh, "
          f"{len(alts)} tư thế thứ hai, {len(backgrounds)} nền)")


def corrections(video):
    """Câu sửa cho từng ảnh khi vẽ lại: "fix" AI ghi ở review/images.json (ảnh bị chấm vẽ lại) và ghi chú người duyệt
    ở review/notes.json. Ghi chú không phải tiếng Anh thì nhờ model AI dịch (cần AI_API_KEY), dịch rồi lưu lại để không dịch lại."""
    ai = load(video / "review" / "images.json") if (video / "review" / "images.json").exists() else {}
    notes_file = video / "review" / "notes.json"
    notes = load(notes_file) if notes_file.exists() else {}
    fixes = {k: r["fix"] for k, r in ai.items() if r.get("verdict") == "vẽ lại" and r.get("fix")}
    changed = False
    for key, note in notes.items():
        text = (note.get("text") or "").strip()
        if not text:
            continue
        english = note.get("english") if note.get("source") == text else None
        if not english:
            english = translate(text)
            if english:                           # chỉ lưu khi dịch được; lỗi thì lần sau dịch lại
                note.update(english=english, source=text)
                changed = True
        fixes[key] = ", ".join(x for x in (fixes.get(key), english or text) if x)
    if changed:
        notes_file.write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")
    return fixes


def translate(text):
    """Ghi chú tiếng Việt -> cụm tiếng Anh cho prompt vẽ (model vẽ chỉ hiểu tiếng Anh). Lỗi hay không có khóa thì giữ nguyên."""
    if all(ord(c) < 128 for c in text):
        return text
    try:
        from llm import chat
        import os
        model = os.environ.get("AI_MODEL_REVIEW") or os.environ.get("AI_MODEL_SCRIPT") or "claude-sonnet-5-5"
        reply = chat("Translate this image-correction note into a short English phrase for an image generation prompt. "
                     "Describe what the image must show, not what is wrong. Reply with the phrase only.\n\n" + text,
                     model, max_tokens=300)
        return reply.strip().strip('"').splitlines()[0][:300]
    except Exception as e:                         # noqa: BLE001  (không có khóa, mạng lỗi: vẫn vẽ lại bằng nguyên văn)
        print(f"  không dịch được ghi chú ({e}), dùng nguyên văn")
        return None


GREENISH = ("green", "mint", "olive", "emerald", "lime", "jade", "sage", "chartreuse", "matcha", "leaf",
             "leaves", "plant", "grass", "frog", "cucumber", "broccoli", "lettuce", "cactus", "moss", "teal", "turquoise")
BLUEISH = ("blue", "navy", "cobalt", "azure", "indigo", "denim", "jeans", "sky", "cyan", "teal", "turquoise", "sapphire")
KEY_PROMPTS = {"green": "on a solid flat pure green background (#00FF00), no shadow",
               "blue": "on a solid flat pure blue background (#0000FF), no shadow",
               "magenta": "on a solid flat pure magenta background (#FF00FF), no shadow"}


def key_for(*texts):
    """Màu nền để tách (04_cutouts.py tự nhận màu nền ở viền ảnh): xanh lá như cũ; đồ vật / quần áo có màu xanh lá thì
    xanh dương (xanh lá sẽ bị khoét khi tách); có cả xanh lá lẫn xanh dương thì hồng tím."""
    text = " ".join(t or "" for t in texts).lower()
    green = any(w in text for w in GREENISH)
    blue = any(w in text for w in BLUEISH)
    if green and blue:
        return KEY_PROMPTS["magenta"]
    return KEY_PROMPTS["blue"] if green else KEY_PROMPTS["green"]


def alt_pose(scene, name):
    """alt_pose của cảnh: một chuỗi (áp cho mọi chủ thể trong cảnh) hoặc {nhân vật: mô tả}."""
    value = scene.get("alt_pose")
    return value.get(name) if isinstance(value, dict) else value


if __name__ == "__main__":
    main()
