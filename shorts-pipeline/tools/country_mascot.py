"""Linh vật quốc gia (国擬人化): đầu là bản đồ nước đó tô cờ, thân nét Irasutoya. Dùng cho "Nhật Bản vs nước khác".

  python tools/country_mascot.py CHN JPN        # vẽ config/refs/mascot_chn_head.png ... và khai nhân vật vào characters.json

Model ảnh không vẽ đúng hình bản đồ, nên phần đầu vẽ bằng code: đường biên thật (Natural Earth 1:50m) tô ảnh cờ thật
(flagcdn.com), viền nâu như nét Irasutoya. Ảnh này là tham chiếu cho job ảnh chuẩn `ref_mascot_<nước>` trên Kaggle
(tools/make_jobs.py, "head_ref"): model thêm mặt, thân, tay chân. Dữ liệu tải một lần vào library/maps/.
"""
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "library" / "maps"
REFS = ROOT / "config" / "refs"
GEOJSON = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson"
FLAG = "https://flagcdn.com/w640/{iso2}.png"
OUTLINE = "#6B4A3A"
SIZE = 900
# ISO3 -> (ISO2 cho cờ, tên tiếng Nhật của linh vật, quần áo, giọng, màu phụ đề)
INFO = {
    "JPN": ("jp", "日本くん", "navy blue school-style jacket, white shirt, grey trousers", "young_man", "#E53935"),
    "CHN": ("cn", "中国くん", "light blue shirt with two buttons, grey trousers", "man", "#FFB300"),
    "KOR": ("kr", "韓国くん", "white shirt, black trousers", "young_man", "#1E88E5"),
    "USA": ("us", "アメリカくん", "brown leather jacket, blue jeans", "man", "#3949AB"),
    "VNM": ("vn", "ベトナムくん", "white shirt, green trousers", "young_man", "#D32F2F"),
    "IND": ("in", "インドくん", "orange kurta shirt, white trousers", "man", "#FB8C00"),
    "THA": ("th", "タイくん", "light purple shirt, navy trousers", "young_man", "#5E35B1"),
    "PHL": ("ph", "フィリピンくん", "yellow polo shirt, khaki trousers", "young_man", "#FDD835"),
    "IDN": ("id", "インドネシアくん", "batik patterned shirt, black trousers", "young_man", "#C62828"),
    "GBR": ("gb", "イギリスくん", "beige trench coat, grey trousers", "man", "#283593"),
    "FRA": ("fr", "フランスくん", "striped navy and white shirt, black trousers", "man", "#1565C0"),
    "DEU": ("de", "ドイツくん", "grey suit jacket, black trousers", "man", "#424242"),
    "RUS": ("ru", "ロシアくん", "thick brown winter coat, black trousers", "man", "#0D47A1"),
    "BRA": ("br", "ブラジルくん", "yellow football jersey, blue shorts", "young_man", "#43A047"),
}


ENGLISH = {"JPN": "Japan", "CHN": "China", "KOR": "South Korea", "USA": "the United States", "VNM": "Vietnam", "IND": "India",
           "THA": "Thailand", "PHL": "the Philippines", "IDN": "Indonesia", "GBR": "the United Kingdom", "FRA": "France",
           "DEU": "Germany", "RUS": "Russia", "BRA": "Brazil"}   # tên trong prompt vẽ (model vẽ chỉ hiểu tiếng Anh)


def cached(name, url):
    MAPS.mkdir(parents=True, exist_ok=True)
    path = MAPS / name
    if not path.exists():
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def outline(iso):
    """Các vòng đa giác chính của nước (bỏ đảo xa / lãnh thổ hải ngoại), tọa độ (kinh độ, vĩ độ)."""
    data = json.loads(cached("countries_50m.geojson", GEOJSON).read_text(encoding="utf-8"))
    feature = next((f for f in data["features"] if f["properties"].get("ADM0_A3") == iso), None)
    if feature is None:
        sys.exit(f"Không có bản đồ cho {iso}")
    geom = feature["geometry"]
    polygons = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    rings = []
    for poly in polygons:
        ring = [(lon + 360 if iso == "RUS" and lon < 0 else lon, lat) for lon, lat in poly[0]]   # Nga vắt qua kinh tuyến 180
        rings.append(ring)

    def area(r):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]))) / 2

    def centre(r):
        return sum(x for x, _ in r) / len(r), sum(y for _, y in r) / len(r)
    main = max(rings, key=area)
    mx, my = centre(main)
    # giữ đảo đủ lớn và gần phần chính (Nhật: 4 đảo lớn; Mỹ: bỏ Alaska, Hawaii; Pháp: bỏ lãnh thổ hải ngoại)
    return [r for r in rings if area(r) > area(main) * 0.004 and math.dist(centre(r), (mx, my)) < 22]


