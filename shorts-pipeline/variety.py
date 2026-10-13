"""Tự đa dạng chuyển động khi kịch bản bỏ trống, để video không lặp một kiểu (dùng trong build_video.py).

Điền vào chỗ trống, không đổi giá trị kịch bản đã ghi:
  anim của lớp nhân vật chính   theo cảm xúc ("emotion"), khác 2 cảnh trước
  motion của cảnh               theo nhịp truyện ("beat"), khác 2 cảnh trước
  transition (chuyển cảnh)      theo thay đổi bối cảnh, hồi tưởng, nhịp
  at của nhân vật nửa người     luân phiên giữa, hơi trái, hơi phải
  "punchline": true             câu chốt: cắt thẳng, máy quay impact (giật zoom + rung + ドドン), khoảng lặng nhạc,
                                nhân vật giật người; cảnh ngay trước được zoom chậm dồn nén (build)
  câu cảm thán (！)              nhân vật giật người (snap, punch...), cách một câu thì máy quay giật zoom (punch_in)
Kết quả cố định theo kịch bản (không ngẫu nhiên), nên dựng lại ra y hệt.
"""
import re
from pathlib import Path

# cảm xúc (từ khóa trong "emotion") -> các kiểu anim hợp
EMOTION_ANIMS = [
    (("cry", "tear", "sob", "heartbroken"), ["sink", "deflate", "breathe", "shiver", "float"]),
    (("scared", "afraid", "fear", "terrified", "panic", "horror"), ["shiver", "jelly", "recede", "shake_no", "sink"]),
    (("relieved", "relief", "calm", "peaceful", "nostalgic", "dreamy", "sleepy", "tired"), ["breathe", "float", "sway", "sink"]),
    (("excited", "giggl", "mischiev", "playful", "proud", "triumph", "cheer"), ["hop", "squash", "jump", "bounce", "spin_in"]),
    (("shy", "blush", "love", "in love", "touched", "grateful"), ["sway", "jelly", "tilt", "float", "nod"]),
    (("jealous", "annoyed", "irritated", "sulk", "pout", "disgust"), ["shake_no", "puff", "tilt", "punch", "sway"]),
    (("regret", "disappoint", "defeated", "exhausted", "despair"), ["deflate", "sink", "breathe", "sway", "recede"]),
    (("sad", "lonely", "gloom", "empty", "guilty", "ashamed", "humiliated", "cold", "weak", "hurt"),
     ["sink", "breathe", "float", "sway"]),
    (("angry", "furious", "shout"), ["puff", "shiver", "punch", "jump", "shake_no"]),
    (("shock", "stunned", "surprised", "frozen"), ["stretch_up", "punch", "jelly", "shiver", "jump", "lean_in"]),
    (("worried", "nervous", "awkward", "embarrass", "flustered", "confused", "suspicious", "troubled"),
     ["tilt", "jelly", "shake_no", "sway", "shiver"]),
    (("laugh", "joy", "overjoyed", "happy", "bright", "big"), ["hop", "squash", "bounce", "sway", "lean_in"]),
    (("smile", "warm", "gentle", "kind", "hopeful", "moved"), ["breathe", "sway", "nod", "float"]),
    (("determined", "serious", "resolute"), ["nod", "lean_in", "punch", "breathe"]),
    (("curious", "thinking", "wonder", "puzzled", "doubt"), ["tilt", "lean_in", "sway", "nod"]),
]
DEFAULT_ANIMS = ["breathe", "sway", "nod", "bounce", "tilt"]
SNAP_ANIMS = ["snap", "punch", "stretch_up", "snap", "jelly"]   # câu chốt, câu cảm thán: phản ứng giật tức thì

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
     "gloom", "shock_lines", None, "zoom_out"),
    ("cry", ("crying", "cries", "cry", "tearful", "tears", "sobbing", "sobs", "heartbroken", "weeping"),
     None, "tears", None, None),
    ("angry", ("angry", "furious", "rage", "shout", "irritated", "annoyed", "hostile", "indignant", "resentful",
               "outraged"), "speed_lines", "anger", None, "shake"),
    ("scared", ("scared", "afraid", "fear", "terrified", "horror", "panic", "frightened", "dread", "ominous",
                "apprehensive", "uneasy", "anxious"), "gloom", "sweat", None, None),
    ("proud", ("proud", "triumph", "smug", "confident", "victor", "cool", "boast", "cocky"),
     "rays", "sparkles", None, "punch_in"),
    ("joy", ("overjoyed", "excited", "delight", "joy", "laugh", "cheer", "thrilled", "elated", "ecstatic", "happy"),
     None, "sparkles", "spark", None),
    ("love", ("love", "blush", "shy", "touched", "moved", "grateful", "crush", "smitten"), None, "hearts", "heart", None),
    ("awkward", ("awkward", "embarrass", "nervous", "flustered", "ashamed", "guilty", "sheepish", "worried"),
     None, "sweat", None, None),
    ("sigh", ("sigh", "tired", "weary", "exhausted", "bored", "fed", "resigned", "relieved", "relief", "drained"),
     None, "sigh", None, None),
    ("dizzy", ("dizzy", "dazed", "overwhelm", "giddy", "spinning", "woozy"), None, "dizzy", None, None),
    ("idea", ("idea", "realiz", "inspired", "eureka", "scheming", "plotting", "clever", "brilliant"),
     None, "idea", None, "punch_in"),
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


