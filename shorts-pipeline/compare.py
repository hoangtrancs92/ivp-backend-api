"""Thẻ so sánh vẽ bằng code (chữ, số luôn sắc và đúng): cảnh "compare" của video Nhật Bản vs nước khác.

  compare.render(spec, out)      # ghi PNG nền trong suốt; build_video.py chèn thành lớp giữa khung

spec: {"round": "第1ラウンド：耐久性", "label": "平均使用年数", "japan": "20年", "other": "8年",
       "winner": "japan" | "other" | "draw", "score": [2, 1], "country": "CHN"}
  round   dải tiêu đề trên cùng (bỏ trống thì không có)
  label   tên chỉ số, nằm giữa hai cột
  japan / other   giá trị hai bên (chuỗi, đã kèm đơn vị)
  winner  bên thắng: tô vàng, vương miện
  score   tỉ số sau hiệp này (Nhật, nước kia), dòng dưới cùng; cảnh kết ghi tỉ số chung cuộc
  country ISO3 nước đem so (build_video.py điền từ script.json "country")
Thử: python compare.py   (xuất ví dụ vào work/compare_test/)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = str(ROOT / "fonts" / "NotoSansCJKjp-Black.otf")
W, H = 1000, 640
INK, NAVY, GOLD, LOSE = "#3A2A22", "#1F2A4D", "#FFD54A", "#E9ECF2"


def name_jp(iso):
    sys.path.insert(0, str(ROOT / "steps"))
    from compare_facts import COUNTRIES
    return "日本" if iso == "JPN" else COUNTRIES.get(iso, (iso, iso))[1]


def font(size):
    return ImageFont.truetype(FONT, size)


def flag(iso):
    """Cờ đã tải ở library/maps/ (tools/country_mascot.py); chưa có thì tải."""
    sys.path.insert(0, str(ROOT / "tools"))
    from country_mascot import FLAG, INFO, cached
    iso2 = INFO[iso][0]
    return Image.open(cached(f"flag_{iso2}.png", FLAG.format(iso2=iso2))).convert("RGB")


def fit_text(draw, text, size, width):
    """Cỡ chữ lớn nhất <= size mà dòng chữ vừa bề ngang."""
    while size > 18 and draw.textlength(text, font=font(size)) > width:
        size -= 2
    return font(size)


def crown(draw, cx, top, w):
    """Vương miện vàng viền nâu (font chữ không có emoji)."""
    h = w * 0.62
    pts = [(cx - w / 2, top + h), (cx - w / 2, top + h * 0.25), (cx - w / 4, top + h * 0.6), (cx, top),
           (cx + w / 4, top + h * 0.6), (cx + w / 2, top + h * 0.25), (cx + w / 2, top + h)]
    draw.polygon(pts, fill=GOLD, outline=INK, width=6)


def render(spec, out):
    if spec.get("style") == "analysis":
        return render_analysis(spec, out)
    iso = spec.get("country", "CHN")
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, W - 8, H - 8), 44, fill="white", outline=INK, width=10)
    top = 8
    if spec.get("round"):                                       # dải tên hiệp
        d.rounded_rectangle((8, 8, W - 8, 130), 44, fill=NAVY, outline=INK, width=10)
        d.rectangle((18, 80, W - 18, 125), fill=NAVY)
        text = str(spec["round"])
        d.text((W / 2, 70), text, fill="white", font=fit_text(d, text, 64, W - 80), anchor="mm")
        top = 130
    label = str(spec.get("label", ""))
    if label:
        d.text((W / 2, top + 42), label, fill=INK, font=fit_text(d, label, 40, W - 120), anchor="mm")
        top += 70
    winner = spec.get("winner", "japan")
    bottom = H - (110 if spec.get("score") else 40)
    for k, (side, code, value) in enumerate((("japan", "JPN", spec.get("japan", "")), ("other", iso, spec.get("other", "")))):
        x0 = 40 + k * (W - 80) / 2 + (10 if k else 0)
        x1 = x0 + (W - 80) / 2 - 10
        cx = (x0 + x1) / 2
        won = winner == side
        d.rounded_rectangle((x0, top + 20, x1, bottom), 30, fill=GOLD if won else LOSE, outline=INK, width=6)
        f = flag(code).resize((150, 100))
        img.paste(f, (round(cx - 75), round(top + 40)))
        d.rectangle((cx - 75, top + 40, cx + 75, top + 140), outline=INK, width=4)
        d.text((cx, top + 175), name_jp(code), fill=INK, font=font(46), anchor="mm")
        value = str(value)
        d.text((cx, (top + 210 + bottom) / 2), value, fill="#C62828" if won else "#55607A",
               font=fit_text(d, value, 110, x1 - x0 - 40), anchor="mm", stroke_width=4 if won else 0, stroke_fill="white")
        if won:
            crown(d, x0 + 58, top + 36, 64)          # góc trên trái của cột thắng
    if winner == "draw":
        d.text((W / 2, (top + bottom) / 2), "=", fill=INK, font=font(80), anchor="mm")
    if spec.get("score"):
        j, o = spec["score"]
        text = f"日本 {j} - {o} {name_jp(iso)}"
        d.text((W / 2, H - 70), text, fill=INK, font=fit_text(d, text, 58, W - 100), anchor="mm")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def render_analysis(spec, out):
    """Một chỉ số, hai giá trị dễ đọc; không tỉ số hoặc vương miện."""
    img = Image.new("RGBA", (W, H), "#F8FAFC")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, W - 8, H - 8), 32, fill="white", outline="#CBD5E1", width=3)
    label = str(spec.get("label") or spec.get("round") or "比較")
    d.text((W / 2, 72), label, fill=NAVY, font=fit_text(d, label, 54, W - 90), anchor="mm")
    for k, (code, value, colour) in enumerate((("JPN", spec.get("japan", ""), "#B91C1C"),
                                              (spec.get("country", "CHN"), spec.get("other", ""), "#1D4ED8"))):
        cx = W * (0.26 if k == 0 else 0.74)
        d.rounded_rectangle((cx - 214, 150, cx + 214, 498), 24, fill="#F1F5F9")
        img.paste(flag(code).resize((96, 64)), (round(cx - 48), 182))
        d.text((cx, 292), name_jp(code), fill=NAVY, font=font(44), anchor="mm")
        value = str(value)
        d.text((cx, 394), value, fill=colour, font=fit_text(d, value, 104, 388), anchor="mm")
    source = str(spec.get("source") or "")
    if source:
        d.text((W / 2, 560), source, fill="#64748B", font=fit_text(d, source, 30, W - 90), anchor="mm")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def photo_card(src, out, caption=""):
    """Ảnh thật (Pexels) trong khung kiểu polaroid: viền trắng dày, viền nâu mảnh, chú thích tiếng Nhật, nghiêng nhẹ,
    bóng đổ. Ghi PNG nền trong suốt."""
    from PIL import ImageFilter, ImageOps
    photo = ImageOps.fit(Image.open(src).convert("RGB"), (900, 700), Image.LANCZOS, centering=(0.5, 0.45))
    pad, bottom = 36, 150 if caption else 60
    card = Image.new("RGBA", (photo.width + pad * 2, photo.height + pad + bottom), "white")
    card.paste(photo, (pad, pad))
    d = ImageDraw.Draw(card)
    d.rectangle((0, 0, card.width - 1, card.height - 1), outline=INK, width=6)
    d.rectangle((pad, pad, pad + photo.width, pad + photo.height), outline="#D9D2C7", width=3)
    if caption:
        d.text((card.width / 2, pad + photo.height + bottom / 2), caption, fill=INK,
               font=fit_text(d, caption, 64, card.width - 80), anchor="mm")
    card = card.rotate(-3, Image.BICUBIC, expand=True)
    shadow = Image.new("RGBA", (card.width + 40, card.height + 40), (0, 0, 0, 0))
    mask = card.getchannel("A").point(lambda a: 90 if a else 0)
    shadow.paste((40, 30, 20, 255), (24, 28), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    shadow.alpha_composite(card, (8, 8))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    shadow.save(out)
    return out


if __name__ == "__main__":
    test = ROOT / "work" / "compare_test"
    render({"round": "第1ラウンド：耐久性", "label": "平均使用年数", "japan": "20年", "other": "8年", "winner": "japan",
            "score": [1, 0], "country": "CHN"}, test / "a.png")
    render({"round": "第2ラウンド：価格", "japan": "300万円", "other": "180万円", "winner": "other", "score": [1, 1],
            "country": "CHN"}, test / "b.png")
    render({"round": "最終結果", "label": "総合スコア", "japan": "5勝", "other": "1勝", "winner": "japan", "score": [5, 1],
            "country": "KOR"}, test / "c.png")
    print(test)
