"""Tự đa dạng chuyển động khi kịch bản bỏ trống, để video không lặp một kiểu (dùng trong build_video.py).

Điền vào chỗ trống, không đổi giá trị kịch bản đã ghi:
  anim của lớp nhân vật chính   theo cảm xúc ("emotion"), khác 2 cảnh trước
  motion của cảnh               theo nhịp truyện ("beat"), khác 2 cảnh trước
  transition (chuyển cảnh)      theo thay đổi bối cảnh, hồi tưởng, nhịp
  at của nhân vật nửa người     luân phiên giữa, hơi trái, hơi phải
Kết quả cố định theo kịch bản (không ngẫu nhiên), nên dựng lại ra y hệt.
"""
import re
from pathlib import Path

# cảm xúc (từ khóa trong "emotion") -> các kiểu anim hợp
EMOTION_ANIMS = [
    (("cry", "tear", "sob", "heartbroken"), ["sink", "breathe", "shiver", "float"]),
    (("scared", "afraid", "fear", "terrified", "panic", "horror"), ["shiver", "recede", "shake_no", "sink"]),
    (("relieved", "relief", "calm", "peaceful", "nostalgic", "dreamy", "sleepy", "tired"), ["breathe", "float", "sway", "sink"]),
    (("excited", "giggl", "mischiev", "playful", "proud", "triumph", "cheer"), ["hop", "jump", "bounce", "spin_in"]),
    (("shy", "blush", "love", "in love", "touched", "grateful"), ["sway", "tilt", "float", "nod"]),
    (("jealous", "annoyed", "irritated", "sulk", "pout", "disgust"), ["shake_no", "tilt", "punch", "sway"]),
    (("regret", "disappoint", "defeated", "exhausted", "despair"), ["sink", "breathe", "sway", "recede"]),
    (("sad", "lonely", "gloom", "empty", "guilty", "ashamed", "humiliated", "cold", "weak", "hurt"),
     ["sink", "breathe", "float", "sway"]),
    (("angry", "furious", "shout"), ["shiver", "punch", "jump", "shake_no"]),
    (("shock", "stunned", "surprised", "frozen"), ["punch", "shiver", "jump", "lean_in"]),
    (("worried", "nervous", "awkward", "embarrass", "flustered", "confused", "suspicious", "troubled"),
     ["tilt", "shake_no", "sway", "shiver"]),
    (("laugh", "joy", "overjoyed", "happy", "bright", "big"), ["hop", "bounce", "sway", "lean_in"]),
    (("smile", "warm", "gentle", "kind", "hopeful", "moved"), ["breathe", "sway", "nod", "float"]),
    (("determined", "serious", "resolute"), ["nod", "lean_in", "punch", "breathe"]),
    (("curious", "thinking", "wonder", "puzzled", "doubt"), ["tilt", "lean_in", "sway", "nod"]),
]
DEFAULT_ANIMS = ["breathe", "sway", "nod", "bounce", "tilt"]

# nhịp truyện -> các kiểu máy quay hợp
BEAT_MOTIONS = {
    "hook": ["punch_in", "focus", "zoom_in", "dutch"],
    "twist": ["punch_in", "focus", "dutch", "zoom_in", "drift"],
    "reveal": ["focus", "dolly_left", "zoom_in", "dolly_right"],
    "ending": ["zoom_out", "drift", "dolly_right", "focus", "dolly_left", "tilt_up"],
    "loop": ["zoom_out", "drift", "focus"],
}
DEFAULT_MOTIONS = ["drift", "dolly_left", "tilt_up", "zoom_in", "dolly_right", "zoom_out", "tilt_down", "pan_left",
                   "pan_right", "focus"]