# Hiệu ứng video nền đen (library/fx, chồng kiểu screen trong build_video.py) theo cảm xúc / nơi chốn của cảnh.
# Thứ tự là độ ưu tiên (ăn mừng trước vui). Tự gắn tối đa ~30% số cảnh, không lặp cùng nhóm hai cảnh liền.
FX_DIR = Path(__file__).resolve().parent / "library" / "fx"
# Đã bỏ hẳn khói (smoke): video khói thật trên nét vẽ phẳng trông như vết bẩn (video 022 cảnh 39-41). Kịch bản lỡ ghi
# "fx_smoke" thì drop_unknown_fx() bỏ đi.
EMOTION_OVERLAY = [
    (("celebrat", "congrat", "victory", "overjoyed", "ecstatic"), "glitter"),
    (("proud", "triumph", "smug", "confident", "victor", "boast", "cocky"), "gold"),
    (("joy", "excited", "delight", "laugh", "cheer", "thrilled", "elated", "happy"), "sparkle"),
    (("inspired", "idea", "wonder", "amazed", "realiz", "enlighten"), "magic"),
    (("touched", "moved", "grateful", "love", "tender", "heartwarm", "relieved", "hopeful", "warm"), "bokeh"),
    (("nostalg", "memory", "reminisc", "wistful", "bittersweet"), "light_leak"),
    (("lonely", "quiet", "calm", "peaceful", "melanchol", "sad", "isolated", "empty"), "dust"),
]
LOCATION_OVERLAY = {"mood_warm_memory": "bokeh", "mood_happy_sparkle": "sparkle", "mood_night_stars": "dust",
                    "mood_sakura": "bokeh", "mood_time_skip": "light_leak"}
FX_SHARE = 0.3
BUSY_EFFECTS = {"rays", "speed_lines", "flash", "gloom", "aura", "shock_lines"}


def drop_unknown_fx(scene):
    """Bỏ lớp hiệu ứng video mà thư viện không có (nhóm đã loại vì trông 3D, hoặc chưa tải): dựng tiếp, không báo lỗi."""
    layers = scene.get("layers") or []
    keep = [l for l in layers if not (str(l.get("effect", "")).startswith("fx_")
                                      and (l["effect"][3:] == "smoke" or not any((FX_DIR / l["effect"][3:]).glob("*.mp4"))))]
    if len(keep) != len(layers):
        scene["layers"] = keep


