"""Bước 1: model AI viết script.json từ một chủ đề. Gọi qua steps/llm.py (cổng chuẩn OpenAI, mặc định ShopAIKey):
cần AI_API_KEY, model chọn bằng AI_MODEL_SCRIPT.

  python steps/01_script.py videos/<tên> "chủ đề truyện"
  python steps/01_script.py videos/<tên> prompt.txt          # chủ đề hoặc cả câu chuyện dài, đọc từ file .txt

Quy tắc viết nằm ở config/script_guide.md (gửi nguyên văn cho model). Model được dùng lại nhân vật, bối cảnh có sẵn
hoặc khai thêm (new_characters, new_locations); thứ mới được ghi vào config/characters.json, config/locations.json
để các bước sau sinh ảnh chuẩn, ảnh nền và các video sau dùng lại.
Đã có script.json thì bỏ qua. Kịch bản có tên nhân vật / bối cảnh không khai báo thì không ghi, báo lỗi để chạy lại.
"""
import functools
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

from common import CONFIG, LIBRARY, ROOT, load_json, normalize_script, video_dir
from llm import LLMError, chat, json_reply

MODEL = os.environ.get("AI_MODEL_SCRIPT") or os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
VOICEVOX_VOICES = json.loads((Path(__file__).resolve().parent.parent / "config" / "voicevox_voices.json").read_text(encoding="utf-8"))
# kiểu kể người dùng chọn ở trang Tạo video (SHORTS_VOICE_MODE): một giọng kể chính, hay các nhân vật nói chuyện với nhau
VOICE_MODE = os.environ.get("SHORTS_VOICE_MODE") if os.environ.get("SHORTS_VOICE_MODE") in ("narration", "dialogue") else "narration"
VOICE_MODES = {
    "narration": "Kiểu kể: MỘT GIỌNG KỂ CHÍNH. Phần lớn câu (khoảng 2/3) là lời kể của một giọng (narrator, hoặc nhân vật chính "
                 "tự kể ngôi thứ nhất); các nhân vật khác chỉ nói xen ở câu then chốt (lời thoại trong 「」).",
    "dialogue": "Kiểu kể: NHÂN VẬT NÓI CHUYỆN. Phần lớn câu (khoảng 2/3 trở lên) là lời thoại trực tiếp của các nhân vật nói qua "
                "lại với nhau, speaker là đúng nhân vật đang nói; lời kể (narrator) chỉ để nối cảnh, chuyển thời gian, ngắn. "
                "Cảnh có lời thoại nên có người nói trong khung hình (characters gồm cả speaker).",
}
# kiểu chuyện người dùng chọn ở trang Tạo video (SHORTS_STORY_MODE); "auto" = AI tự chọn theo đề tài như trước
STORY_MODES = {
    "auto": "",
    "twist": (
        "Kiểu chuyện (BẮT BUỘC): BÍ MẬT LỘ DẦN + CÚ LẬT CUỐI (kiểu kênh 「スカッと迷言集」). Kể ngôi thứ nhất (「俺」/「私」), "
        "chuyện đời thường (gia đình, người yêu, bạn thân, đồng nghiệp). Câu 1 là điều bất thường gây tò mò (「母が異様に若すぎる」). "
        "Sự thật lộ ra từng mảnh, mỗi vài câu thêm một manh mối (đồ vật tìm thấy, tin nhắn, một câu nói lạ). Gần cuối tưởng đã "
        "giải quyết xong (làm lành, cười với nhau) rồi CÂU CUỐI lật ngược hoàn toàn bằng một câu thoại lạnh / rợn của nhân vật kia "
        "(「私は一度も親友だと思ったことない」, 「あなたも気をつけなさい」), có thể thêm phản ứng cụt 「…え」, rồi HẾT, không giải "
        "thích. Dùng cảnh màn hình điện thoại (tin nhắn LINE, cuộc gọi nhỡ, hồ sơ app hẹn hò, ảnh cũ) để kể nhanh manh mối. "
        "Tiêu đề: dòng 1 tên loạt ngắn, dòng 2 tên tập 4-8 chữ gây tò mò không lộ cú lật (「若い母の真相」, 「見る目がない」)."),
    "sukatto": (
        "Kiểu chuyện (BẮT BUỘC): SẢNG KHOÁI TRẢ ĐŨA (スカッと). Ngôi thứ nhất, nhân vật chính bị một kẻ xấu (sếp, mẹ chồng, đồng "
        "nghiệp, người yêu cũ, khách hàng vô lý) chèn ép ngày càng quá đáng; khán giả tức thay; rồi lật thế bằng bằng chứng / người "
        "quyền lực / chính lời kẻ đó; kẻ xấu bị trả giá thích đáng; câu cuối gọn, sảng khoái."),
    "touching": (
        "Kiểu chuyện (BẮT BUỘC): CẢM ĐỘNG. Chuyện gia đình / tình thân / tình bạn có hiểu lầm hoặc bí mật hy sinh, lộ ra ở cuối làm "
        "người xem rơi nước mắt; nhịp chậm hơn ở cao trào, câu cuối ấm áp hoặc day dứt."),
    "comedy": (
        "Kiểu chuyện (BẮT BUỘC): HÀI. Tình huống đời thường leo thang vô lý dần, nhân vật có tật / logic lệch, câu chốt bất ngờ "
        "khiến bật cười; nhiều thoại qua lại, nhịp nhanh."),
    "kaigai": (
        "Kiểu video (BẮT BUỘC): SO SÁNH ĐỐI ĐẦU 日本 vs {country_jp} (KHÔNG phải truyện kể về một người), tân bốc Nhật Bản. "
        "Hai nhân vật dẫn là HAI LINH VẬT QUỐC GIA (đầu là bản đồ nước tô cờ, có sẵn trong danh sách nhân vật, KHÔNG khai lại): "
        "\"mascot_jpn\" (日本くん) và \"{mascot}\" ({country_jp}くん); có mặt ở gần hết các cảnh, mỗi cảnh 1-2 linh vật. "
        "Chủ đề so sánh lấy theo đề tài người dùng (xe hơi, đồ điện tử, đồ ăn, an toàn, dịch vụ, đường phố...). "
        "Cấu trúc: cảnh mở là {country_jp}くん thách đấu, tự tin khoe (「{country_jp}の方が上だ！」); rồi 4-6 HIỆP, mỗi hiệp một hạng mục "
        "(giá, độ bền, an toàn, bán lại, dịch vụ hậu mãi, chất lượng...): chữ tượng thanh / lớp chữ lớn ghi tên hiệp "
        "(「第1ラウンド：耐久性」), {country_jp}くん khoe điểm mạnh của mình (cho họ thắng 1 hiệp nhỏ, vd giá rẻ, để có tranh cãi), "
        "日本くん đáp lại bằng một chi tiết / con số cụ thể, {country_jp}くん cứng họng (「ぐぬぬ…」). Có thể xen cảnh minh họa "
        "(xe chạy đường đèo, khách hàng, thợ sửa xe) bằng người thật. Cuối: tỉ số chung cuộc Nhật thắng áp đảo (vd 5-1), "
        "{country_jp}くん cay cú nói một câu chống chế, câu hỏi chia phe cho người xem (「あなたならどっち？」「コメントで教えて」). "
        "Được chê thẳng SẢN PHẨM, HỆ THỐNG, DỊCH VỤ, THÓI QUEN của nước kia; KHÔNG miệt thị con người theo dân tộc (không gán cả "
        "một dân tộc là bẩn, gian, ngu, thấp kém), không từ xúc phạm, không chính trị, chiến tranh, lịch sử, lãnh thổ, lãnh đạo, "
        "người thật. Được nêu tên hãng / mẫu thật (Toyota, Honda, BYD, Hyundai...) khi khen, hoặc khi nói thông tin trung lập / có thật "
        "(giá bán, kích thước, năm ra mắt, đặc điểm); lời chê chung (hay hỏng, bảo hành chậm) thì nói 'xe ○○ nhiều mẫu' chung chung, "
        "không gắn tên một hãng / mẫu cụ thể. Hãng phải đúng nước (Hyundai, Kia là Hàn Quốc; BYD, Geely, Chery là Trung Quốc). Con số chỉ lấy từ đề tài người dùng hoặc "
        "danh sách SỐ LIỆU THẬT (nếu liên quan chủ đề); không có số thì so bằng chi tiết cụ thể, không bịa thống kê. "
        "Lời bằng tiếng Nhật, nhịp nhanh, nhiều thoại qua lại giữa hai linh vật. Tiêu đề: dòng 1 「日本 vs {country_jp}」, "
        "dòng 2 nêu hạng mục (「車対決、勝つのはどっち？」). "
        "HÌNH ẢNH (KHÔNG làm tranh tĩnh): (1) cảnh hai linh vật đối đáp là cảnh GHÉP LỚP thường: lớp ảnh cutouts/ của linh vật, "
        "anim sôi động (jump, punch, shake_no, hop, lean_in, spin_in, sink khi thua), hiệu ứng (speed_lines, anger, sweat, "
        "shock_lines, sparkles), chữ tượng thanh to (「ドヤッ」「ぐぬぬ」「ガーン」); (2) mỗi hiệp có MỘT cảnh thẻ so sánh: thêm "
        "\"compare\": {{\"round\": \"第1ラウンド：耐久性\", \"label\": \"平均使用年数\", \"japan\": \"20年\", \"other\": \"8年\", "
        "\"winner\": \"japan\" | \"other\" | \"draw\", \"score\": [tỉ số Nhật, tỉ số nước kia sau hiệp này]}} (code tự vẽ thẻ ở "
        "giữa khung; trong cảnh đó hai linh vật \"size\": \"medium\" ở floor_left / floor_right); cảnh kết có \"compare\" "
        "\"round\": \"最終結果\" với tỉ số chung cuộc; (3) cảnh minh họa (thợ sửa xe, khách hàng...) cũng là cảnh GHÉP LỚP có "
        "nhân vật cắt rời và anim (KHÔNG dùng \"full\", \"motion_level\", clip); (4) 3-5 cảnh ẢNH THẬT làm dẫn chứng (ảnh chụp tải từ Pexels, code đặt trong khung ảnh giữa "
        "khung hình): thêm \"photo\": {{\"query\": \"2-5 từ khóa tiếng Anh tả đúng ảnh cần (vd old japanese car mountain road, "
        "car repair shop japan, used car dealership)\", \"caption\": \"chú thích tiếng Nhật ngắn dưới ảnh, tối đa 12 ký tự\"}}; "
        "cảnh ảnh thật là cảnh ghép lớp có 1-2 linh vật đứng hai bên chỉ vào ảnh (không phải cảnh clip, không cùng cảnh "
        "\"compare\"); từ khóa tả đúng ảnh cần, ĐƯỢC ghi hãng + mẫu khi cảnh đó khen hoặc nêu thông tin trung lập về đúng mẫu đó "
        "(vd \"toyota corolla\", \"hyundai tucson\", \"byd electric car\"), cảnh chê chung thì từ khóa chung (\"car breakdown "
        "road\"); không người nổi tiếng, không cờ, không bản đồ. "
        "NHỊP NHANH, KHÔNG KHOẢNG LẶNG: MỌI cảnh đều có \"text\" (kể cả cảnh thẻ so sánh: một câu đọc to kết quả hiệp, vd "
        "「耐久性は日本20年、中国8年！」; cảnh ảnh thật: câu dẫn chứng). Mỗi câu 6-16 ký tự, hai linh vật nói chen nhau dồn dập. "
        "TIẾNG HIỆU ỨNG: cảnh thẻ so sánh, cú khoe, cú cứng họng ghi \"sfx\": [tên], chọn trong: jan, don, dodon, correct, wrong, "
        "fanfare, drumroll, gaan, bikkuri, chiin, punch, boyon, hyu, dash, chanchan."),
    # "Tương phản" ngẫu nhiên: chuyện đời thường chia hai phe (CONTROVERSY ghép vào ở NEW_STORY)
    "contrast": "",
}
STORY_MODE = os.environ.get("SHORTS_STORY_MODE") if os.environ.get("SHORTS_STORY_MODE") in STORY_MODES else "auto"
# "Nhật Bản vs nước khác": nước đem so (ISO3, steps/compare_facts.py COUNTRIES), trang web ghi vào meta.json
from compare_facts import COUNTRIES, fetch as fetch_facts   # noqa: E402
COUNTRY = os.environ.get("SHORTS_COUNTRY") if os.environ.get("SHORTS_COUNTRY") in COUNTRIES else "CHN"
STORY_MODES["kaigai"] = STORY_MODES["kaigai"].format(country=COUNTRIES[COUNTRY][0], country_jp=COUNTRIES[COUNTRY][1],
                                                     mascot=f"mascot_{COUNTRY.lower()}")
