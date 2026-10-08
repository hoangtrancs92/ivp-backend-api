"""Dựng script.json cho video 004 "給料か、眠れる夜か", khoảng 85 giây, theo config/script_guide.md.

Đề tài (người dùng): nhân viên phát hiện công ty xả thải lén. Tố cáo thì mất việc, im lặng thì sống yên.
Câu kết: "Anh chọn lương, hay chọn ngủ ngon?"

Cấu trúc giữ chân người xem:
  0-5 giây   móc câu: xấp tiền và điện thoại trên bàn, "phải chọn một" -> quay về 3 ngày trước
  phát hiện  ống thải xả nước đen ra sông, van chỉ mở ban đêm, quay video
  áp lực     quản đốc: "coi như không thấy", phong bì tiền; đàn anh: người tố cáo trước bị đuổi
  lý do im   con gái, vợ mang thai, nợ nhà 30 năm
  twist      con sông con gái chơi mỗi tuần chính là con sông nước đen chảy vào
  kết mở     vợ: "anh chọn gì em cũng theo" -> lại xấp tiền và điện thoại (vòng lặp) -> câu hỏi cho người xem
Sửa câu ở đây rồi chạy lại: python videos/004-kyuryo-ka-yoru-ka/build_script.py
"""
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


def scene(beat, speaker, text, who, action="", emotion="", shot="half", loc="dining_room", motion=None, anim=None,
          before=(), after=(), alt=None, filter="none", obj=None, path=None, reuse=None, at=None, transition=None):
    """who: một tên nhân vật, hoặc None nếu cảnh chỉ có đồ vật (obj).
    reuse: dùng lại ảnh đồ vật của cảnh khác. motion, anim, transition để None: bước dựng tự chọn (variety.py)."""
    sid = len(scenes) + 1
    names = [who] if who else []
    cid = who or "objects"
    image = f"cutouts/{(reuse or sid):03d}.png"
    main = {"id": cid, "image": image}
    if reuse or obj:
        main.update(size="large", at="center")
    if anim:
        main["anim"] = anim
    if path:
        main["path"] = path
    if at:
        main["at"] = at
    resolve = lambda ls: [dict(l, on=cid) if l.get("on") == "_" else l for l in ls]   # "_" = chủ thể của cảnh
    s = {"id": sid, "beat": beat, "text": text, "speaker": speaker, "characters": names,
         "action": action, "emotion": emotion, "location": loc, "filter": filter,
         "layers": resolve(before) + [main] + resolve(after)}
    for key, value in (("motion", motion), ("transition", transition), ("object", obj), ("alt_pose", alt)):
        if value:
            s[key] = value
    if names:
        s["shot"] = shot
    scenes.append(s)


I, BOSS, SENPAI, WIFE, KID = "worker", "boss", "senpai", "wife", "daughter"
MONEY = "a thick white envelope stuffed with japanese yen bills"

# ---- móc câu: lựa chọn đã ở trước mặt ----
scene("hook", I, "テーブルの上に、\n札束と、スマホ。", None, obj=f"{MONEY} lying next to a smartphone showing a paused video "
      "of a dark pipe, on a wooden table", motion="punch_in", anim="pop", after=[word("ドクン", "objects", "above")])
scene("hook", I, "どちらかを\n選ばなきゃ\nいけない。", I, "sitting at a table, staring down, sweating", "troubled", shot="close",
      before=[fx("gloom")], after=[stk("sweat", I, "beside_right")])
scene("hook", I, "3日前。\nすべてが\n始まった。", I, "in side view, walking down a factory aisle at night holding a flashlight",
      "tired", shot="full", loc="factory_floor", alt=WALK, transition="flash")

# ---- phát hiện ----
scene("rise1", I, "夜勤の\n見回り中、", I, "seen from behind, walking forward holding a flashlight", "calm",
      shot="full", loc="factory_back", alt=WALK)
scene("rise1", I, "変な臭いが\nした。", I, "covering his nose with one hand, frowning", "disgusted", loc="factory_back",
      after=[word("ツーン", I, vertical=True)])
scene("rise1", I, "工場の裏の、\n排水管。", None, obj="a large rusty drainage pipe sticking out of a concrete wall, pouring thick "
      "black liquid into a narrow canal", loc="factory_back", anim="none", at="edge_left", before=[fx("gloom")])   # tường vẽ dính: sát mép trái
scene("rise1", I, "真っ黒な水が、\n川へ流れて\nいた。", None, obj="a small river with thick black oily water and a few dead fish "
      "floating on the surface", loc="riverside", anim="pop", motion="shake", before=[fx("speed_lines")])
