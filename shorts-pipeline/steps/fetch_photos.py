"""Ảnh thật cho cảnh có "photo" trong kịch bản (video so sánh Nhật Bản vs nước khác). Tìm lần lượt: Pixabay, Pexels (nếu có
khóa), rồi Wikimedia Commons (không cần khóa; nhiều ảnh đúng mẫu xe, kể cả xe Trung Quốc mà Pixabay thiếu).

  python steps/fetch_photos.py videos/<tên>

Cảnh ghi "photo": {"query": "old japanese car mountain road", "caption": "20年前の車"}  (query tiếng Anh, caption tùy chọn)
-> photos/NNN.jpg + photos/credits.json (tác giả, link). Ảnh đã có thì giữ; người duyệt bỏ ảnh nào (common.reject_image) thì
lần sau lấy kết quả tìm kiếm kế tiếp (id ảnh bị bỏ ghi ở photos/rejected_ids.json).
Khóa: PIXABAY_API_KEY / PEXELS_API_KEY (trang Cài đặt AI của web), hoặc [keys] pixabay_key / pexels_key trong config.toml.
Giấy phép Pixabay, Pexels: dùng miễn phí cả cho video kiếm tiền, không bắt ghi nguồn. Pixabay cấm dùng link ảnh trực tiếp lâu
dài: ảnh luôn được tải về máy. Wikimedia: chỉ ảnh công cộng / CC0 / CC BY / CC BY-SA (bỏ NC, ND, không rõ giấy phép); ảnh xe ở
đây hầu hết là CC BY-SA, giấy phép này đòi ghi tác giả: tự ghi dòng nguồn vào credits.txt của video (người dùng chọn 2026-10-11:
lấy cả CC BY-SA, tự lưu nguồn; dán vào mô tả TikTok hay không là tùy người đăng).
"""
import html
import json
import os
import re
import sys
import tomllib

import requests

from common import ROOT, load_script, video_dir

# tên hãng: từ khóa có tên hãng thì ảnh BẮT BUỘC có đúng tên đó trong nhãn ("byd electric car" từng ra Tesla Model 3)
BRANDS = {"toyota", "honda", "nissan", "mazda", "subaru", "suzuki", "mitsubishi", "lexus", "daihatsu", "isuzu", "hyundai", "kia",
          "genesis", "byd", "geely", "chery", "nio", "xpeng", "haval", "great", "wuling", "tesla", "ford", "chevrolet", "bmw",
          "mercedes", "audi", "volkswagen", "porsche", "vinfast", "tata", "sony", "panasonic", "samsung", "lg", "xiaomi",
          "huawei", "apple", "oppo", "vivo", "uniqlo", "muji", "nintendo"}
PEXELS = "https://api.pexels.com/v1/search"
WIKIMEDIA = "https://commons.wikimedia.org/w/api.php"
WIKI_HEADERS = {"User-Agent": "shorts-pipeline/1.0 (personal short video tool)"}   # Wikimedia bắt buộc có User-Agent
PIXABAY = "https://pixabay.com/api/"


def sources():
    """[(nguồn, khóa)] theo thứ tự tìm: Pixabay, Pexels nếu có khóa; Wikimedia luôn có (không cần khóa)."""
    conf = {}
    if (ROOT / "config.toml").exists():
        conf = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8")).get("keys", {})
    found = []
    for source in ("pixabay", "pexels"):
        key = os.environ.get(f"{source.upper()}_API_KEY", "").strip() or conf.get(f"{source}_key", "")
        if key:
            found.append((source, key))
    return found + [("wikimedia", "")]


def plain(value):
    """Chữ trong metadata Wikimedia (có thẻ HTML) -> chữ thường."""
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