# cách dựng người dùng chọn ở trang Tạo video (SHORTS_STYLE): "classic" như cũ, "new" như kênh スカッと迷言集 (video mẫu 5, 6)
STYLE = "new" if os.environ.get("SHORTS_STYLE") == "new" else "classic"
# móc câu 1-3 giây đầu, mọi cách dựng (người dùng yêu cầu 2026-10-11): người xem quyết định lướt qua trong 1-2 giây
HOOK = (
    "MÓC CÂU 3 GIÂY ĐẦU (BẮT BUỘC, quan trọng nhất): cảnh 1-2 có \"beat\": \"hook\". Cảnh 1 là câu MẠNH NHẤT của cả video, "
    "tối đa 12 ký tự, đọc dưới 1,5 giây, KHÔNG chào hỏi, không giới thiệu nhân vật, không bối cảnh, không 「今日は」「実は」 mở đầu. "
    "Chọn MỘT kiểu, đổi kiểu giữa các video: (a) nhảy tới khoảnh khắc căng nhất của truyện rồi cảnh sau quay lại 「3日前――」; "
    "(b) câu thoại sốc giữa trận cãi 「離婚して」「あなた誰？」; (c) sự thật lạ khó tin 「母は私より若く見える」; "
    "(d) con số / chi tiết cụ thể gây tò mò 「財布に知らない女の写真」; (e) câu hỏi chọn phe 「これ、悪いのは誰？」. "
    "Cảnh 2 hé thêm một chi tiết làm câu hỏi lớn hơn, chưa trả lời. Tiêu đề và cảnh 1 không nói trùng nhau. "
    "Hình cảnh 1: cận mặt (\"shot\": \"close\"), cảm xúc mạnh (sốc, giận, khóc, cười nhếch mép), không cảnh trống.")