# cảm xúc mạnh -> gói phản ứng tự gắn khi cảnh chưa có hiệu ứng / sticker / chữ tượng thanh nào:
# (tên gói, từ khóa, hiệu ứng sau nhân vật, hiệu ứng trước nhân vật, sticker cạnh đầu, motion máy quay)
# Tiếng đi kèm do build_video.py tự gắn theo hiệu ứng và sticker (speed_lines → ドン, exclaim → ビックリ, ...).
EMOTION_FX = [
    ("surprise", ("shock", "stunned", "surprise", "astonish", "amazed", "startl", "aghast", "horrified", "gasp",
                  "frozen", "speechless", "disbelief", "jolt"),
     "speed_lines", None, "exclaim", "punch_in"),
    ("despair", ("despair", "devastat", "defeated", "crushed", "hopeless", "oppressed", "cornered", "broken"),
     "gloom", None, "lines", "zoom_out"),
    ("cry", ("crying", "cries", "cry", "tearful", "tears", "sobbing", "sobs", "heartbroken", "weeping"),
     None, "tears", None, None),
    ("angry", ("angry", "furious", "rage", "shout", "irritated", "annoyed", "hostile", "indignant", "resentful",
               "outraged"), "speed_lines", None, "anger", "shake"),
    ("scared", ("scared", "afraid", "fear", "terrified", "horror", "panic", "frightened", "dread", "ominous",
                "apprehensive", "uneasy", "anxious"), "gloom", None, "sweat", None),
    ("proud", ("proud", "triumph", "smug", "confident", "victor", "cool", "boast", "cocky"),
     "rays", "sparkles", None, "punch_in"),
    ("joy", ("overjoyed", "excited", "delight", "joy", "laugh", "cheer", "thrilled", "elated", "ecstatic", "happy"),
     None, "sparkles", "spark", None),
    ("love", ("love", "blush", "shy", "touched", "moved", "grateful", "crush", "smitten"), None, "hearts", "heart", None),
    ("awkward", ("awkward", "embarrass", "nervous", "flustered", "ashamed", "guilty", "sheepish", "worried"),
     None, None, "sweat", None),
    ("confused", ("confused", "puzzled", "doubt", "suspicious", "curious", "wonder", "bewilder", "perplex"),
     None, None, "question", None),
    ("sad", ("sad", "lonely", "isolated", "gloom", "disappoint", "hurt", "regret", "remorse", "melanchol"),
     "gloom", None, "tear", None),
]


def emotion_fx(emotion):
    """Gói phản ứng cho emotion, khớp đầu từ (để "sob" không khớp "sobering")."""
    words = re.findall(r"[a-z]+", (emotion or "").lower())
    return next((fx for fx in EMOTION_FX if any(w.startswith(k) for w in words for k in fx[1])), None)


def add_reaction(scene, main, previous_kind):
    """Gắn gói phản ứng theo cảm xúc vào cảnh (như video mẫu: bất ngờ thì 集中線 + ！ + ドン, khoe thì tia sáng + ✦).
    Không gắn khi kịch bản đã tự đặt hiệu ứng / sticker / chữ, hoặc cảnh trước vừa dùng đúng gói này. Trả về tên gói."""
    fx = emotion_fx(scene.get("emotion"))
    layers = scene.get("layers", [])
    busy = any("effect" in l or "word" in l or Path(str(l.get("image", ""))).parent.name == "stickers" for l in layers)
    if fx is None:
        return None
    kind, _, behind, front, sticker, motion = fx
    scene["_emotion_fx"] = kind                 # build_video.py: cảnh cảm xúc được ưu tiên gắn tiếng (kể cả hiệu ứng có sẵn)
    if busy or kind == previous_kind:
        return kind
    target = main.get("id") or Path(main["image"]).stem
    index = layers.index(main)
    if behind:
        effect = {"effect": behind, "duration": 1.6}
        if behind in ("rays", "aura"):
            effect["on"] = target
        layers.insert(index, effect)
    if front:
        layers.append({"effect": front, "on": target})
    if sticker:
        layers.append({"image": f"stickers/{sticker}.png", "size": "small", "at": f"{target}.beside_right",
                       "anim": "pop", "start": 0.1})
    if motion and "motion" not in scene:
        scene["motion"] = motion
    return kind


