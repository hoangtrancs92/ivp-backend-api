"""Tiểu phẩm, bước 3: danh sách ảnh cần vẽ trên Kaggle (jobs.json trong thư mục tiểu phẩm, chạy bằng tools/run_kaggle.py).

  python skit/jobs.py skits/<tên>

Kiểu "rối giấy" như video mẫu: mỗi nhân vật 1 ảnh gốc (tư thế chung) + mỗi biểu cảm 1 ảnh vẽ TỪ ảnh gốc đó (cùng tư thế,
chỉ đổi mặt, để đổi biểu cảm không làm nhân vật nhảy) + 0-2 tư thế khác ("poses": cầm điện thoại, giơ nắm đấm...) + với mỗi ảnh
trên một bản MIỆNG MỞ (_talk) để mấp máy khi nói. Nền từng nơi, tranh chèn. Ảnh đã có thì bỏ qua.
  ref_<nhân vật>                 ảnh chuẩn (nếu config/refs/ chưa có)   -> config/refs/<nhân vật>_front.png
  ch_<nhân vật>_<cảm xúc>[_talk] ảnh biểu cảm (miệng mở)                -> skits/<tên>/characters/<nhân vật>_<cảm xúc>[_talk].png
  ch_<nhân vật>_pose_<tư thế>[_talk] ảnh tư thế khác (miệng mở)         -> skits/<tên>/characters/...
  bg_skit_<tên>_<nơi>     ảnh nền từng nơi (sets)                       -> library/backgrounds/skit_<tên>_<nơi>.png
  bg_skit_<tên>_insNN     tranh chèn minh họa (insert), có người vẽ sẵn -> library/backgrounds/skit_<tên>_insNN.png
"""
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "tools")]
from common import TRIGGER                     # noqa: E402
from make_jobs import KEY_PROMPTS, key_for     # noqa: E402  (chỉ dùng lại, không sửa)

BG = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))["background"]
REFS = ROOT / "config" / "refs"
FACE = {"normal": "calm neutral", "happy": "big happy smiling", "shocked": "shocked, wide-eyed, mouth open",
        "angry": "angry, furrowed brows, shouting", "sad": "sad, teary", "panic": "panicked, sweating, mouth wide open",
        "smug": "smug, confident grin", "crying": "crying with tears streaming",
        "embarrassed": "embarrassed, blushing, awkward smile", "thinking": "thinking, puzzled, eyes looking up",
        "disgusted": "disgusted, grimacing", "sleepy": "sleepy, half-closed eyes, yawning"}
CAST = "{trigger}, {look}, standing straight facing forward, arms down, calm neutral face, full body, white background"
BASE = ("{trigger}, the same person as in the reference image, wearing exactly the same clothes, colors and accessories as in "
        "the reference image, {look}, {pose}, {face} face, {framing}, facing the viewer, alone, the only person in the image, "
        "only the character and small items held in the hands, no desk, no table, no chair, no sofa, no bed, no keyboard, "
        "no computer, no monitor, no furniture, no floor, no props on the ground, no other people, {background}")
# Người ngồi: bàn ghế của họ vẽ liền trong ảnh (không có thì ngồi lơ lửng), ngoài ra không có gì khác
SEATED_BASE = ("{trigger}, the same person as in the reference image, wearing exactly the same clothes, colors and accessories "
               "as in the reference image, {look}, {pose}, {face} face, {framing}, facing the viewer, alone, the only person in "
               "the image, only the person and the chair / desk they use, no floor, no wall, no other furniture, no other "
               "people, {background}")
# Đồ đạc / nơi chốn trong tư thế (vd "sitting at desk", "feet up against desk edge"): thuộc ảnh nền, bỏ khỏi lời vẽ nhân vật
# (skit-008: Kaggle vẽ bàn, ghế, bàn phím vào ảnh nhân vật trong khi nền đã có bàn). Chỗ ngồi / đứng ghi ở "place".
FURNITURE = re.compile(
    r"\s*\b(?:at|on|in|into|around|behind|under|below|beneath|against|beside|by|next to|in front of|over|across|onto|from)\s+"
    r"(?:the\s+|a\s+|an\s+|his\s+|her\s+|their\s+)?(?:[\w-]+\s+){0,2}?"
    r"(?:desk|table|chair|seat|sofa|couch|bench|bed|counter|keyboard|monitor|computer|laptop|floor|ground|door|"
    r"doorway|door frame|window|wall|car|bus|train|stool|shelf|cabinet|kotatsu)(?:\s+(?:edge|top|surface|frame))?\b",
    re.I)