# cách dựng mới: chuyện chia hai phe để người xem tranh luận ở phần bình luận (người dùng yêu cầu 2026-10-11)
CONTROVERSY = (
    "TƯƠNG PHẢN, GÂY TRANH CÃI (BẮT BUỘC): giữ đúng đề tài, nhân vật, tình huống người dùng nhập (không đổi sang chuyện "
    "khác), biến nó thành MỘT câu hỏi đạo đức đời thường mà người xem sẽ chia hai phe "
    "(「どっちが悪い？」): hai nhân vật đối lập rõ (đẹp / giản dị, giàu / nghèo, trẻ / già, tự do / truyền thống, thẳng thắn / "
    "nhẫn nhịn), MỖI BÊN đều có lý do nghe được và một điểm đáng trách. Không để một bên là phản diện thuần túy, không giảng ai "
    "đúng ai sai. Cú lật cuối làm người xem đổi phe hoặc thấy cả hai đều sai một phần. Tiêu đề dòng 2 nêu thẳng thế giằng co "
    "(「妻が正しい？夫が正しい？」 hoặc một câu khẳng định gây tranh luận). Câu cuối (hoặc câu ngay trước câu lật) là câu hỏi ngắn "
    "ném cho người xem, do người kể nói: 「あなたなら、どっちの味方？」, 「これって私が悪いの？」. "
    "Đề tài tranh cãi chỉ là chuyện đời thường (tiền bạc, chia việc nhà, quà cáp, bạn khác giới, mẹ chồng, hàng xóm, đồng "
    "nghiệp, tiền lương, ngoại hình); KHÔNG đụng chính trị, tôn giáo, dân tộc, giới tính theo kiểu miệt thị, người thật, "
    "bạo lực hay xúc phạm một nhóm người.")
# cách dựng mới: kiểu chuyện người dùng chọn, "AI tự chọn" = bí mật + cú lật; luôn gây tranh cãi, trừ 海外の反応 (có luật riêng)
# 3 ô trên trang Tạo video: "Tĩnh có anime" = twist; "Tương phản" = contrast (twist + CONTROVERSY) hoặc kaigai (so với nước khác)
NEW_STORY_MODE = STORY_MODE if STORY_MODE != "auto" else "twist"
NEW_STORY = (STORY_MODES["twist"] + " " + CONTROVERSY if NEW_STORY_MODE == "contrast" else STORY_MODES[NEW_STORY_MODE])
NEW_STYLE = (
    "CÁCH DỰNG MỚI (BẮT BUỘC): mỗi cảnh là một TRANH VẼ CẢ CẢNH có 1-2 nhân vật ở cự ly gần (không ghép nhân vật cắt rời): "
    "\"characters\" tối đa 2 người, \"action\" tả rõ họ đang làm gì ở đâu (vd \"sitting on the sofa looking at a smartphone\"), "
    "\"shot\" chủ yếu close / half; \"layers\" chỉ gồm chữ tượng thanh, sticker, hiệu ứng (KHÔNG có lớp ảnh cutouts/). "
    "Nhịp nhanh: 35-50 cảnh, mỗi cảnh một câu ngắn. "
    "Phụ nữ trẻ đẹp (mẹ trẻ đẹp nổi tiếng trong xóm, người mẫu, siêu mẫu, idol, tiếp viên, cô hàng xóm quyến rũ, người đẹp "
    "bí ẩn) là nhân vật MỚI có \"art\": \"anime\" và \"voice\": \"young_woman\" hoặc \"woman\", luôn từ 20 tuổi trở lên, "
    "không giới hạn số lượng; \"prompt\" tả trang phục gợi cảm mà lịch sự, tôn dáng (vd pink wrap blouse with a V neckline, "
    "fitted white midi skirt, thin silver necklace), không hở hang, không đồ lót. Những người khác giữ nét Irasutoya. "
    + NEW_STORY)
