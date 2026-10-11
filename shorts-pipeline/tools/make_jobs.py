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
  clip_<cảnh>        (mục "clips") clip image-to-video từ tranh cả cảnh, cho cảnh "motion_level": "low"
                     (cần "full"; chuyển động lấy từ "i2v_prompt", không có thì "action")  -> clips/<cảnh>.mp4
Ảnh nào đã có thì không tạo job. Ảnh nền và ảnh chuẩn dùng chung cho mọi video.
Muốn sinh lại một ảnh: xóa file ảnh đó rồi chạy lại lệnh này.
"""
import re
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "steps"))
from common import TRIGGER, character_files   # noqa: E402

# Cách dựng mới (style "new", như kênh スカッと迷言集): mỗi cảnh một tranh vẽ cả cảnh có 1-2 người ở cự ly gần, ảnh chuẩn
# từng người làm tham chiếu để giữ mặt; 576x1024 để vừa T4 với 2 tham chiếu (768x1344 + nhiều tham chiếu từng hết VRAM)
FULL = ("{trigger}, {who} in {place}. {action}. {emotion} expression. {framing}. The people look exactly like in the "
        "reference images (same face, hair, clothes, colors), large and close to the camera, their faces in the middle "
        "of the image and NOT in the top quarter (leave the top quarter as background for captions), "
        "exactly {count} people, no one else, cute flat colors, no text, no speech bubbles")
FULL_FRAMING = {"close": "close-up of the face and shoulders", "half": "medium shot from the waist up",
                "full": "full body in the scene"}
# Nhân vật "art": "anime" (characters.json): vẽ không qua LoRA Irasutoya, lời vẽ kiểu anime (như cô mẹ video mẫu 5)
ANIME = "cute anime style illustration, big sparkling eyes, glossy detailed hair, soft cel shading, beautiful"
ANIME_CAST = ANIME + ", {look}, standing straight facing forward, arms down, gentle smile, full body, white background"
MASCOT_CAST = ("{trigger}, turn the map shape in the reference image into the HEAD of a cute mascot character: keep exactly "
               "the same map outline and the same flag colors and pattern on it, draw a simple cute face on the map head "
               "(two black dot eyes, pink blush, small smile), add a small body with short arms and legs below it, {look}, "
               "standing, one hand waving, full body, plain white background")
ANIME_LORA = 0.0         # ảnh chỉ có nhân vật anime
MIXED_LORA = 0.55        # tranh cả cảnh có cả nhân vật anime và Irasutoya: giảm LoRA để hai nét cùng tồn tại


def is_anime(characters, name):
    owner = characters.get(name, {}).get("ref", name)
    return characters.get(owner, {}).get("art") == "anime" or characters.get(name, {}).get("art") == "anime"


# Biểu cảm cường điệu kiểu manga (như video mẫu: mặt nhân vật co méo rõ cảm xúc) + góc mặt; khớp từ khóa trong "emotion"
EXPRESSIVE = (
    (("smug", "mock", "sneer", "teas", "cocky", "condescend"),
     "smug grin with one corner of the mouth raised, half-closed eyes, one eyebrow raised, looking down mockingly"),
    (("angry", "furious", "rage", "irritat", "annoy"),
     "furious face, furrowed brows, gritted teeth, flushed red cheeks, vein mark on the forehead"),
    (("shock", "surpris", "stunn", "horrif"), "jaw dropped, eyes wide open with tiny pupils, pale face, sweat drops"),
    (("scared", "fear", "terrif", "afraid"), "trembling, eyes wide with fear, pale blue face, mouth wavering"),
    (("sad", "cry", "tear", "heartbroken"), "crying with tears streaming, eyebrows slanted up, trembling mouth"),
    (("happy", "joy", "delight", "excit"), "beaming wide open-mouth smile, eyes squeezed shut in joy, rosy cheeks"),
    (("embarrass", "shy", "blush", "flustered"), "deep red blush, eyes looking away, awkward wavy smile, sweat drop"),
    (("cold", "contempt", "disgust", "disdain"), "cold disdainful stare, narrowed eyes, mouth flat, chin raised"),
    (("creepy", "sinister", "eerie", "menac"), "unsettling calm smile, eyes shadowed and half-lidded, dark shadow over the upper face"),
    (("confus", "puzzl", "doubt", "suspic"), "one eyebrow raised high, squinting suspiciously, mouth twisted to one side"),
    (("despair", "hopeless", "devastat"), "blank hollow eyes, vertical gloom lines on the forehead, mouth hanging open"),
)
ANGLES = ("head tilted to one side", "three-quarter view, face turned slightly", "leaning toward the viewer",
          "head tilted back slightly, looking down", "face straight to the viewer")


def expressive(emotion, scene_id, shot="full"):
    """Biểu cảm rõ, cường điệu theo từ khóa của "emotion"; cảnh cận / nửa người thêm góc mặt đổi luân phiên theo cảnh."""
    text = str(emotion or "natural")
    low = text.lower()
    extra = next((desc for words, desc in EXPRESSIVE if any(w in low for w in words)), "")
    out = f"{text}, exaggerated manga-style expression, {extra}" if extra else f"{text}, clearly readable expression"
    if shot in ("close", "half") and not any(w in low for w in ("tilt", "three-quarter", "lean", "profile")):
        out += f", {ANGLES[scene_id % len(ANGLES)]}"
    return out


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

    def ref_job(owner):
        """Ảnh chuẩn: nhân vật anime vẽ kiểu anime, không LoRA Irasutoya. Linh vật quốc gia ("head_ref", tools/country_mascot.py):
        sửa từ ảnh đầu bản đồ + cờ vẽ bằng code, để hình nước và cờ đúng."""
        head = characters[owner].get("head_ref")
        if head:
            return {"name": f"ref_{owner}", "refs": [f"ref__{head}"],
                    "prompt": MASCOT_CAST.format(trigger=TRIGGER, look=characters[owner]["prompt"])}
        if is_anime(characters, owner):
            return {"name": f"ref_{owner}", "lora": ANIME_LORA,
                    "prompt": ANIME_CAST.format(look=characters[owner]["prompt"])}
        return {"name": f"ref_{owner}", "prompt": CAST.format(trigger=TRIGGER, look=characters[owner]["prompt"])}

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
        full = video / "full" / f"{scene['id']:03d}.png"
        if scene.get("full") and not full.exists():           # cách dựng mới: một tranh cả cảnh, tối đa 2 người
            names = [n for n in scene.get("characters", []) if n in characters][:2]
            refs_full = []
            for n in names:
                owner = characters[n].get("ref", n)
                ref = refs / f"{owner}_front.png"
                if not ref.exists() and owner not in cast:
                    cast[owner] = ref_job(owner)
                refs_full.append(f"ref__{ref.name}" if ref.exists() else f"@ref_{owner}")
            who = " and ".join(f"the person from image {k + 1} ({characters[n]['prompt'][:80]})" for k, n in enumerate(names)) \
                or (scene.get("object") or "a scene")
            place = locations.get(scene["location"], scene["location"])
            place = place.split(", flat colors")[0].replace(f"{TRIGGER}, background illustration of ", "")
            seed = scene["id"] * 10 + 1000 * len(list((video / "rejected").glob(f"full_{scene['id']:03d}*.png")))
            job = {"name": f"full_{scene['id']:03d}", "seed": seed, "width": 576, "height": 1024,
                   "fix": fixes.get(f"full/{full.name}", ""),
                   "prompt": fixed(FULL.format(trigger=TRIGGER, who=who, place=place[:220], action=scene.get("action") or "",
                                               emotion=expressive(scene.get("emotion"), scene["id"], scene.get("shot", "half")),
                                               framing=FULL_FRAMING.get(scene.get("shot", "half"), FULL_FRAMING["half"]),
                                               count=len(names) or "no"), f"full/{full.name}")}
            if refs_full:
                job["refs"] = refs_full
            anime = [k for k, n in enumerate(names) if is_anime(characters, n)]
            if anime:                                          # có nhân vật anime: giữ nét anime của người đó
                others = len(names) - len(anime)
                note = "; ".join(f"the person from image {k + 1} is drawn in {ANIME}" for k in anime)
                if others:
                    note += "; the other person is drawn in simple flat irasutoya style"
                job["prompt"] = f"{job['prompt']}. {note}"
                job["lora"] = MIXED_LORA if others else ANIME_LORA
                if not others:                                 # chỉ nhân vật anime: bỏ từ kích hoạt Irasutoya, bỏ "flat colors"
                    job["prompt"] = job["prompt"].replace(f"{TRIGGER}, ", f"{ANIME}, ", 1).replace("cute flat colors", "anime colors")
            # Kaggle chạy theo LoRA giảm dần: tranh cần ảnh chuẩn "@ref" (vẽ cùng lô) có LoRA thấp hơn sẽ chờ mãi
            # (run_kaggle.py từ chối lô, video 031). Hoãn tranh đó sang lượt sau, khi ảnh chuẩn đã là file có sẵn.
            mine = 1.0 if job.get("lora", True) is True else float(job["lora"])
            waits = [r for r in job.get("refs", []) if r.startswith("@ref_") and
                     (ANIME_LORA if is_anime(characters, r.removeprefix("@ref_")) else 1.0) < mine]
            if waits:
                print(f"  hoãn full_{scene['id']:03d} sang lượt sau: chờ ảnh chuẩn {', '.join(waits)}")
                continue
            scenes.append(job)
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
                    cast[owner] = ref_job(owner)
                anime_job = {"lora": ANIME_LORA} if is_anime(characters, name) else {}
                scenes.append({"name": f"ch_{stem}", "seed": seed, "fix": fixes.get(f"characters/{filename}", ""), **anime_job,
                               "refs": [f"ref__{ref.name}" if ref.exists() else f"@ref_{owner}"],
                               "prompt": fixed(SCENE.format(trigger=ANIME if is_anime(characters, name) else TRIGGER, look=look, action=per_character(scene, "action", name),
                                                            emotion=expressive(per_character(scene, "emotion", name),
                                                                               scene["id"], scene.get("shot", "full")),
                                                            framing=shots[scene.get("shot", "full")]["prompt"],
                                                            background=key_for(look, per_character(scene, "action", name))),
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
            # nhân vật anime: tư thế thứ hai cũng không LoRA, cùng cường độ với ảnh gốc (run_kaggle.py bắt buộc)
            anime = is_anime(characters, name) if name else False
            alts.append({"name": f"ch_{stem}_alt", "seed": seed + 500, "refs": [base],
                         "fix": fixes.get(f"characters/{stem}_alt.png", ""), **({"lora": ANIME_LORA} if anime else {}),
                         "prompt": fixed(ALT.format(trigger=ANIME if anime else TRIGGER, pose=pose),
                                         f"characters/{stem}_alt.png")})

    # mỗi job đứng sau job nó tham chiếu: ảnh chuẩn -> ảnh cảnh -> tư thế thứ hai (quy tắc của run_kaggle.py)
    jobs = list(cast.values()) + scenes + alts + backgrounds
    clips = clip_jobs(video, script, {j["name"] for j in jobs}, settings["i2v"])
    (video / "jobs.json").write_text(json.dumps({"jobs": jobs, "clips": clips}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    print(f"{video.name}/jobs.json: {len(jobs)} job ({len(cast)} ảnh chuẩn, {len(scenes)} ảnh cảnh, "
          f"{len(alts)} tư thế thứ hai, {len(backgrounds)} nền), {len(clips)} clip")


def clip_jobs(video, script, new_names, i2v):
    """Clip image-to-video (kaggle_job/i2v_runner.py) cho cảnh "motion_level": "low" chưa có clips/<cảnh>.mp4.
    Ảnh đầu vào là tranh cả cảnh: sinh cùng lần chạy ("@full_NNN") hoặc đã có ở full/ ("full__NNN.png").
    Độ dài theo giọng đọc nếu đã có audio/NNN.wav, không thì [i2v] seconds; số frame dạng 4k+1."""
    clips = []
    for scene in script["scenes"]:
        level, sid = scene.get("motion_level"), f"{scene['id']:03d}"
        if level == "high":
            print(f"  cảnh {sid}: motion_level high (gửi API) chưa làm, dựng như ảnh tĩnh")
        if level != "low" or (video / "clips" / f"{sid}.mp4").exists():
            continue
        if f"full_{sid}" in new_names:
            image = f"@full_{sid}"
        elif scene.get("full") and (video / "full" / f"{sid}.png").exists():
            image = f"full__{sid}.png"
        else:
            print(f"  bỏ qua clip cảnh {sid}: cần \"full\" (tranh cả cảnh) làm ảnh đầu")
            continue
        seconds = i2v["seconds"]
        wav = video / "audio" / f"{sid}.wav"
        if wav.exists():
            import wave
            with wave.open(str(wav)) as w:
                seconds = w.getnframes() / w.getframerate()
        frames = min(round(seconds * i2v["fps"] / 4) * 4 + 1, i2v["max_frames"])
        prompt = scene.get("i2v_prompt") or scene.get("action") or "the people move slightly and naturally"
        clips.append({"name": f"clip_{sid}", "image": image, "prompt": prompt, "frames": frames,
                      "seed": scene["id"] * 10})
    return clips


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


def per_character(scene, key, name):
    """"action" / "emotion" của cảnh cho một nhân vật: chuỗi (áp cho mọi nhân vật) hoặc {nhân vật: mô tả} (cảnh nhiều
    nhân vật, video 026); thiếu nhân vật đó thì ghép mô tả của cả cảnh."""
    value = scene.get(key) or ""
    if isinstance(value, dict):
        value = value.get(name) or "; ".join(f"{k}: {v}" for k, v in value.items())
    value = str(value)
    if key == "action" and len(scene.get("characters") or []) >= 2:
        value = alone(value, scene.get("characters") or [])
    return value


PEOPLE = ("man", "woman", "boy", "girl", "son", "daughter", "mother", "father", "mom", "dad", "parent", "child", "kid",
          "waiter", "waitress", "clerk", "friend", "teacher", "student", "husband", "wife", "boss", "colleague", "coworker",
          "grandma", "grandpa", "grandmother", "grandfather", "customer", "brother", "sister", "boyfriend", "girlfriend",
          "person", "people", "other", "partner", "baby", "doctor", "nurse", "him", "her", "them")
PHRASE = re.compile(r"\s*\b(?:toward|towards|to|at|beside|next to|with)\s+(?:the\s+|his\s+|her\s+|their\s+|a\s+|an\s+)?"
                    r"([a-z][a-z' _-]*?)(?=[,;.]|$)", re.I)


def alone(action, names=()):
    """Cảnh nhiều nhân vật: mỗi người vẽ thành một ảnh riêng rồi mới ghép. Câu "facing right toward the waiter",
    "handing a box to the girl" làm model vẽ luôn người kia vào ảnh, ghép lại thành hai người giống nhau (video 024).
    Chỉ bỏ cụm nhắc tới NGƯỜI (giữ "looking at the clock"), giữ hướng nhìn và động tác, rồi dặn chỉ vẽ một người."""
    words = set(PEOPLE) | {n.lower() for n in names} | {p for n in names for p in n.lower().split("_")}

    def drop(m):
        head = re.findall(r"[a-z]+", m.group(1).lower())[:2]       # danh từ chính ngay sau giới từ ("clock on her wrist": clock)
        return "" if any(w in words for w in head) else m.group(0)

    cleaned = PHRASE.sub(drop, action).strip(" ,;")
    return f"{cleaned}, alone, the only person in the image, nobody else"


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