SEATED = re.compile(r"\b(seat|seated|sitting|sits|kneel|kneeling|slouch|slouched|leaning back)\b", re.I)


def seated_pose(pose, base):
    """Tư thế phụ của người đang ngồi (vd "leaning forward squinting") vẫn là ngồi, trừ khi nói rõ đứng dậy / đi."""
    standing = re.search(r"\b(stand|walk|run|jump|rise|get up)", str(pose), re.I)
    if SEATED.search(str(base)) and not standing:
        if not SEATED.search(str(pose)):
            pose = f"sitting, {pose}"
        # mang theo bàn ghế của tư thế chính ("at desk", "in chair"): đổi tư thế không làm mất bàn ghế (skit-008: ảnh tư thế gõ
        # phím chỉ còn bàn phím lơ lửng, người ngồi giữa không trung)
        low = str(base).lower()
        seat = ("on an office chair at a desk" if "desk" in low else "at a table" if "table" in low
                else "on a sofa" if re.search(r"sofa|couch", low) else "on a chair" if re.search(r"chair|stool", low) else "")
        if seat and not re.search(r"\b(desk|table|chair|stool|sofa|couch|bench)\b", str(pose), re.I):
            pose = f"{pose}, {seat}"
    return pose


def furniture_pose(pose):
    """Người ngồi: bàn ghế vẽ LIỀN trong ảnh nhân vật (như video mẫu), cả người, nên giữ nguyên câu tư thế (có bàn ghế)."""
    return bool(SEATED.search(str(pose)))


def body_pose(pose):
    """Tư thế chỉ còn cơ thể và đồ cầm tay: bỏ cụm nơi chốn / đồ đạc; ngồi thì thêm 'sitting posture' (không vẽ ghế)."""
    text = FURNITURE.sub("", str(pose))
    text = re.sub(r"\b(?:hands\s+)?typing\b|\bkeyboard\b", "hands moving as if typing", text, flags=re.I)
    text = re.sub(r"\s*,\s*(?:,\s*)+", ", ", text).strip(" ,")
    if SEATED.search(pose):
        text += ", sitting posture with nothing under the person"
    return text or "standing"
TALK = ("{trigger}, exactly the same image as the reference image: the same person, same clothes, same pose, same size and "
        "position, same face; only the mouth is now open as if talking, {background}")
EXPR = ("{trigger}, exactly the same image as the reference image: the same person, same clothes, same pose, same size and "
        "position, same framing; only the facial expression changes to a {face} face, {background}")


def framing(pose):
    """Luôn cả người; người ngồi vẽ cả ghế / bàn của họ trong ảnh (nửa người trôi nổi trông kỳ, skit-008)."""
    return ("full body from head to feet including the chair or furniture they sit on" if SEATED.search(str(pose))
            else "full body from head to feet")


META = re.compile(r"(9:16|vertical|composition|subtitle|caption|bgm|music|narration|seconds|delivery|animation|"
                  r"irasutoya|style|proportions|consistent|expressive|cheerful light|cute rounded|3d)", re.I)


def place_prompt(place):
    """Chỉ phần tả nơi chốn: bỏ câu lời dặn kỹ thuật (khung 9:16, phụ đề, nhạc, phong cách...) mà model vẽ ảnh sẽ vẽ thành chữ /
    khung tranh (skit-007), bỏ chữ trong ngoặc 「」, tối đa ~300 ký tự."""
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", str(place)) if x.strip()]
    keep = [x for x in sentences if not META.search(x)] or sentences[:1]
    text = re.sub(r"「[^」]*」|\"[^\"]*\"", "", " ".join(keep))
    text = re.sub(r",?\s*(with )?(a )?(small )?(removable )?(tag|sign|label)?\s*(reading|labeled|that says)\s*(?=[.,]|$)", "", text)
    return text[:300].rsplit(" ", 1)[0] if len(text) > 300 else text