scene("rise1", I, "嘘だろ…", I, "frozen with eyes wide and mouth open", "shocked", shot="close", loc="factory_back",
      motion="shake", before=[fx("speed_lines")])
scene("rise1", I, "バルブは、\n夜だけ\n開いていた。", None, obj="a large red valve wheel on a rusty industrial pipe, turned open",
      loc="factory_back", anim="pop", after=[fx("sparkles", "_", colour="#FF8A65")])
scene("rise1", I, "誰かが、\nわざと\n開けている。", I, "looking around nervously in the dark", "suspicious", loc="factory_back",
      after=[stk("question", I)])
scene("rise1", I, "僕はスマホで、\n動画を撮った。", I, "in side view, holding up a smartphone to film something", "determined",
      loc="factory_back")

# ---- áp lực từ quản đốc ----
scene("rise2", I, "翌朝、\n工場長に\n報告した。", I, "walking forward with a serious face", "determined", shot="full",
      loc="manager_office", alt=WALK, path=["off_left", "center"])
scene("rise2", I, "排水が、\n川に流れて\nます", I, "standing straight, explaining seriously", "serious", loc="manager_office",
      alt=TALK)
scene("rise2", I, "工場長は、\n少し黙った。", BOSS, "sitting at a large desk with fingers interlocked", "cold",
      loc="manager_office", before=[fx("gloom")])
scene("rise2", BOSS, "見なかった\nことにしろ", BOSS, "leaning forward with a cold stare", "cold", shot="close",
      loc="manager_office", motion="dutch", alt=TALK)
scene("rise2", I, "でも、あれは\n違法です！", I, "clenching his fists", "angry", loc="manager_office", after=[fx("flash")])
scene("rise2", BOSS, "君には、\n家族が\nいるだろう", BOSS, "smiling coldly", "sinister smile", shot="close",
      loc="manager_office", before=[fx("gloom")])
scene("rise2", I, "机の上に、\n分厚い封筒。", None, obj=f"{MONEY} on a dark wooden office desk", loc="manager_office",
      motion="punch_in", anim="pop", after=[fx("sparkles", "_")])
scene("rise2", BOSS, "ボーナスだ。\n黙っていれば\nな", BOSS, "pushing something forward across a desk with one hand",
      "sly smile", loc="manager_office", alt=TALK)
scene("rise2", I, "言葉が、\n出なかった。", I, "standing frozen, sweating", "speechless", shot="close",
      loc="manager_office", after=[stk("sweat", I, "beside_right")])

# ---- cảnh báo của đàn anh ----
scene("rise3", I, "休憩中、\n先輩が\n言った。", SENPAI, "sitting with a paper cup of coffee", "tired",
      loc="factory_floor")
scene("rise3", SENPAI, "前にも、\n告発した\nやつがいた", SENPAI, "speaking quietly, looking down", "serious", shot="close",
      loc="factory_floor", alt=TALK)
scene("rise3", SENPAI, "次の週には、\nクビだった", SENPAI, "shrugging with both hands", "resigned", loc="factory_floor",
      before=[fx("gloom")])
scene("rise3", SENPAI, "この町に、\n次の仕事は\nないぞ", SENPAI, "looking straight ahead with a serious face", "serious",
      shot="close", loc="factory_floor", alt=TALK)

# ---- lý do để im lặng ----
scene("home", KID, "パパ、\nおかえり！", KID, "running forward with both arms open", "happy", shot="full", loc="genkan",
      alt="running with the other leg forward, arms open", after=[fx("hearts", "_")])
scene("home", I, "妻のお腹には、\n二人目がいる。", WIFE, "holding a tiny pair of white baby socks in both hands, smiling gently", "warm",
      before=[fx("aura", "_", colour="#FFB3D1")])
scene("home", I, "家のローンも、\nあと30年。", None, obj="a stack of bills and a house loan document on a wooden dining table",
      anim="pop")
scene("home", I, "黙れば、\n全部\n守れる…", I, "staring at a thick white envelope in his hand", "conflicted", shot="close",
      motion="dutch", before=[fx("gloom")])

# ---- twist: con sông của con gái ----
scene("twist", KID, "パパ、週末\nまた川で\n遊ぼう！", KID, "smiling brightly and pointing outside", "excited", alt=TALK,
      after=[fx("sparkles", "_")])
