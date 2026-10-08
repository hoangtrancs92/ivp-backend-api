"""Dựng script.json cho video 003 "父の財布の写真", khoảng 2 phút, theo config/script_guide.md.

Cấu trúc giữ chân người xem (TikTok):
  0-3 giây   câu mở gây tò mò: ảnh bé gái lạ rơi ra từ ví bố
  mỗi 15-20 giây một câu hỏi hoặc chi tiết mới: bố ngoại tình? -> chủ nhật bố đi đâu? -> bố cười với phụ nữ trẻ
  giữa video  twist giả (người phụ nữ là y tá, và cô ấy biết "tôi")
  3/4 video   twist thật: bé gái trong ảnh là "tôi" năm 5 tuổi
  kết         vòng lặp: tấm ảnh đó giờ nằm trong ví "tôi" (cùng một ảnh với cảnh mở đầu)
Sửa câu ở đây rồi chạy lại: python videos/003-chichi-no-saifu/build_script.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "script.json"
TALK = "mouth open while talking"
CREAM = "#F6F1E4"                              # màu lòng tấm ảnh chụp
WALK = "the other leg stepping forward, arms swinging the other way"
PHOTO = ("a single old instant photograph with a thick white border, slightly bent at one corner, lying flat; "
         "inside the photo frame a five-year-old girl with very short hair in light blue hospital pajamas "
         "smiles weakly and makes a peace sign")


def fx(kind, on=None, **kw):
    layer = {"effect": kind, **kw}
    if on:
        layer["on"] = on
    return layer


def stk(name, on, where="beside_left", start=0.3):
    return {"image": f"stickers/{name}.png", "size": "tiny", "at": f"{on}.{where}", "anim": "pop", "start": start}


def word(text, on, where="beside_right", start=0.3, vertical=False):
    return {"word": text, "size": 80, "at": f"{on}.{where}", "anim": "pop_fade", "start": start, "vertical": vertical}


scenes = []


def scene(beat, speaker, text, who, action="", emotion="", shot="half", loc="dining_room", motion=None, anim=None,
          before=(), after=(), alt=None, filter="none", obj=None, path=None, reuse=None, fill=None, at=None):
    """who: một tên nhân vật, danh sách hai tên (đứng trái, phải), hoặc None nếu cảnh chỉ có đồ vật (obj).
    reuse: dùng lại ảnh đồ vật của một cảnh khác (vd tấm ảnh ở cảnh 2), không sinh ảnh mới.
    fill: màu tô kín lòng tấm ảnh chụp (model vẽ lòng ảnh bằng màu nền xanh nên bị khoét khi tách nền).
    motion, anim để None: bước dựng tự chọn cho đa dạng (variety.py); chỉ ghi khi có chủ ý (shake, exit_right...)."""
    sid = len(scenes) + 1
    names = [who] if isinstance(who, str) else list(who or [])
    cid = names[0] if names else "objects"
    if reuse:
        main = [{"id": cid, "image": f"cutouts/{reuse:03d}.png", "size": "large", "at": "center", "anim": anim}]
    elif obj:
        main = [{"id": cid, "image": f"cutouts/{sid:03d}.png", "size": "large", "at": "center", "anim": anim}]
    elif len(names) == 2:
        main = [{"id": n, "image": f"cutouts/{sid:03d}_{n}.png", "size": "large", "at": side, "anim": anim}
                for n, side in zip(names, ("left", "right"))]
    else:
        main = [{"id": cid, "image": f"cutouts/{sid:03d}.png", "anim": anim}]
        if path:
            main[0]["path"] = path
    for layer in main:
        if layer["anim"] is None:
            del layer["anim"]
    resolve = lambda ls: [dict(l, on=cid) if l.get("on") == "_" else l for l in ls]   # "_" = nhân vật chính
    s = {"id": sid, "beat": beat, "text": text, "speaker": speaker, "characters": names,
         "action": action, "emotion": emotion, "location": loc, "filter": filter,
         "layers": resolve(before) + main + resolve(after)}
    if motion:
        s["motion"] = motion
    if fill:
        main[0]["fill_holes"] = fill
    if at:                                     # vd "edge_left": ảnh có cột, tường vẽ dính thì dán sát mép khung
        main[0]["at"] = at
    if names:
        s["shot"] = shot
    if obj:
        s["object"] = obj
    if alt:
        s["alt_pose"] = alt
    scenes.append(s)


ME, DAD, MOM, NURSE, KID = "me", "father", "mother", "nurse", "me_child_sick"

# ---- móc câu (0-8 giây) ----
scene("hook", "narrator", "父の財布から、\n写真が落ちた。", None, obj="an open brown leather wallet on a wooden table with an old "
      "photo sliding out of it", anim="pop", after=[word("ヒラッ", "objects", "above")])
scene("hook", "narrator", "知らない、\n女の子だった。", None, obj=PHOTO, fill=CREAM, anim="pop",
      before=[fx("speed_lines")])
scene("hook", "me", "…誰、この子？", ME, "holding an old small photo, staring at it", "confused", shot="close",
      after=[stk("question", ME)])
scene("hook", "narrator", "父は慌てて、\n写真を奪った。", DAD, "snatching something quickly with one hand", "flustered",
      motion="shake", before=[fx("speed_lines")], after=[stk("sweat", DAD)])

# ---- bối cảnh: người bố không bao giờ cười ----
scene("setup", "narrator", "父は昔から、\n無口な人だった。", DAD, "standing with arms crossed", "stern")
scene("setup", "narrator", "笑った顔なんて、\n見たことがない。", DAD, "facing forward with arms crossed, both eyes visible behind his glasses, mouth in a flat line", "expressionless",
      shot="close", before=[fx("gloom")])
scene("setup", "me", "まさか…\n浮気？", ME, "covering her mouth with one hand", "suspicious", shot="close", motion="shake",
      after=[stk("lines", ME, "above")])
scene("setup", "narrator", "その日から、\n父が気になった。", ME, "peeking around a doorway", "curious", loc="genkan")

# ---- nghi vấn 1: chủ nhật bố đi đâu ----
scene("rise1", "narrator", "毎週日曜、\n父は一人で\n出かける。", DAD, "walking out carrying a small tote bag", "calm", shot="full",
      loc="genkan", anim="exit_right", alt=WALK)
scene("rise1", "narrator", "行き先は、\n誰も知らない。", MOM, "tilting her head with a small smile", "calm", loc="kitchen",
      after=[stk("question", MOM)])
scene("rise1", "mother", "お父さんの、\n趣味でしょ", MOM, "smiling while washing dishes", "gentle smile", loc="kitchen")
scene("rise1", "narrator", "母は笑った。\nでも、目が\n赤かった。", MOM, "smiling with slightly teary eyes", "teary smile", shot="close",
      loc="kitchen")
scene("rise1", "narrator", "ある日曜、\n私は父をつけた。", ME, "sneaking forward wearing a cap and sunglasses", "determined",
      shot="full", loc="genkan", alt=WALK, path=["off_left", "center"])
scene("rise1", "narrator", "父が入ったのは、\n大きな病院。", DAD, "walking toward a building carrying a small tote bag", "calm",
      shot="full", loc="hospital_entrance", anim="none", at="edge_right")   # góc tòa nhà vẽ dính: sát mép phải
scene("rise1", "me", "病院…？\nどこか悪いの？", ME, "hiding behind a pillar, peeking", "worried", shot="close",
      loc="hospital_entrance", anim="none", at="edge_left", after=[stk("sweat", ME, "beside_right")])   # cột: sát mép trái

# ---- nghi vấn 2: người phụ nữ trẻ, bố cười ----
scene("rise2", "narrator", "父は、\n若い女性と\n話していた。", NURSE, "talking cheerfully", "bright smile",
      loc="hospital_hallway", alt=TALK)
scene("rise2", "narrator", "そして、\n笑っていた。", DAD, "laughing happily", "big laugh", loc="hospital_hallway",
      after=[fx("sparkles", "_"), fx("flash")])
scene("rise2", "me", "あの父が…\n笑ってる！？", ME, "frozen in shock, mouth wide open", "shocked", shot="close",
      loc="hospital_hallway", motion="shake", before=[fx("speed_lines")])
scene("rise2", "narrator", "頭に、\n血がのぼった。", ME, "clenching both fists", "furious", loc="hospital_hallway",
      anim="jump", after=[stk("anger", ME)])
scene("rise2", "narrator", "その夜、\n父を問い詰めた。", ME, "pointing forward angrily", "angry", motion="shake")
scene("rise2", "me", "あの女の人、\n誰なの！", ME, "shouting with one hand on the table", "angry", shot="close",
      alt=TALK, after=[fx("flash")])
scene("rise2", "father", "…お前には、\n関係ない", DAD, "looking away coldly", "cold", alt=TALK, before=[fx("gloom")])
scene("rise2", "narrator", "父はそれだけ\n言って去った。", DAD, "walking away with his back turned", "cold", shot="full",
      motion="pan_right", anim="exit_left", alt=WALK)
scene("rise2", "narrator", "母は、\n黙っていた。", MOM, "looking down quietly", "sad", loc="kitchen", before=[fx("gloom")])

# ---- nghi vấn 3: cô ấy biết "tôi" (twist giả) ----
scene("rise3", "narrator", "次の日曜。\n私は一人で\n病院へ。", ME, "walking with a determined stride", "determined", shot="full",
      loc="hospital_entrance", alt=WALK)
scene("rise3", "me", "父とは、\nどういう\n関係ですか", ME, "standing straight, speaking seriously", "serious",
      loc="hospital_hallway")
scene("rise3", "narrator", "彼女は、\n目を丸くした。", NURSE, "eyes wide open", "surprised", shot="close",
      loc="hospital_hallway", after=[stk("exclaim", NURSE)])
scene("rise3", "nurse", "もしかして…\n娘さん？", NURSE, "covering her mouth with both hands", "surprised smile",
      loc="hospital_hallway", alt=TALK)
scene("rise3", "nurse", "大きく、\nなったね", NURSE, "smiling warmly with hands clasped", "warm smile", shot="close",
      loc="hospital_hallway", after=[fx("sparkles", "_")])
scene("rise3", "me", "…え？", ME, "frozen, eyes wide", "stunned", shot="close", loc="hospital_hallway", motion="shake",
      before=[fx("speed_lines")])

# ---- twist thật: bé gái trong ảnh là "tôi" ----
scene("twist", "nurse", "あなたは昔、\nここにいたの", NURSE, "explaining gently", "gentle", loc="hospital_hallway")
scene("twist", "nurse", "5歳のとき、\n重い病気でね", NURSE, "looking down with a serious face", "serious",
      loc="hospital_hallway")
scene("twist", "narrator", "何も、\n覚えて\nいなかった。", ME, "holding her head with both hands", "shocked", shot="close",
      loc="hospital_hallway", before=[fx("gloom")])
scene("twist", "nurse", "お父さん、\n毎晩来てたのよ", NURSE, "smiling sadly", "sad smile", loc="hospital_hallway")
scene("twist", "narrator", "仕事帰りに、\n一日も欠かさず。", DAD, "walking quickly down a hallway at night in a suit", "worried",
      shot="full", loc="hospital_hallway", filter="sepia", alt=WALK, path=["off_left", "center"])
scene("twist", "narrator", "眠る私の手を、\nずっと\n握っていた。", DAD, "sitting by a hospital bed, holding a small hand", "worried",
      loc="hospital_room", filter="sepia", before=[fx("aura", "_")])
scene("twist", "father", "がんばれ…\nがんばれ…", DAD, "whispering with tears in his eyes", "crying", shot="close",
      loc="hospital_room", filter="sepia", alt=TALK, after=[fx("tears", "_")])
scene("twist", "narrator", "手術の前の日、\n写真を\n一枚撮った。", KID, "sitting on a hospital bed, smiling weakly, making a peace sign",
      "weak smile", loc="hospital_room", filter="sepia", after=[fx("sparkles", "_")])
scene("twist", "narrator", "それが、\nあの写真だった。", None, reuse=2, fill=CREAM, anim="pop",
      before=[fx("rays", "_"), fx("aura", "_")], after=[fx("flash")])
scene("twist", "me", "あの子は…\n私だったんだ", ME, "covering her mouth, crying", "crying", shot="close",
      loc="hospital_hallway", after=[fx("tears", "_")])

# ---- vì sao bố đến bệnh viện mỗi chủ nhật ----
scene("reveal", "nurse", "手術は成功。\nそれからね", NURSE, "smiling gently", "gentle smile", loc="hospital_hallway")
scene("reveal", "nurse", "毎週ここで、\n子どもたちに", NURSE, "pointing toward a room", "warm smile", loc="hospital_hallway")
scene("reveal", "narrator", "父は絵本を、\n読んでいたのだ。", DAD, "reading a picture book aloud, smiling", "kind smile",
      loc="hospital_room", alt=TALK, after=[fx("sparkles", "_")])
scene("reveal", "nurse", "娘が元気に\nなった\nお礼だって", NURSE, "smiling with hands on her chest", "warm smile",
      loc="hospital_hallway", before=[fx("aura", "_", colour="#FFB3D1")])
scene("reveal", "narrator", "涙で、\n前が\n見えなかった。", ME, "wiping tears with both hands", "crying", shot="close",
      loc="hospital_hallway", after=[fx("tears", "_")])

# ---- kết: nụ cười đầu tiên của bố ----
scene("ending", "narrator", "家に帰ると、\n父が待っていた。", DAD, "standing awkwardly with hands behind his back", "awkward",
      loc="genkan", after=[stk("sweat", DAD)])
scene("ending", "father", "…聞いたのか", DAD, "scratching his cheek", "embarrassed", shot="close", loc="genkan")
scene("ending", "me", "なんで、\n言わなかったの", ME, "crying with fists clenched", "crying", loc="genkan",
      after=[fx("tears", "_")])
scene("ending", "father", "怖い思い出は、\n忘れた\nままでいい", DAD, "speaking gently", "gentle", shot="close", loc="genkan",
      alt=TALK, before=[fx("aura", "_")])
scene("ending", "father", "お前が\n笑っていれば、\nそれでいい", DAD, "smiling gently for the first time", "gentle smile", shot="close",
      loc="genkan", before=[fx("rays", "_")], after=[fx("sparkles", "_")])
scene("ending", "narrator", "初めて見た、\n父の笑顔だった。", DAD, "smiling warmly", "warm smile", loc="genkan",
      before=[fx("aura", "_", colour="#FFB3D1")], after=[fx("hearts", "_")])
scene("ending", "me", "お父さん、\nありがとう", ME, "smiling through tears", "happy tears", loc="genkan",
      alt=TALK, after=[fx("hearts", "_")])
scene("ending", "narrator", "父は照れて、\nそっぽを向いた。", DAD, "looking away with red cheeks", "embarrassed", loc="genkan",
      after=[stk("sweat", DAD)])
scene("ending", "mother", "やっと、\n言えたね", MOM, "smiling with tears", "happy tears", loc="kitchen",
      before=[fx("aura", "_", colour="#FFB3D1")])
scene("ending", "narrator", "次の日曜は、\n二人で病院へ。", [DAD, ME], "walking forward, smiling", "happy", shot="full",
      loc="hospital_entrance", alt=WALK)
scene("ending", "narrator", "私も一緒に、\n絵本を読んだ。", ME, "reading a picture book aloud, smiling", "happy",
      loc="hospital_room", after=[fx("sparkles", "_")])

# ---- vòng lặp về cảnh mở đầu ----
scene("loop", "narrator", "今、\n私の財布にも、", None, obj="an open pink leather wallet seen from the front, nothing else, no table; "
      "tucked in its clear card pocket is " + PHOTO.removeprefix("a single "), anim="pop", after=[fx("sparkles", "_")])
scene("loop", "narrator", "あの写真が、\n入っている。", None, reuse=2, fill=CREAM, anim="pop",
      before=[fx("rays", "_"), fx("aura", "_")], after=[fx("sparkles", "_")])

script = {
    "title": ["父の財布にあった", "知らない女の子の写真"],
    "font": "Noto Sans CJK JP", "font_file": "fonts/NotoSansCJKjp-Black.otf",
    "speakers": {"narrator": "#4FC3F7", "me": "#4FC3F7", "father": "#FFB74D", "mother": "#F48FB1", "nurse": "#81C784"},
    "scenes": scenes,
}
OUT.write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
shots = {k: sum(1 for s in scenes if s.get("shot") == k) for k in ("full", "half", "close")}
print(f"{len(scenes)} cảnh; shot {shots}; đồ vật {sum(1 for s in scenes if 'object' in s)}; "
      f"alt_pose {sum(1 for s in scenes if 'alt_pose' in s)}; hiệu ứng {sum(1 for s in scenes for l in s['layers'] if 'effect' in l)}")