# cách dựng mới: nữ nét anime vẽ thật đẹp, gợi cảm nhưng kín đáo (thêm vào mô tả cố định của nhân vật khi tạo)
GLAM = ("gorgeous glamorous adult woman, sexy and elegant, attractive curvy figure, beautiful detailed face, "
        "long eyelashes, glossy hair, fashionable outfit, tasteful, fully clothed")
STORY_MODE = NEW_STORY_MODE if STYLE == "new" else STORY_MODE
RECENT = 6             # số video gần nhất đưa vào phần "Gần đây đã dùng"

# giọng edge-tts cho nhân vật mới, theo loại giọng model chọn
VOICES = {
    "man": ("ja-JP-KeitaNeural", "+0%", "-5Hz"),
    "young_man": ("ja-JP-KeitaNeural", "+5%", "+5Hz"),
    "old_man": ("ja-JP-KeitaNeural", "-8%", "-20Hz"),
    "boy": ("ja-JP-KeitaNeural", "+10%", "+30Hz"),
    "woman": ("ja-JP-NanamiNeural", "+0%", "-5Hz"),
    "young_woman": ("ja-JP-NanamiNeural", "+5%", "+10Hz"),
    "old_woman": ("ja-JP-NanamiNeural", "-8%", "-20Hz"),
    "girl": ("ja-JP-NanamiNeural", "+10%", "+40Hz"),
}
BACKGROUND = "irasutoya_style, background illustration of {desc}, flat colors, simple shapes, no people, no text"
NAME = re.compile(r"[a-z][a-z0-9_]{1,39}")

PROMPT = """Viết kịch bản cho một video TikTok dọc, kể truyện ngắn bằng tiếng Nhật.

Đề tài người dùng nhập (có thể là một câu ngắn hoặc cả câu chuyện):
<<<
{topic}
>>>

Thể loại, góc kể, cấu trúc, độ dài, độ đa dạng: theo quy tắc ở cuối yêu cầu này (bắt buộc).

Nhân vật có sẵn ("narrator" chỉ là giọng kể, không xuất hiện trong ảnh). Dùng lại khi hợp; cần ai khác thì khai trong "new_characters":
{characters}

Bối cảnh có sẵn. Dùng lại khi hợp; cần nơi khác hoặc thời điểm, thời tiết khác thì khai trong "new_locations":
{locations}

Gần đây đã dùng (các video trước, tránh lặp lại để video này trông khác):
{recent}

Sticker có sẵn (đường dẫn dùng trong layers): {stickers}

Giọng đọc (VOICEVOX). Chọn cho MỖI speaker (kể cả "narrator") một giọng trong danh sách sau, hợp giới tính, tuổi, tính cách;
hai nhân vật khác nhau không dùng chung giọng; nhân vật đã có ở video trước thì giữ giọng hợp với họ:
{voices}
Mỗi cảnh ghi "tone" (giọng điệu của câu): normal, happy, excited, sad, crying, angry, whisper, scared, calm, narration
(narration cho lời kể đều đều). Chọn theo cảm xúc thật của câu, không để mọi câu là normal.
{voice_mode}
{story_mode}

Trả về đúng một đối tượng JSON, không kèm chữ nào khác, theo schema:
{{
  "title": ["dòng tiêu đề 1", "dòng tiêu đề 2"],
  "genre": "thể loại đã chọn (mục 0 quy tắc)",
  "font": "Noto Sans CJK JP", "font_file": "fonts/NotoSansCJKjp-Black.otf",
  "new_characters": {{"<tên_mới>": {{"prompt": "ngoại hình tiếng Anh", "voice": "man|woman|old_man|old_woman|boy|girl|young_man|young_woman", "colour": "#RRGGBB", "art": "irasutoya | anime"}}}},
  "new_locations": {{"<tên_mới>": "mô tả tiếng Anh: nơi chốn, thời gian trong ngày, thời tiết, mùa, đồ vật đặc trưng"}},
  "speakers": {{"<tên speaker>": "<màu hex lấy từ colour của nhân vật>"}},
  "voices": {{"narrator": "<tên giọng VOICEVOX>", "<tên speaker>": "<tên giọng VOICEVOX>"}},
  "scenes": [{{
    "id": 1, "beat": "hook | setup | rise1 | rise2 | rise3 | twist | ending",
    "text": "câu thoại tiếng Nhật", "speaker": "narrator", "tone": "narration",
    "characters": ["father"], "action": "tiếng Anh, tư thế và hành động, gồm cả đồ vật đang cầm (vd holding a glass beer mug)",
    "emotion": "tiếng Anh, cụ thể và mạnh (smug, furious, shocked, creepy smile, embarrassed...), có thể thêm góc mặt (head tilted, three-quarter view)",
    "object": null,
    "shot": "full | half | close",
    "location": "dining_room", "filter": "none",
    "alt_pose": null,
    "punchline": false,
    "focus": null,
    "phone": null,
    "layers": [ ... ]
  }}]
}}
"new_characters" và "new_locations" để {{}} nếu không cần thêm.
"art" của nhân vật mới: mặc định "irasutoya"; "anime" khi đề tài yêu cầu nhân vật đó vẽ kiểu anime (アニメ風, anime) hoặc khi
một nhân vật cần nổi bật hẳn (người đẹp bí ẩn, nhân vật "khác thường"): tối đa 1 nhân vật anime mỗi video. Nhân vật anime
cần nét riêng thì tạo nhân vật MỚI (tên mới), không dùng lại nhân vật cũ.

Quy tắc kỹ thuật cho layers (thứ tự là thứ tự vẽ). Mỗi lớp là MỘT trong 3 dạng, đúng tên khóa như sau
(khóa ảnh luôn là "image", không dùng "src", "file", "path" cho ảnh; "path" chỉ dùng cho đường đi):
  ảnh:     {{"id": "father", "image": "cutouts/001.png"}}            có thể thêm at, size, anim, path, over, start, duration
  chữ:     {{"word": "ドン", "size": 70, "vertical": true, "at": "top_right"}}
  hiệu ứng: {{"effect": "rays", "on": "father"}}
  chữ rải quanh đầu: {{"effect": "murmur", "text": "ニヤ", "on": "father"}}  (5-7 chữ tượng thanh nhỏ nghiêng quanh mặt,
    nhấp nháy: 「ニヤ」 cười đểu, 「ドキッ」 giật mình / rung động, 「イライラ」 bực, 「ソワソワ」 bồn chồn, 「ジー」 nhìn chằm chằm,
    「ガーン」 sốc, 「ルンルン」 vui; cảnh tranh cả cảnh thì bỏ "on"); ~1/6 số cảnh, ở câu cảm xúc mạnh của một người
- Ảnh chủ thể: "cutouts/NNN.png" nếu cảnh có một nhân vật hoặc chỉ có đồ vật, "cutouts/NNN_<tên>.png" nếu nhiều nhân vật
  (NNN là id 3 chữ số, <tên> là tên nhân vật ĐẦY ĐỦ đúng như trong "characters", vd "cutouts/012_mascot_chn.png", không viết
  tắt). MỖI nhân vật MỘT lớp riêng, không gộp nhiều nhân vật vào một lớp. Đặt "id" bằng tên nhân vật (hoặc "objects").
- "text" luôn là chuỗi; cảnh không lời (thẻ so sánh, clip minh họa) ghi "" (không null).
- Sticker: {{"image": "<đường dẫn trong danh sách sticker trên>", "at": "father.beside_right", "size": "tiny"}}.
- at / path: center, left, right, top, top_left, top_right, bottom, floor, floor_left, floor_right,
  off_left, off_right, off_top, off_bottom; hoặc "<id>.<điểm neo>" với điểm neo: center, top, bottom, left, right,
  above, head, beside_left, beside_right, hand_left, hand_right.
- size: tiny, small, medium, large, huge, hoặc số (chiều cao so với khung hình).
- anim, motion, transition: để trống thì bước dựng tự chọn cho đa dạng; chỉ ghi khi có chủ ý (xem mục 6 quy tắc).
  anim: nod, shake_no, sway, tilt, breathe, shiver, hop, sink, float, punch, spin_in, lean_in, rise, squash, jelly,
  puff, deflate, stretch_up, snap, bounce, jump,
  pulse, approach, recede, exit_left, exit_right, slide_left, slide_right, drop, pop, pop_fade, none.
  Có thể thêm "start", "duration" (giây), "over" cho path.
- phone: cảnh MÀN HÌNH ĐIỆN THOẠI (vẽ bằng code, chữ Nhật rõ) khi câu chuyện nhắc tin nhắn, cuộc gọi nhỡ, thông báo, chặn
  liên lạc, hồ sơ app hẹn hò; ~1/10 số cảnh, chỉ khi hợp. Cảnh phone để "characters": [], layers chỉ chữ / hiệu ứng nếu cần.
  {{"app": "chat", "title": "綾乃", "items": [{{"from": "them", "text": "今から話せる？"}}, {{"from": "me", "text": "無理"}}]}}
  {{"app": "calls", "items": ["綾乃  不在着信(3)", "綾乃  不在着信"]}}       {{"app": "notify", "items": [{{"app": "LINE", "text": "綾乃: どこにいるの？"}}]}}
  {{"app": "dialog", "dialog_title": "綾乃をブロックしますか？", "message": "…", "buttons": ["キャンセル", "ブロック"], "items": [...]}}
  {{"app": "profile", "title": "マッチングアプリ", "items": ["けいすけ 28", "大阪府", "IT関連"]}}
- punchline: true cho câu chốt (cảnh riêng, 3-6 câu mỗi video; xem mục 6 quy tắc).
- focus: {{"on": "<id nhân vật>" hoặc "<id>.hand_right" hoặc [x, y], "at": 0.45, "zoom": 1.45}} khi lời nhắc tới một thứ
  trong khung (đồng hồ, điện thoại, tấm ảnh, người nghe sững lại): nửa đầu toàn cảnh, rồi máy đẩy vào điểm đó. ~1/6 số cảnh.
- motion: impact, build, punch_in, focus, dutch, drift, dolly_left, dolly_right, tilt_up, tilt_down, zoom_in, zoom_out, pan_left,
  pan_right, shake, none. transition: cut, fade, push_left, push_right, push_up, whip, zoom, flash, wipe, iris.
  filter: none hoặc sepia.

Quy tắc viết kịch bản (bắt buộc theo, kể cả thể loại, nhân vật, bối cảnh, shot, đồ vật, bố cục, sticker, chuyển động, độ đa dạng):

{guide}"""