def overlay_for(scene):
    """Nhóm hiệu ứng video hợp với cảnh, hoặc None."""
    if scene.get("filter") == "sepia":
        return "light_leak"                     # hồi tưởng: vệt sáng như phim cũ
    if scene.get("location") in LOCATION_OVERLAY:
        return LOCATION_OVERLAY[scene["location"]]
    words = re.findall(r"[a-z]+", str(scene.get("emotion", "")).lower())
    return next((group for keys, group in EMOTION_OVERLAY if any(w.startswith(k) for w in words for k in keys)), None)


def add_overlay(scene, previous_group, used, total):
    """Gắn {"effect": "fx_<nhóm>"} vào cuối "layers" (vẽ sau cùng: ánh sáng phủ lên cả nhân vật, như video mẫu).
    Bỏ qua khi kịch bản đã đặt hiệu ứng fx_, khi cùng nhóm với cảnh trước, khi đã đủ ~30% số cảnh, khi chưa tải thư viện."""
    layers = scene.setdefault("layers", [])
    if any(str(l.get("effect", "")).startswith("fx_") for l in layers):
        return None
    if any(l.get("effect") in BUSY_EFFECTS for l in layers):   # đã có tia sáng / 集中線...: thêm lớp ánh sáng thì rối
        return None
    group = overlay_for(scene)
    if not group or group == previous_group or used >= total * FX_SHARE or not any((FX_DIR / group).glob("*.mp4")):
        return None
    layers.append({"effect": f"fx_{group}"})
    return group


SPEAKER_ANIMS = ["nod", "lean_in", "sway", "hop"]       # người đang nói: khoa tay, chồm tới
LISTENER_ANIMS = ["tilt", "nod", "breathe", "jelly"]    # người nghe: nghiêng đầu, gật gù, giật mình


def add_interaction(scene, nth, seed):
    """Cảnh từ 2 nhân vật: ai cũng cử động (người nói / người nghe khác kiểu); câu thoại thì cách một cảnh một lần máy giữ
    toàn cảnh nửa đầu câu rồi đẩy vào mặt người nói ("focus": hai cú máy trong một cảnh). Trả về số cảnh thoại đã đếm."""
    layers = [l for l in scene.get("layers", []) if Path(str(l.get("image", ""))).parent.name == "cutouts"]
    if len(scene.get("characters") or []) < 2 or len(layers) < 2:
        return nth
    speaker = scene.get("speaker")
    for k, layer in enumerate(layers):
        if "anim" not in layer and not str(layer.get("at", "")).startswith("edge_"):
            pool = SPEAKER_ANIMS if layer.get("id") == speaker else LISTENER_ANIMS
            layer["anim"] = pool[(seed + k) % len(pool)]
            layer["_auto_anim"] = True
    if scene.get("focus") or scene.get("punchline") or not scene.get("_dialogue") \
            or speaker not in [l.get("id") for l in layers]:
        return nth
    nth += 1
    if nth % 2 == 1:
        scene["focus"] = {"on": speaker, "at": 0.45, "zoom": 1.4}
    return nth


def main_voice(script):
    """Giọng kể chính của video: speaker nói nhiều câu nhất (narrator, hoặc nhân vật chính tự kể)."""
    speakers = [s.get("speaker") for s in script.get("scenes", [])]
    return max(set(speakers), key=speakers.count) if speakers else None


def is_dialogue(scene, voice):
    """Câu thoại (nhân vật cất lời): không phải lời kể của giọng kể chính, hoặc nằm trong 「」."""
    speaker = scene.get("speaker")
    return speaker not in (None, "", "narrator") and (speaker != voice or "「" in scene.get("text", ""))


CALM_MOTIONS = ["zoom_in", "drift", "zoom_out", "pan_left", "zoom_in", "pan_right"]   # tranh cả cảnh: không nghiêng / nhòe
ROUGH_MOTIONS = {"dutch", "focus", "tilt_up", "tilt_down", "dolly_left", "dolly_right", "shake", "build"}


