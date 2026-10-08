"""Dựng videos/002-haha-no-bento/script.json: 母のお弁当ノート, khoảng 90 giây, theo config/script_guide.md."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "script.json"
TALK = "mouth open while talking"
WALK = "the other leg stepping forward, arms swinging the other way"


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


def scene(beat, speaker, text, who, action="", emotion="", shot="half", loc="kitchen", motion="none", anim="none",
          before=(), after=(), alt=None, filter="none", obj=None, path=None):
    """who: tên nhân vật, hoặc None nếu cảnh chỉ có đồ vật (obj)."""
    sid = len(scenes) + 1
    cid = who or "objects"
    main = {"id": cid, "image": f"cutouts/{sid:03d}.png", "anim": anim}
    if obj:
        main.update(size="large" if shot != "small" else "medium", at="center")
    if path:
        main["path"] = path
    layers = [dict(l, on=cid) if l.get("on") == "_" else l for l in before] + [main]
    layers += [dict(l, on=cid) if l.get("on") == "_" else l for l in after]
    s = {"id": sid, "beat": beat, "text": text, "speaker": speaker, "characters": [who] if who else [],
         "action": action, "emotion": emotion, "location": loc, "motion": motion, "filter": filter, "layers": layers}
    if who:
        s["shot"] = shot
    if obj:
        s["object"] = obj
    if alt:
        s["alt_pose"] = alt
    scenes.append(s)


ME, TEEN, MOM, PAT, DAD = "me", "me_teen", "mother", "mother_patient", "father"
BOX = "a small pink lunch box"

# ---- setup: cơm hộp kyaraben của mẹ ----
scene("setup", "narrator", "母は毎朝、\nお弁当を作った。", MOM, f"standing at the kitchen counter, packing food into {BOX} with chopsticks",
      "gentle smile", motion="zoom_in", anim="bounce", after=[fx("sparkles", "_")])
scene("setup", "narrator", "朝5時、\n包丁の音で\n目が覚める。", TEEN, "lying in bed under a blanket, rubbing her eyes", "sleepy",
      loc="bedroom", after=[word("トントン", TEEN, vertical=True)])
scene("setup", "narrator", "タコさんに、\nうさぎのリンゴ。", None, obj="an open pink lunch box with octopus-shaped red sausages, "
      "rabbit-shaped apple slices and rice with a smiley face made of seaweed", motion="zoom_in", anim="pop",
      after=[fx("sparkles", "_")])
scene("setup", "me_teen", "もう高校生なのに…", TEEN, f"standing in a classroom, holding {BOX} with both hands", "embarrassed",
      loc="classroom", after=[stk("sweat", TEEN)])
scene("setup", "narrator", "クラスで\n笑われた。", TEEN, f"standing with her head down, holding {BOX}", "ashamed", shot="full",
      loc="classroom", motion="shake", before=[fx("speed_lines")])
scene("setup", "narrator", "恥ずかしくて、\nたまらなかった。", TEEN, "covering her face with both hands", "humiliated", shot="close",
      loc="classroom", motion="zoom_in", before=[fx("gloom")])

# ---- rise1: "đừng làm nữa" ----
scene("rise1", "me_teen", "もう作らないで！", TEEN, "shouting with both fists clenched", "angry", motion="shake", anim="jump",
      after=[stk("anger", TEEN), fx("flash")])
scene("rise1", "narrator", "母は少し、\n黙っていた。", MOM, f"standing still, holding {BOX}, looking down", "sad",
      before=[fx("gloom")])
scene("rise1", "mother", "…そっか", MOM, "small sad smile, looking at her daughter", "sad smile", shot="close", motion="zoom_in",
      alt=TALK)
scene("rise1", "narrator", "次の日も、\nお弁当はあった。", None, obj="a lunch box wrapped in a pink cloth on a wooden table",
      anim="pop")
scene("rise1", "narrator", "私はそれを、\n食べずに残した。", TEEN, "walking away with her back turned", "cold", shot="full",
      loc="genkan", motion="pan_left", anim="exit_right", alt=WALK)
scene("rise1", "narrator", "母は、何も\n言わなかった。", MOM, "washing a lunch box at the sink", "lonely", motion="zoom_out",
      before=[fx("gloom")])

# ---- rise2: Tokyo ----
scene("rise2", "narrator", "高校を出て、\n東京へ出た。", ME, "walking with a determined stride, pulling a small red rolling suitcase",
      "determined", shot="full", loc="station", motion="pan_right", anim="bounce", alt=WALK)
scene("rise2", "narrator", "仕事は毎日、\n終電まで。", ME, "slumped over an office desk, typing on a laptop", "exhausted",
      loc="office", after=[stk("sweat", ME)])
scene("rise2", "narrator", "夕飯は、\nいつもコンビニ。", ME, "sitting on the floor, eating a convenience store bento from a plastic tray",
      "tired", loc="apartment", motion="zoom_in")
scene("rise2", "narrator", "味なんて、\nしなかった。", ME, "holding chopsticks, staring blankly", "empty", shot="close",
      loc="apartment", before=[fx("gloom")], after=[fx("rain")])
scene("rise2", "mother", "ちゃんと\n食べてる？", MOM, "holding a white smartphone to her ear", "worried", anim="bounce", alt=TALK)
scene("rise2", "me", "食べてるよ。\n忙しいの", ME, "holding a white smartphone to her ear, looking away", "annoyed",
      loc="apartment", after=[stk("sweat", ME)])
scene("rise3", "narrator", "ある日、\n荷物が届いた。", None, obj="a cardboard delivery box with a shipping label", loc="apartment",
      motion="zoom_in", anim="pop", after=[word("ピンポーン", "objects", "above")])
scene("rise3", "narrator", "中には、\n母の手料理。", None, obj="an open cardboard box full of plastic food containers with homemade "
      "japanese side dishes and a folded letter", loc="apartment", motion="zoom_in", anim="pop", after=[fx("sparkles", "_")])
scene("rise3", "mother", "体だけは、\n大事にね", MOM, "smiling gently with hands clasped in front", "warm", motion="zoom_in",
      anim="bounce", before=[fx("aura", "_", colour="#FFB3D1")])
scene("rise3", "me", "…うん", ME, "holding a letter on pink paper, lips trembling", "moved", shot="close", loc="apartment")
scene("rise3", "narrator", "それから半年後。", ME, "standing at an office desk, looking at a ringing white smartphone", "surprised",
      loc="office", after=[stk("exclaim", ME)])
scene("rise3", "father", "母さんが、\n倒れた", DAD, "holding a white smartphone to his ear, eyes wide", "shocked", shot="close",
      loc="dining_room", motion="shake", before=[fx("speed_lines")], after=[fx("flash")])
scene("rise3", "narrator", "頭が、\n真っ白になった。", ME, "frozen in place with her mouth open", "shocked", shot="close",
      loc="office", motion="shake", before=[fx("speed_lines")])
scene("rise3", "narrator", "新幹線に、\n飛び乗った。", ME, "running fast", "desperate", shot="full", loc="station", motion="pan_left",
      anim="bounce", alt="running with the other leg forward, arms swinging the other way", path=["off_right", "center"])

# ---- twist: cuốn sổ ----
scene("twist", "narrator", "病院の母は、\n小さく見えた。", PAT, "lying in a hospital bed under a white blanket", "weak smile",
      loc="hospital_room", motion="zoom_in", before=[fx("gloom")])
scene("twist", "mother_patient", "あら、\n来てくれたの", PAT, "sitting up in a hospital bed", "gentle smile", loc="hospital_room",
      anim="bounce", alt=TALK)
scene("twist", "narrator", "ただの、\n過労だった。", ME, "letting out a breath with her shoulders dropping", "relieved",
      loc="hospital_room", after=[word("ホッ", ME)])
scene("twist", "narrator", "着替えを取りに\n実家へ戻った。", ME, "walking with a tote bag on her shoulder", "tired", shot="full",
      loc="genkan", motion="pan_right", anim="bounce", alt=WALK)
scene("twist", "narrator", "台所の棚に、\n古いノート。", None, obj="an old worn notebook with a faded pink cover lying on a wooden shelf",
      motion="zoom_in", anim="pop", after=[fx("sparkles", "_")])
scene("twist", "narrator", "表紙には\n「お弁当\nノート」", None, obj="an old notebook with a hand-drawn lunch box doodle on its pink cover",
      motion="zoom_in", anim="pop")
scene("twist", "narrator", "幼稚園から\n毎日の記録。", ME, "sitting at a kitchen table, turning the pages of an old notebook",
      "curious", after=[stk("question", ME)])
scene("twist", "mother", "今日はタコさん\n喜ぶかな", MOM, "packing octopus-shaped sausages into a small lunch box", "happy",
      motion="zoom_in", anim="bounce", filter="sepia", after=[fx("sparkles", "_")])
scene("twist", "mother", "全部、\n食べてくれた！", MOM, "raising both hands in joy", "overjoyed", anim="jump", filter="sepia",
      after=[fx("hearts", "_")])
scene("twist", "mother", "キャラ弁、\n恥ずかしい\nみたい", MOM, "looking down at an open lunch box", "worried", filter="sepia",
      after=[stk("sweat", MOM)])
scene("twist", "mother", "普通のおかずに\nしよう。\nごめんね", MOM, "writing in a notebook at a kitchen table", "apologetic",
      shot="close", motion="zoom_in", filter="sepia")
scene("twist", "mother", "今日も残してた\n疲れてるのかな", MOM, "holding an untouched lunch box", "sad", filter="sepia",
      before=[fx("gloom")])
scene("twist", "narrator", "最後のページ。", None, obj="an old notebook open to its last page with handwritten japanese text",
      motion="zoom_in", anim="pop")
scene("twist", "mother", "いつか、\nあの子のお弁当、\n食べたいな", MOM, "smiling with her eyes closed, hands on her chest", "hopeful",
      shot="close", motion="zoom_in", filter="sepia", before=[fx("rays", "_"), fx("aura", "_", colour="#FFB3D1")])
scene("twist", "narrator", "涙が、\n止まらなかった。", ME, "holding an old notebook to her chest, crying", "crying", shot="close",
      motion="zoom_in", after=[fx("tears", "_")])

# ---- ending: con làm cơm hộp ----
scene("ending", "narrator", "次の朝、\n台所に立った。", ME, "wearing a pink apron, cracking an egg into a frying pan", "determined",
      anim="bounce", after=[fx("sparkles", "_")])
scene("ending", "narrator", "卵焼きは、\nうまく巻けない。", ME, "holding a frying pan with a messy rolled omelet", "troubled smile",
      after=[stk("sweat", ME)])
scene("ending", "narrator", "タコさんも、\n少し不格好。", None, obj="a pink lunch box with slightly misshapen octopus-shaped sausages "
      "and a lopsided rolled omelet", motion="zoom_in", anim="pop", after=[fx("sparkles", "_")])
scene("ending", "me", "お母さん、\nお弁当だよ", ME, f"holding out {BOX} with both hands", "shy smile", loc="hospital_room",
      anim="bounce", alt=TALK, after=[fx("hearts", "_")])
scene("ending", "mother_patient", "…これ、\nあなたが？", PAT, "sitting up in a hospital bed, eyes wide", "surprised", shot="close",
      loc="hospital_room", motion="zoom_in", after=[stk("exclaim", PAT)])
scene("ending", "narrator", "母はゆっくり、\n一口食べた。", PAT, f"sitting in a hospital bed, eating with chopsticks from {BOX}",
      "calm", loc="hospital_room")
scene("ending", "mother_patient", "…おいしい", PAT, "smiling with tears, holding chopsticks", "happy tears", shot="close",
      loc="hospital_room", motion="zoom_in", before=[fx("aura", "_", colour="#FFB3D1")], after=[fx("sparkles", "_")])
scene("ending", "narrator", "母が、\n泣きながら笑った。", PAT, "laughing while crying, one hand on her cheek", "laughing and crying",
      loc="hospital_room", anim="bounce", after=[fx("tears", "_"), fx("hearts", "_")])
scene("ending", "me", "これからは、\n私が作るね", ME, "smiling with tears, hands clasped in front", "happy tears",
      loc="hospital_room", motion="zoom_in", anim="bounce", alt=TALK, after=[fx("sparkles", "_")])
scene("ending", "narrator", "あのノートの\n続きは、", None, obj="an old notebook open with fresh new handwriting on a page and a pen "
      "lying on it", motion="zoom_in", anim="pop", after=[fx("sparkles", "_")])
scene("ending", "narrator", "今、私が\n書いている。", ME, "writing in an old notebook at a kitchen table, smiling", "gentle smile",
      motion="zoom_out", before=[fx("rays", "_"), fx("aura", "_")])

script = {
    "title": ["母の", "お弁当ノート"],
    "font": "Noto Sans CJK JP", "font_file": "fonts/NotoSansCJKjp-Black.otf",
    "speakers": {"narrator": "#4FC3F7", "me": "#4FC3F7", "me_teen": "#4FC3F7", "mother": "#F48FB1",
                 "mother_patient": "#F48FB1", "father": "#FFB74D"},
    "scenes": scenes,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
shots = {k: sum(1 for s in scenes if s.get("shot") == k) for k in ("full", "half", "close")}
print(f"{len(scenes)} cảnh; shot {shots}; đồ vật {sum(1 for s in scenes if 'object' in s)}; "
      f"alt_pose {sum(1 for s in scenes if 'alt_pose' in s)}; hiệu ứng {sum(1 for s in scenes for l in s['layers'] if 'effect' in l)}")