def recent_usage(current):
    """Tóm tắt các video gần nhất đã dùng thể loại, nhân vật, bối cảnh nào, để model tránh lặp."""
    scripts = sorted((p for p in (ROOT / "videos").glob("*/script.json") if p.parent != current),
                     key=lambda p: p.stat().st_mtime, reverse=True)[:RECENT]
    if not scripts:
        return "(chưa có video nào)"
    genres, chars, locs, emotions = Counter(), Counter(), Counter(), Counter()
    titles = []
    for p in scripts:
        try:
            s = load_json(p)
        except ValueError:
            continue
        titles.append(" ".join(s.get("title", [])))
        genres[s.get("genre", "cảm động gia đình")] += 1
        for scene in s.get("scenes", []):
            chars.update(scene.get("characters", []))
            locs[scene.get("location", "")] += 1
            emotions[scene.get("emotion", "")] += 1
    top = lambda c, n: ", ".join(f"{k} ({v})" for k, v in c.most_common(n) if k)   # noqa: E731
    return (f"- Tiêu đề: {' / '.join(titles)}\n- Thể loại: {top(genres, 5)}\n"
            f"- Nhân vật dùng nhiều: {top(chars, 8)}\n- Bối cảnh dùng nhiều (số cảnh): {top(locs, 10)}\n"
            f"- Cảm xúc dùng nhiều: {top(emotions, 8)}")