MAKE_SCENES = False      # toàn cảnh Kaggle vẽ cả người (thử ở skit-008: thừa người, người nhỏ): tắt; nhân vật đứng ghép lên
                        # sàn trống của nền là đủ tự nhiên. Bật lại: True
MAX_SCENES = 8
SCENE_W, SCENE_H = 512, 912        # toàn cảnh có 2 tham chiếu: nhỏ để vừa T4 (768x1344 + 5 tham chiếu từng hết VRAM), dựng phóng lên
SCENE = ("{trigger}, the same room as in image 1 (same furniture, same layout, same camera angle and colors), now with these "
         "people in it, who are shown in image 2 from left to right: {people}. Each person looks exactly like in image 2 "
         "(same face, hair, clothes, colors). "
         "Exactly {count} people in the image, no one else, no extra people in the background. The people are large and fill "
         "most of the frame, placed close to the camera in the foreground and middle of the room, interacting naturally with "
         "the furniture of the room, flat colors, no text, no speech bubbles")


def cast_sheet(names, refs, out):
    """Bảng nhân vật: ảnh chuẩn từng vai cắt sát người, xếp cạnh nhau từ trái sang phải trên nền trắng (một tham chiếu thay
    cho nhiều tham chiếu, để vừa bộ nhớ GPU). Trả về đường dẫn ảnh."""
    from PIL import Image, ImageChops
    people = []
    for n in names:
        img = Image.open(refs[n]).convert("RGB")
        diff = ImageChops.difference(img, Image.new("RGB", img.size, img.getpixel((2, 2))))
        box = diff.convert("L").point(lambda v: 255 if v > 24 else 0).getbbox() or (0, 0, img.width, img.height)
        person = img.crop(box)
        people.append(person.resize((round(person.width * 900 / person.height), 900), Image.LANCZOS))
    gap = 40
    sheet = Image.new("RGB", (sum(p.width for p in people) + gap * (len(people) + 1), 980), (255, 255, 255))
    x = gap
    for p in people:
        sheet.paste(p, (x, 40))
        x += p.width + gap
    sheet.save(out)
    return out


def wide_states(skit):
    """Các "toàn cảnh" cần vẽ: mỗi trạng thái sân khấu khác nhau ở câu góc rộng (nơi, ai có mặt, tư thế từng người) là một
    ảnh có người vẽ sẵn trong bối cảnh. Trả về ({khóa: trạng thái}, [khóa của từng câu hoặc None])."""
    cast = skit["cast"]
    sets = list(skit.get("sets") or {"main": ""})
    home = {n: cast[n].get("set") if cast[n].get("set") in sets else sets[0] for n in cast}
    entering = {l.get("enter") for l in skit["lines"] if l.get("enter") in cast}
    present, poses, keys, states, count = {n for n in cast if n not in entering}, {}, [], {}, {}
    for line in skit["lines"]:
        if line.get("enter") in cast:
            present.add(line["enter"])
        for n, q in (line.get("pose") or {}).items():
            poses.pop(n, None) if q == "default" else poses.__setitem__(n, q)
        shot = line.get("shot") or "wide"
        if ":" in shot or line.get("insert") or not present:
            keys.append(None)
        else:
            where = home.get(line["speaker"], sets[0])
            people = tuple(sorted(n for n in present if home[n] == where))
            key = (where, people, tuple((n, poses.get(n, "")) for n in people))
            states.setdefault(key, {"set": where, "people": list(people), "poses": {n: poses.get(n, "") for n in people}})
            count[key] = count.get(key, 0) + 1
            keys.append(key)
        if line.get("exit") in cast:
            present.discard(line["exit"])
    keep = sorted(states, key=lambda k: -count[k])[:MAX_SCENES]       # quá nhiều: giữ trạng thái hay dùng nhất
    for i, key in enumerate(keys):                                     # câu thuộc trạng thái bị bỏ: lấy trạng thái gần nhất
        if key is not None and key not in keep:
            keys[i] = next((k for k in keep if k[0] == key[0] and set(k[1]) == set(key[1])),
                           next((k for k in keep if k[0] == key[0]), None))
    return {k: states[k] for k in keep}, keys


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]