PLACE_TRANSITIONS =["push_left", "whip", "wipe", "push_up", "iris", "zoom", "push_right"]
HALF_POSITIONS = ["floor", "floor_left", "floor", "floor_right"]


def main_layer(scene):
    """Lớp ảnh chủ thể của cảnh (cutouts/NNN...png), hoặc None."""
    for layer in scene.get("layers", []):
        image = Path(layer.get("image", ""))
        if image.parent.name == "cutouts" and image.stem.startswith(f"{scene['id']:03d}"):
            return layer
    return None


def pick(pool, recent, seed):
    """Chọn trong pool theo vòng, bỏ qua những giá trị vừa dùng."""
    for k in range(len(pool)):
        choice = pool[(seed + k) % len(pool)]
        if choice not in recent:
            return choice
    return pool[seed % len(pool)]


def anim_pool(emotion):
    emotion = (emotion or "").lower()
    for words, pool in EMOTION_ANIMS:
        if any(w in emotion for w in words):
            return pool
    return DEFAULT_ANIMS


def fill(script):
    """Điền anim, motion, transition, vị trí còn trống. Sửa trực tiếp script và trả về nó."""
    recent_anims, recent_motions, last_transition, previous, last_fx = [], [], None, None, None
    for index, scene in enumerate(script["scenes"]):
        seed = scene["id"] * 7
        main = main_layer(scene)
        if main is not None and scene.get("characters"):
            last_fx = add_reaction(scene, main, last_fx)
            if "anim" not in main:
                # lớp dán sát mép (có cột, tường vẽ dính) đứng yên, không nhún lắc
                stuck = str(main.get("at", "")).startswith("edge_")
                main["anim"] = "none" if stuck else pick(anim_pool(scene.get("emotion")), recent_anims[-2:], seed)
                main["_auto_anim"] = True           # anim tự chọn: build_video.py không gắn tiếng cho nó
            recent_anims.append(main["anim"])
            if (scene.get("shot") == "half" and "at" not in main and "path" not in main
                    and len(scene["characters"]) == 1):
                main["at"] = HALF_POSITIONS[index % len(HALF_POSITIONS)]
        if "motion" not in scene:
            scene["motion"] = pick(BEAT_MOTIONS.get(scene.get("beat"), DEFAULT_MOTIONS), recent_motions[-2:], seed)
        recent_motions.append(scene["motion"])
        if "transition" not in scene:
            scene["transition"] = transition(previous, scene, last_transition, seed)
        last_transition = scene["transition"]
        previous = scene
    return script


def transition(previous, scene, last, seed):
    if previous is None:
        return "cut"
    if (previous.get("filter") == "sepia") != (scene.get("filter") == "sepia"):
        return "fade"                                   # vào hoặc ra hồi tưởng
    if scene.get("beat") != previous.get("beat") and scene.get("beat") in ("twist", "reveal"):
        return "flash"
    if scene.get("location") != previous.get("location"):
        return pick(PLACE_TRANSITIONS, [last], seed // 7 * 3)    # đổi bối cảnh (bước 3 nguyên tố cùng 7 kiểu)
    if scene.get("beat") != previous.get("beat"):
        return "fade"
    return "fade" if scene["id"] % 4 == 0 and last != "fade" else "cut"   # cùng chỗ: phần lớn cắt thẳng


def report(script):
    """Cảnh báo (không chặn) khi một kiểu lặp nhiều cảnh liền: trả về danh sách câu cảnh báo."""
    warnings = []
    for name, values in (("anim nhân vật", [(s["id"], (main_layer(s) or {}).get("anim")) for s in script["scenes"]
                                             if s.get("characters")]),
                         ("motion", [(s["id"], s.get("motion")) for s in script["scenes"]])):
        run = 1
        for (_, a), (sid, b) in zip(values, values[1:]):
            run = run + 1 if a == b and b not in (None, "none") else 1
            if run == 3:
                warnings.append(f"cảnh {sid}: {name} '{b}' lặp 3 cảnh liền")
    return warnings