def wikimedia(query):
    """Ảnh Wikimedia Commons theo từ khóa, chỉ giấy phép dùng thương mại và sửa được; nhãn = tên file + thể loại + mô tả."""
    r = requests.get(WIKIMEDIA, headers=WIKI_HEADERS, timeout=30, params={
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 40,
        "gsrsearch": f"{query} filetype:bitmap", "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1600})
    r.raise_for_status()
    found = []
    for page in sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        licence = plain(meta.get("LicenseShortName", {}).get("value"))
        low = licence.lower()
        if not (low.startswith(("cc by", "cc0", "public domain", "pd")) and "nc" not in low.split("-")
                and "nd" not in low.replace("-", " ").split()):
            continue
        found.append({"id": f"wikimedia_{page['pageid']}", "src": info.get("thumburl") or info.get("url"),
                      "photographer": plain(meta.get("Artist", {}).get("value"))[:120], "url": info.get("descriptionurl", ""),
                      "alt": " ".join([page.get("title", ""), plain(meta.get("Categories", {}).get("value")),
                                       plain(meta.get("ImageDescription", {}).get("value"))[:300]]),
                      "licence": licence, "landscape": info.get("width", 0) >= info.get("height", 1)})
    return [f for f in found if f["landscape"]] + [f for f in found if not f["landscape"]]


def search(source, key, query, skip):
    """Ảnh ngang trước (khung polaroid là khung ngang 9:7), không có thì ảnh dọc; trong các kết quả chọn ảnh có nhãn / mô tả
    khớp nhiều từ khóa nhất (ảnh đầu tiên hay lạc đề: "used car dealership" ra đuôi xe Cadillac). Bỏ ảnh người duyệt đã loại.
    Trả về {"id", "src", "photographer", "url", "alt"} hoặc None."""
    words = {w for w in query.lower().split() if len(w) > 2}
    brands = {w for w in query.lower().split() if w in BRANDS}
    if source == "wikimedia":
        found = [f for f in wikimedia(query) if f["id"] not in skip and all(b in f["alt"].lower() for b in brands)]
        return max(found, key=lambda f: (sum(w in f["alt"].lower() for w in words), -found.index(f))) if found else None
    for orientation in ("landscape", "portrait"):
        if source == "pixabay":
            r = requests.get(PIXABAY, timeout=30, params={
                "key": key, "q": query[:100], "image_type": "photo", "safesearch": "true", "per_page": 40,
                "orientation": "horizontal" if orientation == "landscape" else "vertical"})
            r.raise_for_status()
            found = [{"id": f"pixabay_{h['id']}", "src": h["largeImageURL"], "photographer": h.get("user", ""),
                      "url": h["pageURL"], "alt": h.get("tags", "")} for h in r.json().get("hits", [])]
        else:
            r = requests.get(PEXELS, headers={"Authorization": key}, timeout=30,
                             params={"query": query, "per_page": 40, "orientation": orientation})
            r.raise_for_status()
            found = [{"id": p["id"], "src": p["src"]["large2x"], "photographer": p["photographer"], "url": p["url"],
                      "alt": p.get("alt", "")} for p in r.json().get("photos", [])]
        found = [f for f in found if f["id"] not in skip and all(b in f["alt"].lower() for b in brands)]
        if found:                                     # cùng điểm thì giữ thứ tự của trang ảnh (phổ biến trước)
            return max(found, key=lambda f: (sum(w in f["alt"].lower() for w in words), -found.index(f)))
    return None


def main():
    video = video_dir()
    script = load_script(video)
    wanted = [s for s in script["scenes"] if isinstance(s.get("photo"), dict) and s["photo"].get("query")]
    if not wanted:
        return print("Kịch bản không có cảnh ảnh thật, bỏ qua.")
    folder = video / "photos"
    folder.mkdir(exist_ok=True)
    credits_file, rejected_file = folder / "credits.json", folder / "rejected_ids.json"
    credits = json.loads(credits_file.read_text(encoding="utf-8")) if credits_file.exists() else {}
    rejected = set(json.loads(rejected_file.read_text(encoding="utf-8"))) if rejected_file.exists() else set()
    for scene in wanted:
        out = folder / f"{scene['id']:03d}.jpg"
        if out.exists():
            continue
        query = scene["photo"]["query"]
        photo = data = None
        order = sources()
        if any(w in BRANDS for w in query.lower().split()):   # tên hãng: Wikimedia có ảnh thân xe đúng mẫu (Pixabay hay ra
            order = order[-1:] + order[:-1]                    # ảnh khoang máy, chi tiết); từ khóa chung: Pixabay trước
        for source, key in order:                         # nguồn đầu không có (vd BYD trên Pixabay) thì tìm nguồn sau
            try:
                photo = search(source, key, query, rejected)
                if photo is None:
                    continue
                data = requests.get(photo["src"], timeout=60, headers=WIKI_HEADERS)
                data.raise_for_status()
                break
            except requests.RequestException as e:        # mạng / khóa sai: thử nguồn sau, không chặn video
                print(f"photos/{out.name}: lỗi {source} ({e})")
                photo = None
        if photo is None:
            print(f"photos/{out.name}: không nguồn nào có ảnh cho '{query}'")
            continue
        out.write_bytes(data.content)
        credits[out.name] = {"id": photo["id"], "source": source, "query": query, "photographer": photo["photographer"],
                             "url": photo["url"], "alt": photo["alt"][:300], "licence": photo.get("licence", source)}
        print(f"photos/{out.name}: '{query}' -> {photo['url']} ({photo['photographer']}, {photo.get('licence', source)})")
    credits_file.write_text(json.dumps(credits, ensure_ascii=False, indent=1), encoding="utf-8")
    write_credit_lines(video, credits)


def write_credit_lines(video, credits):
    """Dòng nguồn ảnh Wikimedia (giấy phép CC đòi ghi tác giả) vào credits.txt của video, cạnh tên giọng VOICEVOX."""
    path = video / "credits.txt"
    lines = [x for x in (path.read_text(encoding="utf-8").splitlines() if path.exists() else [])
             if x.strip() and not x.startswith("写真: ")]
    lines += [f"写真: {c['photographer'] or 'Wikimedia Commons'} / {c['licence']} ({c['url']})"
              for c in credits.values() if c.get("source") == "wikimedia"]
    if lines:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