def fill(script):
    """Điền anim, motion, transition, vị trí còn trống. Sửa trực tiếp script và trả về nó."""
    from steps.render_rules import normalize_motion
    normalize_motion(script)
    from analysis_profile import enabled, apply
    if enabled(script):
        return apply(script)
    for scene in script["scenes"]:
        # tranh vẽ cả cảnh / màn hình điện thoại (video 031): hiệu ứng phủ (mưa, tuyết, hạt) che người, máy nghiêng / lấy nét
        # làm nhòe, điện thoại nghiêng ra ngoài khung: bỏ các thứ đó, chỉ giữ vệt sáng nhẹ của hồi tưởng
        if scene.get("full") or scene.get("phone"):
            scene["layers"] = [l for l in scene.get("layers", []) if not (str(l.get("effect", "")).startswith("fx_")
                               and l.get("effect") != "fx_light_leak")]
            if scene.get("motion") in ROUGH_MOTIONS:
                scene.pop("motion")
            scene.pop("focus", None)
            if scene.get("phone"):
                scene["motion"] = "zoom_in"
    recent_anims, recent_motions, last_transition, previous, last_fx = [], [], None, None, None
    exclaims = talks = talks_used = fx_used = dialogue_scenes = 0
    last_overlay = None
    voice = main_voice(script)
    for index, scene in enumerate(script["scenes"]):
        seed = scene["id"] * 7
        main = main_layer(scene)
        punch = bool(scene.get("punchline"))
        exclaim = not punch and bool(re.search(r"[！!]", scene.get("text", "")))
        if punch:
            scene.setdefault("transition", "cut")
            scene.setdefault("motion", "impact")
            scene.setdefault("music_stop", True)
            if previous is not None and previous.get("_auto_motion") and not previous.get("punchline"):
                previous["motion"] = "build"        # cảnh dẫn: zoom chậm dồn nén rồi mới tới cú chốt
                recent_motions[-1] = "build"
        if (punch or exclaim) and main is not None and "anim" not in main and not str(main.get("at", "")).startswith("edge_"):
            main["anim"] = pick(SNAP_ANIMS, recent_anims[-1:], seed)
            main["_auto_anim"] = True               # tiếng đã có ở máy quay (impact, punch_in)
        if exclaim:
            exclaims += 1
            if "motion" not in scene and exclaims % 2 == 1:
                scene["motion"] = "punch_in"        # zoom ~112%; cách một câu cảm thán, không thì rung cả video
        # nhân vật cất lời (câu thoại, không phải lời kể): máy nhích vào nhanh ~108%, cách một câu thoại một lần
        # (giọng kể chính của video, kể cả khi nhân vật chính tự kể, không tính là cất lời; câu trong 「」 thì có)
        dialogue = is_dialogue(scene, voice)
        scene["_dialogue"] = dialogue               # build_video.py: chỉ câu thoại mới mấp máy miệng
        if not punch and "motion" not in scene and dialogue:
            talks += 1
            if talks % 2 == 1 and recent_motions[-1:] != ["talk_in"] and talks_used < len(script["scenes"]) * 0.15:
                talks_used += 1
                scene["motion"] = "talk_in"
                scene["_auto_motion"] = True
        drop_unknown_fx(scene)
        calm = scene.get("full") or scene.get("phone")
        last_overlay = add_overlay(scene, last_overlay, fx_used, len(script["scenes"])) if not calm or \
            scene.get("filter") == "sepia" else None
        fx_used += bool(last_overlay)
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
        dialogue_scenes = add_interaction(scene, dialogue_scenes, seed)
        if "motion" not in scene and index == 0:   # móc câu: giật zoom vào ngay khung hình đầu (kể cả tranh cả cảnh)
            scene["motion"] = "punch_in"
            scene["_auto_motion"] = True
        if "motion" not in scene:
            pool = CALM_MOTIONS if calm else BEAT_MOTIONS.get(scene.get("beat"), DEFAULT_MOTIONS)
            scene["motion"] = pick(pool, recent_motions[-2:], seed)
            scene["_auto_motion"] = True
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