def head(iso):
    """Ảnh đầu linh vật: bản đồ tô cờ, viền nâu, trên nền trắng. Trả về đường dẫn."""
    rings = outline(iso)
    lats = [lat for r in rings for _, lat in r]
    k = math.cos(math.radians((min(lats) + max(lats)) / 2))          # chiếu đơn giản: co kinh độ theo vĩ độ giữa
    pts = [[(lon * k, -lat) for lon, lat in r] for r in rings]
    xs, ys = [x for r in pts for x, _ in r], [y for r in pts for _, y in r]
    scale = (SIZE - 120) / max(max(xs) - min(xs), max(ys) - min(ys))
    w, h = round((max(xs) - min(xs)) * scale) + 120, round((max(ys) - min(ys)) * scale) + 120
    poly = [[((x - min(xs)) * scale + 60, (y - min(ys)) * scale + 60) for x, y in r] for r in pts]
    mask = Image.new("L", (w, h))
    draw = ImageDraw.Draw(mask)
    for r in poly:
        draw.polygon(r, fill=255)
    iso2 = INFO[iso][0]
    flag = Image.open(io.BytesIO(cached(f"flag_{iso2}.png", FLAG.format(iso2=iso2)).read_bytes())).convert("RGB")
    # hoa văn cờ (mặt trời Nhật, sao Trung Quốc) đặt vào khối chính của bản đồ (bỏ 12% điểm ở mỗi phía: bán đảo, đảo xa),
    # phần ngoài tô màu chính của cờ; kéo cờ theo cả khung chữ nhật thì hoa văn rơi ra ngoài hình nước
    filled = np.argwhere(np.asarray(mask) > 0)
    (y0, x0), (y1, x1) = np.quantile(filled, 0.12, axis=0), np.quantile(filled, 0.88, axis=0)
    box_w, box_h = max(round(x1 - x0), 8), max(round(y1 - y0), 8)
    count, main_colour = max(flag.resize((64, 43)).getcolors(64 * 43))
    if count > 0.55 * 64 * 43:            # cờ có màu nền chính (Nhật, Trung Quốc, Hàn, Việt Nam): hoa văn vào khối chính
        paint = Image.new("RGB", (w, h), main_colour)
        paint.paste(ImageOps.fit(flag, (box_w, box_h), Image.LANCZOS), (round(x0), round(y0)))
    else:                                 # cờ sọc (Mỹ, Pháp, Nga, Đức...): trải cả cờ theo hình nước
        paint = flag.resize((w, h), Image.LANCZOS)
    out = Image.new("RGB", (w, h), "white")
    out.paste(paint, (0, 0), mask)
    line = ImageDraw.Draw(out)
    for r in poly:
        line.line(r + r[:1], fill=OUTLINE, width=9, joint="curve")
    REFS.mkdir(parents=True, exist_ok=True)
    path = REFS / f"mascot_{iso.lower()}_head.png"
    out.save(path)
    return path


def character(iso):
    """Mục characters.json của linh vật (tên mascot_<nước>). Ảnh chuẩn sinh trên Kaggle từ ảnh đầu (head_ref)."""
    _, name_jp, clothes, voice, colour = INFO[iso]
    return f"mascot_{iso.lower()}", {
        "prompt": f"cute country mascot character of {ENGLISH[iso]}, the head is the map shape of {ENGLISH[iso]} painted with its "
                  f"national flag, simple cute face drawn on the map head, small round body, {clothes}, brown shoes",
        "head_ref": f"mascot_{iso.lower()}_head.png", "lora": None, "mascot": iso, "voice_type": voice, "colour": colour}


def ensure(isos):
    """Vẽ đầu (nếu chưa có) và trả về {tên nhân vật: mục characters.json} cho các nước."""
    found = {}
    for iso in isos:
        if not (REFS / f"mascot_{iso.lower()}_head.png").exists():
            head(iso)
        name, spec = character(iso)
        found[name] = spec
    return found


if __name__ == "__main__":
    for iso in sys.argv[1:] or ["JPN", "CHN"]:
        print(head(iso))