def add_new(script, characters, locations, raw=None):
    """Ghi nhân vật, bối cảnh mới model khai vào config/. Tên trùng thứ có sẵn thì giữ bản có sẵn. Trả về danh sách đã thêm."""
    added = []
    lock = CONFIG / ".config.lock"
    for _ in range(50):                         # nhiều người cùng tạo video: lần lượt từng người sửa file
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL)
            break
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 60:
                lock.unlink(missing_ok=True)
            time.sleep(0.2)
    else:
        sys.exit("config/ đang bị khóa quá lâu, thử lại.")
    try:
        characters.update(load_json(CONFIG / "characters.json"))     # đọc lại: có thể vừa có người thêm
        locations.update(load_json(CONFIG / "locations.json"))
        for name, spec in (raw or {}).items():          # nhân vật code tạo sẵn (linh vật quốc gia), ghi nguyên mục
            if name not in characters:
                characters[name] = spec
                added.append(f"nhân vật {name}")
        for name, spec in (script.get("new_characters") or {}).items():
            if name in characters or not NAME.fullmatch(name) or not isinstance(spec, dict) or not spec.get("prompt"):
                continue
            engine, rate, pitch = VOICES.get(spec.get("voice"), VOICES["woman"])
            colour = spec.get("colour") if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(spec.get("colour"))) else "#81C784"
            characters[name] = {"prompt": spec["prompt"].strip(), "lora": None,
                                "voice": {"engine": "edge", "name": engine, "rate": rate, "pitch": pitch}, "colour": colour}
            if spec.get("art") == "anime":                 # vẽ kiểu anime, không qua LoRA Irasutoya (tools/make_jobs.py)
                characters[name]["art"] = "anime"
                if STYLE == "new" and spec.get("voice") in ("woman", "young_woman"):   # chỉ cách dựng mới, chỉ nữ người lớn
                    characters[name]["prompt"] = f"{GLAM}, {characters[name]['prompt']}"
            added.append(f"nhân vật {name}")
        for name, desc in (script.get("new_locations") or {}).items():
            if name in locations or not NAME.fullmatch(name) or not isinstance(desc, str) or not desc.strip():
                continue
            desc = re.sub(r"^\s*(irasutoya_style,\s*)?(background illustration of\s*)?", "", desc.strip())
            locations[name] = BACKGROUND.format(desc=desc.rstrip(". "))
            added.append(f"bối cảnh {name}")
        if added:
            for path, data in ((CONFIG / "characters.json", characters), (CONFIG / "locations.json", locations)):
                tmp = path.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp.replace(path)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)
    return added


def mascots():
    """Mục characters.json của hai linh vật (Nhật + nước đem so); vẽ ảnh đầu nếu chưa có."""
    sys.path.insert(0, str(ROOT / "tools"))
    from country_mascot import ensure
    found = ensure(["JPN", COUNTRY])
    for spec in found.values():
        engine, rate, pitch = VOICES.get(spec.pop("voice_type"), VOICES["man"])
        spec["voice"] = {"engine": "edge", "name": engine, "rate": rate, "pitch": pitch}
    return found


BRIEF = """Bạn là biên kịch TikTok Nhật. Từ ĐỀ TÀI người dùng nhập dưới đây, viết DÀN Ý ngắn (tiếng Việt, câu mẫu tiếng Nhật)
cho một video {seconds} theo đúng các quy tắc bên dưới. Giữ nguyên nhân vật, tình huống, chi tiết người dùng đã viết; chỉ bổ
sung chỗ còn thiếu và sắp lại cho có móc câu và tương phản. Không viết kịch bản đầy đủ.

ĐỀ TÀI:
<<<
{topic}
>>>

QUY TẮC:
{rules}

Trả về đúng các mục sau, mỗi mục 1-3 dòng:
1. Hai phe / hai bên đối lập (ai, đứng ở đâu, lý lẽ của mỗi bên, điểm đáng trách của mỗi bên)
2. Câu hỏi tranh cãi cho người xem (tiếng Nhật)
3. Kiểu móc câu chọn (a-e) và câu cảnh 1 (tiếng Nhật, tối đa 12 ký tự), câu cảnh 2
4. Các nấc diễn biến (3-4 nấc, mỗi nấc một chi tiết / con số mới)
5. Twist giả và twist thật
6. Câu kết (tiếng Nhật)
7. Tiêu đề 2 dòng (tiếng Nhật)"""


def brief(video, topic):
    """"Tương phản" (ngẫu nhiên / Nhật vs nước khác): AI viết dàn ý từ đề tài người dùng theo quy tắc móc câu + tương phản,
    rồi mới viết kịch bản từ đề tài + dàn ý. Lưu work/brief.md (chạy lại thì dùng lại)."""
    if STORY_MODE not in ("contrast", "kaigai"):
        return topic
    path = video / "work" / "brief.md"
    if not path.exists():
        rules = (NEW_STORY if STYLE == "new" else STORY_MODES[STORY_MODE]) + " " + HOOK + facts_note()
        print(f"Viết dàn ý tương phản bằng {MODEL}...", flush=True)
        try:
            text = chat(BRIEF.format(topic=topic, rules=rules, seconds="70-90 giây"), MODEL, max_tokens=4000).strip()
        except LLMError as e:
            print(f"  không viết được dàn ý ({e}), viết kịch bản thẳng từ đề tài", flush=True)
            return topic
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"  dàn ý: {path}", flush=True)
    return (f"{topic}\n\n--- DÀN Ý ĐÃ CHỈNH THEO QUY TẮC (bám theo dàn ý này, giữ đúng đề tài ở trên) ---\n"
            + path.read_text(encoding="utf-8"))


KAIGAI_BGM = "hageshii/darkmatter.mp3"  # nhạc đối đầu kịch tính cho video Tương phản
KAIGAI_VOICE_SPEED = 1.35               # VOICEVOX speedScale cho video so sánh (mặc định [voice] voicevox_speed 1.2)