def main():
    folder = Path(sys.argv[1]).resolve()
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    have = lambda *paths: any(p.exists() for p in paths)   # noqa: E731
    jobs, refs = [], []
    tiers = []                                              # (bậc, job): ảnh làm tham chiếu phải đứng trước ảnh dùng nó
    exists = lambda stem: have(folder / "characters" / f"{stem}.png", folder / "cutouts" / f"{stem}.png")   # noqa: E731
    source = lambda stem: f"char__{stem}.png" if exists(stem) else f"@ch_{stem}"                         # noqa: E731
    tag = slug(folder.name.removeprefix("skit-"))
    ref_of = {}                                             # vai -> tham chiếu ảnh chuẩn (dùng lại cho ảnh toàn cảnh)       # ảnh chuẩn riêng từng tiểu phẩm (vai sk_* trùng tên giữa các tiểu phẩm)
    for name, c in skit["cast"].items():
        ref = REFS / f"{tag}_{name}_front.png"
        if not ref.exists() and (REFS / f"{name}_front.png").exists() and (folder / "characters" / f"{name}_normal.png").exists():
            ref = REFS / f"{name}_front.png"                # tiểu phẩm cũ đã vẽ bằng ảnh chuẩn tên chung
        if not ref.exists():
            refs.append({"name": f"ref_{tag}_{name}", "prompt": CAST.format(trigger=TRIGGER, look=c["look"])})
        ref_src = f"ref__{ref.name}" if ref.exists() else f"@ref_{tag}_{name}"
        ref_of[name] = ref_src
        seed = sum(map(ord, name)) % 10000
        stems = []                                          # các ảnh (trừ bản miệng mở) của nhân vật này
        for stem, pose in [(f"{name}_normal", c["pose"])] + [(f"{name}_pose_{k}", seated_pose(v, c["pose"]))
                                                             for k, v in (c.get("poses") or {}).items()]:
            stems.append(stem)
            if not exists(stem):
                tiers.append((1, {"name": f"ch_{stem}", "seed": seed, "refs": [ref_src],
                                  "prompt": (SEATED_BASE if furniture_pose(pose) else BASE).format(
                                      trigger=TRIGGER, look=c["look"], pose=pose if furniture_pose(pose) else body_pose(pose),
                                      face=FACE["normal"],
                                                        framing=framing(pose), background=key_for(c["look"], pose))}))
        background = key_for(c["look"], c["pose"])
        for expr in c["expressions"]:
            stem = f"{name}_{expr}"
            if expr == "normal":
                continue
            stems.append(stem)
            if not exists(stem):
                tiers.append((2, {"name": f"ch_{stem}", "seed": seed, "refs": [source(f"{name}_normal")],
                                  "prompt": EXPR.format(trigger=TRIGGER, face=FACE[expr], background=background)}))
        for stem in stems:                                  # bản miệng mở của từng ảnh: mấp máy khi nói
            if not exists(f"{stem}_talk"):
                tiers.append((3, {"name": f"ch_{stem}_talk", "seed": seed, "refs": [source(stem)],
                                  "prompt": TALK.format(trigger=TRIGGER, background=background)}))
    jobs = [j for _, j in sorted(tiers, key=lambda t: t[0])]
    library = ROOT / "library" / "backgrounds"
    sets = skit.get("sets") or {"main": skit["location"]}
    skit["backgrounds"] = {}
    for key, place in sets.items():
        bg_name = f"skit_{slug(folder.name.removeprefix("skit-"))}_{key}"
        skit["backgrounds"][key] = bg_name
        if not (library / f"{bg_name}.png").exists():
            jobs.append({"name": f"bg_{bg_name}", "lora": BG["lora"], "width": BG["width"], "height": BG["height"], "fix": "",
                         "prompt": f"{TRIGGER}, background illustration of {place_prompt(place)}, vertical portrait composition at "
                                   f"eye level, a wide open empty floor area in the foreground and middle where people can stand, "
                                   f"furniture only along the back wall and the sides, no desk, table or chair in the middle of "
                                   f"the floor, the room fills the frame from top to bottom, full-bleed scene edge to edge, "
                                   f"flat colors, simple shapes, "
                                   f"no people, no text"})
    skit["background"] = skit["backgrounds"][next(iter(sets))]
    skit["inserts"] = {}
    for line in skit["lines"]:
        text = line.get("insert")
        if not text or text in skit["inserts"]:
            continue
        ins = f"skit_{slug(folder.name.removeprefix("skit-"))}_ins{len(skit['inserts']) + 1:02d}"
        skit["inserts"][text] = ins
        if not (library / f"{ins}.png").exists():
            jobs.append({"name": f"bg_{ins}", "width": BG["width"], "height": BG["height"], "fix": "",
                         "seed": len(skit["inserts"]) * 101,
                         "prompt": f"{TRIGGER}, {text}, full illustration with a detailed background, flat colors, "
                                   f"simple cute characters, no text, no speech bubbles"})
    # toàn cảnh có người vẽ sẵn trong bối cảnh (nền nơi đó làm tham chiếu 1, ảnh chuẩn từng vai 2, 3...): người ngồi đúng
    # ghế, sau bàn, đúng phối cảnh; câu góc rộng dùng ảnh này, cận / nhóm vẫn dùng ảnh cắt rời (đổi mặt, mấp máy miệng)
    states, keys = wide_states(skit) if MAKE_SCENES else ({}, [None] * len(skit["lines"]))
    skit["scenes"] = {}
    for i, (key, st) in enumerate(states.items(), start=1):
        name = f"skit_{tag}_scene{i:02d}"
        bg = skit["backgrounds"][st["set"]]
        cast = skit["cast"]
        people = "; ".join(f"person {k + 1} ({cast[n]['look'][:90]}), "
                           f"{seated_pose(cast[n]['poses'].get(st['poses'][n], cast[n]['pose']), cast[n]['pose'])}"   # nguyên văn: có bàn ghế
                           f"{', ' + cast[n]['place'] if cast[n].get('place') else ''}"
                           for k, n in enumerate(st["people"]))
        skit["scenes"][name] = {**st, "image": name}
        ready = {n: REFS / ref_of[n].removeprefix("ref__") for n in st["people"] if ref_of[n].startswith("ref__")}
        if not (library / f"{name}.png").exists() and len(ready) == len(st["people"]):   # ảnh chuẩn chưa có: lượt sau
            refs_bg = f"bg__{bg}.png" if (library / f"{bg}.png").exists() else f"@bg_{bg}"
            sheet = cast_sheet(st["people"], ready, REFS / f"{name}_sheet.png")
            jobs.append({"name": f"bg_{name}", "width": SCENE_W, "height": SCENE_H, "fix": "", "seed": 300 + i,
                         "refs": [refs_bg, f"ref__{sheet.name}"],
                         "prompt": SCENE.format(trigger=TRIGGER, people=people, count=len(st["people"]))})
    names = {key: f"skit_{tag}_scene{i:02d}" for i, key in enumerate(states, start=1)}
    for line, key in zip(skit["lines"], keys):
        line["scene"] = names.get(key) if key else None
    (folder / "skit.json").write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    # thứ tự: ảnh chuẩn -> ảnh gốc, tư thế -> biểu cảm -> miệng mở (tham chiếu phải đứng trước, quy tắc của run_kaggle.py)
    jobs = refs + jobs
    (folder / "jobs.json").write_text(json.dumps({"jobs": jobs}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{folder.name}/jobs.json: {len(jobs)} ảnh ({len(refs)} ảnh chuẩn, "
          f"{sum(j['name'].startswith('ch_') for j in jobs)} ảnh nhân vật, {sum(j['name'].startswith('bg_') for j in jobs)} nền / tranh chèn)")


if __name__ == "__main__":
    main()
