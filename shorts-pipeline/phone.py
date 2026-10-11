"""Màn hình điện thoại vẽ bằng code (chữ tiếng Nhật luôn sắc, đúng; model vẽ ảnh không viết được chữ): cảnh "phone" của kịch bản.

  phone.render(spec, out)       # spec = scene["phone"], ghi PNG nền trong suốt (khung máy + màn hình)

spec: {"app": "chat" | "calls" | "notify" | "dialog" | "profile", "title": "...", "items": [...], ...}
  chat:    items [{"from": "me" | "them", "text": "..."}]          tin nhắn kiểu LINE
  calls:   items ["綾乃  不在着信(3)", ...] hoặc [{"name", "note"}]  lịch sử cuộc gọi nhỡ
  notify:  items [{"app": "LINE", "text": "..."}]                  thông báo màn hình khóa
  dialog:  "message": "...", "buttons": ["キャンセル", "ブロック"]   hộp thoại hệ thống (kèm items nếu có làm nền)
  profile: items ["けいすけ 28", "大阪府", "IT関連", ...]             hồ sơ app hẹn hò / mạng xã hội
Thử: python phone.py   (xuất ví dụ vào work/phone_test/)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FONT = str(ROOT / "fonts" / "NotoSansCJKjp-Black.otf")
PW, PH = 760, 1500                     # cỡ ảnh khung máy (dựng thu về theo "size" của lớp)
SCREEN = (36, 40, PW - 36, PH - 40)    # vùng màn hình trong khung
GREEN, BG_CHAT, GREY = (6, 199, 85), (140, 170, 210), (240, 241, 245)


def font(size):
    return ImageFont.truetype(FONT, size)


def wrap(text, f, width):
    """Xuống dòng theo bề ngang (tiếng Nhật không có dấu cách: cắt theo ký tự)."""
    rows, row = [], ""
    for ch in str(text):
        if f.getlength(row + ch) > width and row:
            rows.append(row)
            row = ""
        row += ch
    return rows + [row] if row else rows


def frame():
    """Khung máy đen bo góc + màn hình; trả về (ảnh, vùng vẽ)."""
    img = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((14, 20, PW - 6, PH - 4), 92, fill=(0, 0, 0, 110))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, PW - 14, PH - 18), 90, fill=(22, 22, 26, 255))
    d.rounded_rectangle(SCREEN, 64, fill=(255, 255, 255, 255))
    d.rounded_rectangle((PW / 2 - 90, 56, PW / 2 + 90, 92), 18, fill=(22, 22, 26, 255))   # tai thỏ
    return img, d


def status_bar(d, light=False):
    c = (255, 255, 255) if light else (30, 30, 30)
    d.text((SCREEN[0] + 60, SCREEN[1] + 22), "21:47", font=font(30), fill=c)
    x, y = SCREEN[2] - 150, SCREEN[1] + 26
    d.text((x, y - 4), "5G", font=font(26), fill=c)
    for k in range(4):                                  # vạch sóng vẽ tay (phông không có ký tự ▮)
        d.rectangle((x + 50 + k * 12, y + 22 - k * 6, x + 58 + k * 12, y + 28), fill=c)


def header(d, title, colour=(255, 255, 255), text=(30, 30, 30), back=True):
    x0, y0, x1, _ = SCREEN
    d.rectangle((x0, y0 + 70, x1, y0 + 170), fill=colour)
    if back:
        d.text((x0 + 26, y0 + 92), "〈", font=font(46), fill=text)
    f = font(40)
    d.text(((x0 + x1 - f.getlength(title)) / 2, y0 + 96), title, font=f, fill=text)
    return y0 + 190


def chat(img, d, spec):
    x0, y0, x1, y1 = SCREEN
    d.rectangle((x0, y0 + 60, x1, y1 - 30), fill=BG_CHAT)
    status_bar(d)
    y = header(d, spec.get("title") or "トーク", (245, 246, 250)) + 10
    f = font(34)
    for item in spec.get("items", [])[:7]:
        me = isinstance(item, dict) and item.get("from") == "me"
        text = item.get("text", "") if isinstance(item, dict) else str(item)
        rows = wrap(text, f, 380)
        w = max(f.getlength(r) for r in rows) + 44
        h = len(rows) * 46 + 30
        if y + h > y1 - 60:
            break
        left = x1 - 30 - w if me else x0 + 110
        if not me:
            d.ellipse((x0 + 24, y, x0 + 94, y + 70), fill=(250, 210, 190))
        d.rounded_rectangle((left, y, left + w, y + h), 30, fill=(140, 230, 110) if me else (255, 255, 255))
        for k, r in enumerate(rows):
            d.text((left + 22, y + 14 + k * 46), r, font=f, fill=(20, 20, 20))
        if me:
            d.text((left - 70, y + h - 34), "既読", font=font(22), fill=(60, 70, 90))
        y += h + 26


def calls(img, d, spec):
    x0, y0, x1, y1 = SCREEN
    status_bar(d)
    y = header(d, spec.get("title") or "履歴")
    for item in spec.get("items", [])[:8]:
        name, note = (item.get("name", ""), item.get("note", "")) if isinstance(item, dict) else (str(item), "")
        if not note and "  " in name:
            name, note = name.split("  ", 1)
        d.ellipse((x0 + 30, y + 22, x0 + 110, y + 102), fill=(220, 225, 235))
        d.text((x0 + 132, y + 22), name, font=font(38), fill=(220, 40, 40) if "不在" in note or not note else (30, 30, 30))
        d.text((x0 + 132, y + 72), note or "不在着信", font=font(26), fill=(120, 120, 130))
        d.ellipse((x1 - 100, y + 40, x1 - 50, y + 90), fill=(6, 170, 80))          # nút gọi (vẽ tay, phông không có 📞)
        d.rounded_rectangle((x1 - 86, y + 58, x1 - 64, y + 72), 6, fill=(255, 255, 255))
        y += 128
        d.line((x0 + 132, y - 4, x1 - 20, y - 4), fill=(225, 225, 230), width=2)
        if y > y1 - 140:
            break


def notify(img, d, spec):
    x0, y0, x1, y1 = SCREEN
    grad = Image.new("RGBA", (x1 - x0, y1 - y0), (40, 50, 90, 255))
    mask = Image.new("L", grad.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, grad.width - 1, grad.height - 1), 64, fill=255)
    img.paste(grad, (x0, y0), mask)
    status_bar(d, light=True)
    f = font(120)
    d.text(((x0 + x1 - f.getlength("21:47")) / 2, y0 + 110), "21:47", font=f, fill=(255, 255, 255))
    y = y0 + 330
    for item in spec.get("items", [])[:5]:
        app, text = (item.get("app", "LINE"), item.get("text", "")) if isinstance(item, dict) else ("LINE", str(item))
        rows = wrap(text, font(30), x1 - x0 - 120)[:2]
        h = 80 + len(rows) * 42
        d.rounded_rectangle((x0 + 24, y, x1 - 24, y + h), 34, fill=(250, 250, 255))
        d.rounded_rectangle((x0 + 46, y + 22, x0 + 90, y + 66), 12, fill=GREEN if app == "LINE" else (90, 120, 230))
        d.text((x0 + 106, y + 24), app, font=font(28), fill=(80, 80, 90))
        d.text((x1 - 110, y + 24), "今", font=font(24), fill=(130, 130, 140))
        for k, r in enumerate(rows):
            d.text((x0 + 50, y + 74 + k * 42), r, font=font(30), fill=(20, 20, 20))
        y += h + 20


def profile(img, d, spec):
    x0, y0, x1, y1 = SCREEN
    status_bar(d)
    y = header(d, spec.get("title") or "プロフィール")
    d.rectangle((x0, y, x1, y + 420), fill=(205, 215, 230))
    d.ellipse(((x0 + x1) / 2 - 120, y + 70, (x0 + x1) / 2 + 120, y + 310), fill=(160, 175, 200))
    d.rectangle(((x0 + x1) / 2 - 170, y + 300, (x0 + x1) / 2 + 170, y + 420), fill=(160, 175, 200))
    y += 450
    items = [str(i) for i in spec.get("items", [])]
    if items:
        d.text((x0 + 40, y), items[0], font=font(50), fill=(20, 20, 20))
        y += 84
    for item in items[1:7]:
        for k, r in enumerate(wrap(("・" if True else "") + item, font(32), x1 - x0 - 80)[:3]):
            d.text((x0 + 40 + (36 if k else 0), y), r, font=font(32), fill=(70, 70, 80))
            y += 50
        y += 4
    d.rounded_rectangle((x0 + 60, y1 - 170, x1 - 60, y1 - 80), 46, fill=(255, 90, 120))
    f = font(34)
    d.text(((x0 + x1 - f.getlength("いいね！")) / 2, y1 - 150), "いいね！", font=f, fill=(255, 255, 255))


def dialog(img, d, spec):
    x0, y0, x1, y1 = SCREEN
    if spec.get("items"):                       # nền: danh sách cuộc gọi / tin nhắn, rồi phủ tối + hộp thoại
        (chat if spec.get("under") == "chat" else calls)(img, d, spec)
    else:
        status_bar(d)
        header(d, spec.get("title") or "設定")
    dim = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(dim).rounded_rectangle(SCREEN, 64, fill=(0, 0, 0, 120))
    img.alpha_composite(dim)
    d = ImageDraw.Draw(img)
    rows = wrap(spec.get("message", ""), font(34), x1 - x0 - 200)
    h = 200 + len(rows) * 50
    top = (y0 + y1 - h) / 2
    d.rounded_rectangle((x0 + 70, top, x1 - 70, top + h), 36, fill=(250, 250, 252))
    title = spec.get("dialog_title") or spec.get("title") or ""
    if title:
        f = font(38)
        d.text(((x0 + x1 - f.getlength(title)) / 2, top + 30), title, font=f, fill=(20, 20, 20))
    for k, r in enumerate(rows):
        f = font(34)
        d.text(((x0 + x1 - f.getlength(r)) / 2, top + 92 + k * 50), r, font=f, fill=(60, 60, 70))
    buttons = spec.get("buttons") or ["キャンセル", "OK"]
    d.line((x0 + 70, top + h - 96, x1 - 70, top + h - 96), fill=(220, 220, 225), width=2)
    bw = (x1 - x0 - 140) / len(buttons)
    for k, b in enumerate(buttons):
        f = font(34)
        cx = x0 + 70 + bw * (k + 0.5)
        d.text((cx - f.getlength(b) / 2, top + h - 72), b, font=f,
               fill=(225, 40, 40) if k == len(buttons) - 1 and len(buttons) > 1 else (40, 110, 230))


KINDS = {"chat": chat, "calls": calls, "notify": notify, "dialog": dialog, "profile": profile}


def render(spec, out):
    img, d = frame()
    KINDS.get(spec.get("app"), chat)(img, d, spec)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


if __name__ == "__main__":
    test = ROOT / "work" / "phone_test"
    render({"app": "chat", "title": "綾乃", "items": [{"from": "them", "text": "今から少し話せる？"},
                                                      {"from": "them", "text": "どうしても話したいことがあるの…"},
                                                      {"from": "me", "text": "もう話すことはない"}]}, test / "chat.png")
    render({"app": "calls", "title": "履歴", "items": ["綾乃  不在着信(3)", "綾乃  不在着信", "お母さん  発信 2分"]}, test / "calls.png")
    render({"app": "notify", "items": [{"app": "LINE", "text": "綾乃: どこにいるの？"}, {"app": "LINE", "text": "綾乃: 返信してほしい…"}]},
           test / "notify.png")
    render({"app": "dialog", "title": "履歴", "dialog_title": "綾乃をブロックしますか？",
            "message": "ブロックすると、トークや通話ができなくなります。", "buttons": ["キャンセル", "ブロック"],
            "items": ["綾乃  不在着信(3)", "綾乃  不在着信"]}, test / "dialog.png")
    render({"app": "profile", "title": "マッチングアプリ", "items": ["けいすけ 28", "大阪府", "IT関連", "関西の大学 卒",
                                                                 "一緒に楽しい時間を過ごせる人と出会いたいです"]}, test / "profile.png")
    print(f"Xuất ví dụ vào {test}")
    sys.exit(0)