def fix_subject_layers(script):
    """Sửa ngay khi viết lớp ảnh chủ thể model hay viết lệch (video 045): tên viết tắt (cutouts/047_chn.png), nhiều nhân vật
    gộp một lớp (cutouts/006_mascot_jpn_mascot_chn.png). Đổi về đúng tên file make_jobs.py sẽ sinh. Trả về danh sách thay đổi."""
    changes = []
    for scene in script.get("scenes", []):
        names = scene.get("characters") or []
        if scene.get("full") or scene.get("phone") or not names:
            continue
        sid = f"{scene['id']:03d}"
        expected = {n: f"cutouts/{sid}.png" if len(names) == 1 else f"cutouts/{sid}_{n}.png" for n in names}
        layers = scene.get("layers") or []
        cut = [x for x in layers if str(x.get("image", "")).startswith("cutouts/")]
        if len(names) > 1 and len(cut) == 1 and cut[0]["image"] not in expected.values():   # gộp nhiều người một lớp
            k = layers.index(cut[0])
            spots = ["floor_left", "floor_right"] + ["floor"] * len(names)
            layers[k:k + 1] = [{**{a: b for a, b in cut[0].items() if a not in ("id", "image", "at", "path")},
                                "id": n, "image": expected[n], "at": spots[i]} for i, n in enumerate(names)]
            changes.append(f"cảnh {scene['id']}: tách lớp gộp {cut[0]['image']} thành {len(names)} lớp")
            continue
        for layer in cut:
            if layer["image"] in expected.values():
                continue
            tail = Path(layer["image"]).stem[4:]
            match = [n for n in names if n == layer.get("id")] or [n for n in names if tail and n.endswith(tail)]
            if len(match) == 1:
                changes.append(f"cảnh {scene['id']}: {layer['image']} -> {expected[match[0]]}")
                layer.update(image=expected[match[0]], id=match[0])
    return changes


@functools.lru_cache(maxsize=1)                  # dàn ý và kịch bản dùng chung một lần lấy số liệu
def facts_note():
    """Kiểu "Nhật Bản vs nước khác": số liệu thật (World Bank) Nhật hơn nước kia, để AI tân bốc Nhật bằng số đúng."""
    if STORY_MODE != "kaigai":
        return ""
    try:
        rows = [r for r in fetch_facts(COUNTRY) if r["japan_better"]]
    except Exception as e:                        # noqa: BLE001  (mạng lỗi: vẫn viết, chỉ không có số)
        print(f"  không lấy được số liệu ({e}), viết không kèm số", flush=True)
        return ""
    print(f"  số liệu Nhật hơn {COUNTRIES[COUNTRY][0]}: {len(rows)} chỉ số (World Bank)", flush=True)
    if not rows:
        return ""
    jp = COUNTRIES[COUNTRY][1]
    lines = NL.join(f"- {r['name']}: 日本 {r['japan']:g}{r['unit']}（{r['year_japan']}年） / {jp} {r['other']:g}{r['unit']}"
                    f"（{r['year_other']}年）" for r in rows)
    return (NL * 2 + "SỐ LIỆU THẬT (World Bank, cấp quốc gia) dùng để tân bốc Nhật Bản, CHỈ khi liên quan chủ đề so sánh (chủ đề là xe hơi thì chỉ dùng số an toàn giao thông, ô nhiễm; không liên quan thì bỏ qua). Đưa tối đa 3-5 con số trong danh sách này vào lời kể / thoại "
            "đúng chỗ cú sốc tương ứng (vd nói về an toàn thì dùng tỉ lệ giết người), ghi năm khi cần, làm tròn dễ đọc. "
            "CHỈ dùng số trong danh sách, không tự bịa số khác. Có thể thêm 1 cảnh bảng so sánh 2 cột bằng cảnh màn hình "
            "điện thoại hoặc chữ to." + NL + lines)


NL = chr(10)