scene("twist", I, "娘が毎週\n遊ぶ川。", None, obj="a red toy bucket and a small fishing net left on a grassy riverbank",
      loc="riverside", anim="pop")
scene("twist", I, "あの黒い水が、\n流れ込む\n川だった。", None, reuse=7, loc="riverside", anim="punch", motion="shake",
      before=[fx("speed_lines")], after=[fx("flash")], transition="flash")
scene("twist", I, "まさか…", I, "covering his mouth with one hand, eyes wide", "shocked", shot="close", motion="punch_in",
      before=[fx("speed_lines")])
scene("twist", I, "その夜、\n眠れなかった。", I, "lying in bed under a blanket, staring at the ceiling", "sleepless",
      loc="bedroom", before=[fx("gloom")], after=[fx("rain")])
scene("twist", I, "目を閉じると、\nあの黒い水。", None, reuse=6, loc="factory_back", anim="none", at="edge_left", motion="dutch",
      before=[fx("gloom")])
scene("twist", I, "目を開けると、\n娘の寝顔。", KID, "sleeping peacefully in bed", "peaceful", shot="close", loc="bedroom",
      after=[fx("sparkles", "_")])

# ---- lựa chọn ----
scene("choice", I, "告発すれば、\n仕事を失う。", I, "holding a smartphone with his thumb over the screen", "tense",
      before=[fx("gloom")])
scene("choice", I, "黙っていれば、\n家族は\n暮らせる。", I, "looking at a thick white envelope in his hand", "conflicted")
scene("choice", I, "でも、\n娘の川は…", I, "clenching his teeth with his head down", "anguished", shot="close",
      before=[fx("speed_lines")])
scene("choice", WIFE, "…あなた？", WIFE, "standing with hands clasped in front, looking worried", "worried", loc="genkan")
scene("choice", WIFE, "何か、\n隠してるでしょ", WIFE, "looking straight ahead with a gentle but serious face, both arms down at her sides", "serious",
      shot="close", alt=TALK)
scene("choice", I, "僕は、\n全部話した。", I, "sitting at a table, talking seriously with his hands clasped", "serious",
      alt=TALK)
scene("choice", I, "妻は、\n長い間\n黙っていた。", WIFE, "eyes closed, thinking quietly", "thoughtful", shot="close")
scene("choice", WIFE, "あなたが、\n決めていいよ", WIFE, "smiling softly with both hands clasped in front", "gentle",
      before=[fx("aura", "_", colour="#FFB3D1")])
scene("choice", WIFE, "どっちを\n選んでも、\nついていく", WIFE, "smiling with tears in her eyes", "teary smile", shot="close",
      alt=TALK, after=[fx("sparkles", "_")])

# ---- kết mở, vòng lặp về cảnh đầu ----
scene("ending", I, "テーブルの上に、\n札束と、スマホ。", None, reuse=1, anim="pop", motion="focus")
scene("ending", I, "明日の朝、\n答えを出す。", I, "looking straight ahead with determination", "determined", shot="close",
      before=[fx("rays", "_")])
scene("ending", I, "給料を\n選ぶか、", I, "holding a thick white envelope in one hand", "serious", shot="full")
scene("ending", I, "ぐっすり眠れる\n夜を選ぶか。", I, "holding a smartphone in one hand", "serious", shot="full")
scene("ending", I, "あなたなら、\nどっちを\n選ぶ？", I, "looking straight at the viewer with a serious face", "serious",
      shot="close", motion="punch_in", before=[fx("rays", "_"), fx("aura", "_")])

script = {
    "title": ["会社の秘密を", "知ってしまった"],
    "font": "Noto Sans CJK JP", "font_file": "fonts/NotoSansCJKjp-Black.otf",
    "speakers": {I: "#4FC3F7", BOSS: "#E57373", SENPAI: "#FFB74D", WIFE: "#F48FB1", KID: "#FFD54F"},
    "scenes": scenes,
}
OUT.write_text(json.dumps(script, ensure_ascii=False, indent=1), encoding="utf-8")
shots = {k: sum(1 for s in scenes if s.get("shot") == k) for k in ("full", "half", "close")}
print(f"{len(scenes)} cảnh; shot {shots}; đồ vật {sum(1 for s in scenes if 'object' in s)}; dùng lại "
      f"{sum(1 for s in scenes if not s['characters'] and 'object' not in s)}; alt_pose {sum(1 for s in scenes if 'alt_pose' in s)}; "
      f"hiệu ứng {sum(1 for s in scenes for l in s['layers'] if 'effect' in l)}")
