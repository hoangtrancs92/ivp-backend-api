"""Bước 4: tách nền ảnh chủ thể của từng cảnh (nhân vật, hoặc đồ vật), cắt sát mép. Chạy trên CPU.

  python steps/04_cutouts.py videos/<tên>

characters/*.png → cutouts/. File đã có thì bỏ qua. Thông số: mục [cutout] trong config/settings.toml.

Ảnh sinh trên nền màu đặc (xanh lá, xem key_prompt) thì tách theo màu: pixel gần màu nền thành trong suốt,
kể cả lỗ kín như lỗ quai cốc; chỗ trắng của nhân vật (áo trắng, bọt bia) giữ nguyên.
Ảnh nền trắng (ảnh cũ) thì dùng model rembg; model này hay khoét thủng chỗ trắng của nhân vật.
"""
import numpy as np
from PIL import Image

from common import SETTINGS, video_dir

CUT = SETTINGS["cutout"]


def key_colour(rgb):
    """Màu nền: trung vị các pixel viền ảnh. None nếu nền là trắng hoặc xám (không phải nền màu đặc)."""
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(float)
    colour = np.median(edge, axis=0)
    return colour if colour.max() - colour.min() > 120 else None     # màu bão hòa, không phải trắng hay xám


def chroma_key(img, colour):
    """Độ đục theo khoảng cách màu tới màu nền: gần thì trong suốt, xa thì đục, ở giữa thì mờ dần (viền mềm).
    Viền mềm được khử màu nền lem vào."""
    rgb = np.asarray(img.convert("RGB")).astype(float)
    distance = np.linalg.norm(rgb - colour, axis=2)
    alpha = np.clip((distance - CUT["key_low"]) / (CUT["key_high"] - CUT["key_low"]), 0, 1)
    soft = (alpha > 0) & (alpha < 1)
    a = alpha[soft][:, None]
    rgb[soft] = np.clip((rgb[soft] - (1 - a) * colour) / a, 0, 255)  # bỏ phần màu nền trộn vào viền
    despill(rgb, colour)
    return Image.fromarray(np.dstack([rgb, alpha * 255]).astype(np.uint8), "RGBA")


def despill(rgb, colour):
    """Khử ánh màu nền trên chỗ sáng và nhạt (thủy tinh, bọt, áo trắng bị nhuộm xanh): kênh màu nền
    không được vượt hai kênh kia quá spill_max. Màu đậm thật (áo len xanh lá) không đủ sáng nên giữ nguyên."""
    if sum(c > 128 for c in colour) != 1:              # nền hồng tím (2 kênh mạnh): không khử ánh theo một kênh
        return
    main = int(np.argmax(colour))                       # kênh của màu nền (xanh lá: G, xanh dương: B)
    others = [c for c in range(3) if c != main]
    ceiling = rgb[..., others].max(axis=2)
    pale = rgb[..., others].min(axis=2) >= CUT["spill_min_bright"]
    excess = rgb[..., main] - ceiling
    fix = pale & (excess > 0) & (excess <= CUT["spill_max"])
    rgb[..., main][fix] = ceiling[fix]


def main():
    video = video_dir()
    session = None
    (video / "cutouts").mkdir(exist_ok=True)
    for path in sorted((video / "characters").glob("*.png")):
        out = video / "cutouts" / path.name
        if out.exists():
            continue
        img = Image.open(path).convert("RGB")
        colour = key_colour(np.asarray(img))
        if colour is not None:
            cut, how = chroma_key(img, colour), "theo màu nền"
        else:
            if session is None:                 # nạp model tách nền chỉ khi có việc
                from rembg import new_session, remove
                session = new_session(CUT["model"])
            cut, how = remove(img, session=session), "rembg"
        cut.crop(cut.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()).save(out)   # cắt sát mép
        print(f"cutouts/{path.name} ({how})")


if __name__ == "__main__":
    main()