def main():
    video = video_dir()
    if len(sys.argv) < 3:
        sys.exit('Dùng: python steps/01_script.py videos/<tên> "chủ đề truyện"')
    out = video / "script.json"
    if out.exists():
        return print("Đã có script.json, bỏ qua.")

    topic = sys.argv[2]
    if topic.endswith(".txt") and Path(topic).is_file():   # trang web ghi đề tài vào file: dài bao nhiêu cũng được
        topic = Path(topic).read_text(encoding="utf-8").strip()
    characters = load_json(CONFIG / "characters.json")
    locations = load_json(CONFIG / "locations.json")
    if STORY_MODE == "kaigai":                      # linh vật 日本くん và nước đem so: đầu bản đồ + cờ (tools/country_mascot.py)
        for added in add_new({}, characters, locations, raw=mascots()):
            print("  thêm", added, flush=True)
    topic = brief(video, topic)
    stickers = sorted(f"stickers/{p.name}" for p in (LIBRARY / "stickers").glob("*.png"))
    prompt = PROMPT.format(
        topic=topic,
        characters=json.dumps({k: {"prompt": v["prompt"], "colour": v["colour"]} for k, v in characters.items()},
                              ensure_ascii=False, indent=1),
        locations=json.dumps({k: BACKGROUND_DESC.sub("", v).replace(", flat colors, simple shapes, no people, no text", "")
                              for k, v in locations.items()}, ensure_ascii=False, indent=1),
        recent=recent_usage(video),
        stickers=", ".join(stickers) or "(chưa có)",
        voices=chr(10).join(f"- {name}: {v['gender']}, {v['age']}; {v['desc']}" for name, v in VOICEVOX_VOICES["voices"].items()),
        voice_mode=VOICE_MODES[VOICE_MODE],
        story_mode=(NEW_STYLE if STYLE == "new" else STORY_MODES[STORY_MODE]) + " " + HOOK + facts_note(),
        guide=(CONFIG / "script_guide.md").read_text(encoding="utf-8"))   # quy tắc mở rộng, sửa trong file đó

    print(f"Viết kịch bản bằng {MODEL}...", flush=True)
    script, ask = None, prompt
    for attempt in range(1 + LENGTH_RETRIES):
        text = ""
        try:
            text = chat(ask, MODEL, max_tokens=32000)
            reply = json_reply(text)
        except LLMError as e:
            sys.exit(str(e))
        except ValueError:
            if script:                              # lần viết dài thêm hỏng: giữ bản trước
                break
            sys.exit(f"{MODEL} không trả về JSON hợp lệ. Thử lại hoặc chọn model khác. Đầu câu trả lời: {text[:300]}")
        if script is None or fit(length(reply)) < fit(length(script)):   # giữ bản sát khoảng 70-80 giây nhất
            script = reply
        scenes, chars, seconds = length(script)
        print(f"  độ dài: {scenes} cảnh, {chars} ký tự lời, ước khoảng {seconds:.0f} giây", flush=True)
        if not fit((scenes, chars, seconds)):
            break
        if attempt < LENGTH_RETRIES:
            short = seconds < MIN_SECONDS or scenes < MIN_SCENES
            print(f"  {'ngắn' if short else 'dài'} quá, nhờ model viết {'dài thêm' if short else 'gọn lại'}...", flush=True)
            ask = prompt + (LONGER if short else SHORTER).format(scenes=scenes, seconds=round(seconds),
                                                                 script=json.dumps(script, ensure_ascii=False))
    else:
        print(f"  CẢNH BÁO: kịch bản ước {length(script)[2]:.0f} giây, ngoài khoảng {MIN_SECONDS}-{MAX_SECONDS} giây "
              f"sau {LENGTH_RETRIES} lần viết lại.")

    from common import summarize_changes
    for line in summarize_changes(normalize_script(script) + fix_subject_layers(script)):   # gộp các dòng "bỏ null" cho log gọn
        print("  sửa kịch bản:", line)
    added = add_new(script, characters, locations)
    problems = []
    for scene in script["scenes"]:
        problems += [f"cảnh {scene['id']}: không có nhân vật '{n}'" for n in scene.get("characters", []) if n not in characters]
        if scene["location"] not in locations:
            problems.append(f"cảnh {scene['id']}: không có bối cảnh '{scene['location']}'")
        if scene["speaker"] not in characters:
            problems.append(f"cảnh {scene['id']}: speaker '{scene['speaker']}' không có giọng trong characters.json")
    for a in added:
        print("  thêm", a)
    if problems:                                # không ghi kịch bản hỏng: lần chạy sau viết lại
        (video / "work").mkdir(exist_ok=True)
        (video / "work" / "script_rejected.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
        sys.exit("Kịch bản dùng tên chưa khai báo:\n  " + "\n  ".join(problems[:10]) + "\nBấm Chạy tiếp để viết lại.")
    script["voice_mode"] = VOICE_MODE
    script["story_mode"] = STORY_MODE
    script["style"] = STYLE
    if os.environ.get("SHORTS_CONTRAST_MODE") == "1":
        script["bgm"] = KAIGAI_BGM
        script["music_quieter"] = 8.0       # nhạc nền khoảng 21 dB dưới giọng đọc
    if STORY_MODE == "kaigai":
        script["country"] = COUNTRY                 # thẻ so sánh (compare.py) vẽ cờ nước này
        script["bgm"] = KAIGAI_BGM                  # nhạc đối đầu kịch tính cố định
        script["voice_speed"] = KAIGAI_VOICE_SPEED  # đọc nhanh hơn, không tự đọc chậm lại cho đủ độ dài
        for scene in script["scenes"]:
            for key in ("motion_level", "i2v_prompt", "full"):   # không clip AI, không tranh tĩnh: cảnh ghép lớp
                scene.pop(key, None)
            card = scene.get("compare")
            if isinstance(card, dict) and not str(scene.get("text") or "").strip():   # thẻ không lời = khoảng lặng
                label = card.get("label") or str(card.get("round", "")).split("：")[-1]
                scene["text"] = f"{label}、日本{card.get('japan', '')}、{COUNTRIES[COUNTRY][1]}{card.get('other', '')}！"
                scene["speaker"] = scene.get("speaker") or "narrator"
    for scene in script["scenes"]:                  # cách dựng mới: cảnh (trừ màn hình điện thoại) vẽ cả cảnh
        if STYLE == "new" and not scene.get("phone"):
            scene["full"] = True
    script.pop("new_characters", None)
    script.pop("new_locations", None)
    out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    locs = Counter(s["location"] for s in script["scenes"])
    print(f"Đã ghi {out}: {len(script['scenes'])} cảnh, thể loại {script.get('genre', '?')}, "
          f"{len(locs)} bối cảnh ({', '.join(f'{k} {v}' for k, v in locs.most_common())})")


BACKGROUND_DESC = re.compile(r"^irasutoya_style, background illustration of ")

# Độ dài bắt buộc: 70-80 giây (ngắn hoặc dài quá thì nhờ model viết lại). Ước theo tốc độ đọc tiếng Nhật đã tăng 1,2 lần (~8 ký tự/giây) cộng khoảng nghỉ mỗi cảnh.
MIN_SCENES, MIN_SECONDS, MAX_SECONDS, LENGTH_RETRIES = 40, 68, 86, 2
CHARS_PER_SECOND, GAP_PER_SCENE = 8.0, 0.35
LONGER = """

---
Bản kịch bản bạn vừa viết chỉ có {scenes} cảnh (ước {seconds} giây), NGẮN HƠN yêu cầu 70-80 giây (44-52 cảnh).
Viết lại TOÀN BỘ kịch bản cho đủ 44-52 cảnh: giữ cốt truyện, nhân vật, tiêu đề; thêm một nấc truyện, cảnh phản ứng, cảnh chèn
đồ vật, hồi tưởng, nền cảm xúc; tách câu dài thành 2-3 cảnh với hình khác nhau. Mỗi câu vẫn ngắn (6-14 ký tự).
Trả về JSON đầy đủ cùng định dạng như trên. Bản cũ:
{script}"""
SHORTER = """

---
Bản kịch bản bạn vừa viết có {scenes} cảnh (ước {seconds} giây), DÀI HƠN yêu cầu 70-80 giây (44-52 cảnh).
Viết lại TOÀN BỘ kịch bản gọn lại còn 44-52 cảnh: giữ cốt truyện, nhân vật, tiêu đề, twist và câu chốt; bỏ cảnh nối thừa, gộp
cảnh lặp ý. alt_pose chỉ khoảng 1/4 cảnh có nhân vật, khi cần. Mỗi câu vẫn ngắn (6-14 ký tự).
Trả về JSON đầy đủ cùng định dạng như trên. Bản cũ:
{script}"""


def fit(measure):
    """Độ lệch khỏi khoảng cho phép (0 = vừa): giây thiếu / thừa, cộng phạt nếu ít cảnh quá."""
    scenes, _, seconds = measure
    return max(MIN_SECONDS - seconds, 0) + max(seconds - MAX_SECONDS, 0) + max(MIN_SCENES - scenes, 0)


def length(script):
    """(số cảnh, số ký tự lời, số giây ước tính) của kịch bản."""
    scenes = script.get("scenes") or []
    chars = sum(len(str(s.get("text", ""))) for s in scenes)
    return len(scenes), chars, chars / CHARS_PER_SECOND + len(scenes) * GAP_PER_SCENE

if __name__ == "__main__":
    main()
