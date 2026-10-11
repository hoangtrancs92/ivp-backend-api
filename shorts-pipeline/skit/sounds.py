"""Tiểu phẩm: tìm và tải tiếng hiệu ứng MỚI theo đúng mô tả trong kịch bản (trường "sfx" từng câu), không dùng tạm tiếng có sẵn.

  python skit/sounds.py skits/<tên>
  python skit/sounds.py --catalog          # chỉ làm mới danh mục tiếng

Nguồn: 効果音ラボ (https://soundeffect-lab.info/), điều khoản: dùng được trong video kiếm tiền, không cần ghi nguồn, cấm phát tán
lại file gốc (thư mục library/sfx/lab/ đã trong .gitignore). Danh mục ~1.200+ tiếng (tên + mô tả) quét một lần, lưu
library/sfx/lab_catalog.json, quá 30 ngày thì quét lại.
AI đạo diễn (skit/write.py --direct) nghĩ tiếng cần trước, rồi tra danh mục gọn (`compact()`: ~1.500 tên, gộp bản đánh số):
có tên khớp thì ghi đúng tên (ở đây tải luôn, không cần AI), không có thì ghi mô tả tự do. Mô tả tự do / tên không khớp: lọc sơ
40 tiếng gần nghĩa nhất theo chữ, rồi AI chọn đúng một tiếng hoặc "không có"; không có thì câu đó im lặng (tiếng sai nghĩa
tệ hơn không có tiếng). Tiếng tải về: library/sfx/lab/_skit/<file>.wav (dùng lại giữa các tiểu phẩm nếu
AI chọn đúng tiếng đó). Kết quả ghi vào skit.json: "sounds" {mô tả: đường dẫn | null}.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "tools")]
from llm import LLMError, chat, json_reply   # noqa: E402
from fetch_sfx import to_wav                 # noqa: E402  (chỉ dùng lại, không sửa)

SITE = "https://soundeffect-lab.info"
PAGES = ["animal", "anime", "battle", "button", "environment", "machine", "various", "voice"]
CATALOG = ROOT / "library" / "sfx" / "lab_catalog.json"
OUT = ROOT / "library" / "sfx" / "lab" / "_skit"
MODEL = os.environ.get("AI_MODEL_SCRIPT") or "claude-sonnet-5-5"
ITEM = re.compile(r'<li><span>([^<]+)</span>([^<]*)<a href="([^"]+\.mp3)"')

KEYWORDS = """Tìm tiếng hiệu ứng trong kho 効果音ラボ (tên tiếng ngắn kiểu 「カークラッシュ」「自動車事故」「ショック1」「拍手喝采」
「ドアを開ける1」). Với mỗi mô tả dưới đây, viết 4-6 từ khóa tiếng Nhật ngắn có thể là TÊN tiếng đó trong kho (đồng nghĩa, kanji /
katakana / từ tượng thanh, vật phát ra tiếng). Trả về đúng một JSON {{"<số>": ["từ khóa", ...]}}, không kèm chữ nào khác.

{wanted}"""

PICK = """Chọn tiếng hiệu ứng cho một tiểu phẩm hài tiếng Nhật. Với mỗi yêu cầu, chọn ĐÚNG MỘT tiếng trong danh sách ứng viên
của nó khớp nghĩa nhất (đúng vật / hành động / cảm giác), hoặc null nếu không có tiếng nào thật sự khớp (đừng chọn đại).
Trả về đúng một JSON {{"<số yêu cầu>": <số ứng viên hoặc null>}}, không kèm chữ nào khác.

{requests}"""


def get(url, referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (shorts-pipeline; personal use)"}
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()


def build_catalog():
    """Quét các trang danh mục (và trang con .html của chúng): [{title, desc, url, page}]."""
    seen, items, queue = set(), {}, [f"{SITE}/sound/{p}/" for p in PAGES]
    while queue:
        page = queue.pop(0)
        if page in seen or len(seen) > 80:
            continue
        seen.add(page)
        try:
            html = get(page).decode("utf-8", "replace")
        except OSError as e:
            print(f"  bỏ qua {page}: {e}", flush=True)
            continue
        for title, desc, href in ITEM.findall(html):
            url = href if href.startswith("http") else SITE + href if href.startswith("/") else page.rsplit("/", 1)[0] + "/" + href
            items.setdefault(url, {"title": title.strip(), "desc": desc.strip(), "url": url, "page": page})
        for sub in re.findall(r'href="(/sound/[a-z0-9_-]+/[a-z0-9_-]+\.html)"', html):
            queue.append(SITE + sub)
        time.sleep(1)                                    # tải chậm, lịch sự với trang
    catalog = {"updated": time.time(), "items": list(items.values())}
    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Danh mục: {len(items)} tiếng từ {len(seen)} trang -> {CATALOG}", flush=True)
    return catalog["items"]


def catalog():
    """Danh mục tiếng, đã bỏ các tiếng bị loại (library/sfx/banned.txt)."""
    banned = ROOT / "library" / "sfx" / "banned.txt"
    banned = {l.strip() for l in banned.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}         if banned.exists() else set()
    items = None
    if CATALOG.exists():
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        if time.time() - data["updated"] < 30 * 86400 and data["items"]:
            items = data["items"]
    return [it for it in (items or build_catalog()) if Path(it["url"]).stem not in banned]


def base_name(title):
    """Tên gộp các bản đánh số: 「ショック3」 -> 「ショック」."""
    return re.sub(r"[0-9０-９]+$", "", title).strip()


def compact(items=None):
    """(chữ cho AI đọc: tên tiếng theo trang, {tên gộp: [tiếng]}) — các bản đánh số gộp một tên."""
    groups, names = {}, {}
    for it in items or catalog():
        page = it["page"].rstrip("/").split("/sound/")[-1].replace(".html", "")
        name = base_name(it["title"])
        if name not in names:
            groups.setdefault(page, []).append(name)
        names.setdefault(name, []).append(it)
    return "\n".join(f"[{p}] " + "、".join(g) for p, g in groups.items()), names


def exact(want, names, salt=0):
    """Tiếng đúng tên AI đạo diễn chọn (tên gộp hoặc tên đầy đủ có số); nhiều bản thì chọn theo salt (khác nhau giữa các tiểu phẩm)."""
    want = want.strip().strip("「」")
    if want in names:
        options = names[want]
        return options[salt % len(options)]
    for options in names.values():
        for it in options:
            if it["title"] == want:
                return it
    return None


def grams(text):
    text = re.sub(r"[\s、。・!！?？「」()（）0-9０-９]", "", text)
    return {text[i:i + 2] for i in range(len(text) - 1)} | set(text)


def candidates(want, items, keywords=(), count=40):
    """Tiếng gần nghĩa nhất theo chữ chung (bigram) giữa mô tả / từ khóa đồng nghĩa và tên + ghi chú của tiếng."""
    def best(text, n):
        w = grams(text)
        return sorted(items, key=lambda it: -len(w & grams(it["title"] + it["desc"])) * 2 - len(w & grams(it["title"])))[:n]
    pool = {it["url"]: it for it in best(want, 16)}
    for k in keywords:
        pool.update({it["url"]: it for it in items if k in it["title"]})          # khớp nguyên từ khóa trong tên
        pool.update({it["url"]: it for it in best(k, 6)})
    return list(pool.values())[:count]


def download(item):
    OUT.mkdir(parents=True, exist_ok=True)
    wav = OUT / f"{Path(item['url']).stem}.wav"
    if not wav.exists():
        mp3 = wav.with_suffix(".mp3")
        mp3.write_bytes(get(item["url"], referer=item["page"]))
        to_wav(mp3, wav)
        mp3.unlink()
        time.sleep(1)
    return wav


def main():
    if "--catalog" in sys.argv:
        return build_catalog()
    folder = Path(sys.argv[1]).resolve()
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    wanted = list(dict.fromkeys(l["sfx"] for l in skit["lines"] if l.get("sfx")))
    sounds = {k: v for k, v in (skit.get("sounds") or {}).items() if k in wanted and (v is None or (ROOT / v).exists())}
    todo = [w for w in wanted if w not in sounds]
    if not todo:
        return print(f"Đủ tiếng ({len(wanted)} yêu cầu), bỏ qua.")
    items = catalog()
    _, names = compact(items)
    salt = sum(map(ord, folder.name))
    for w in list(todo):                                 # đúng tên trong kho: tải luôn
        item = exact(w, names, salt)
        if item:
            try:
                sounds[w] = download(item).relative_to(ROOT).as_posix()
                print(f"  {w}: {item['title']} (đúng tên trong kho)", flush=True)
                todo.remove(w)
            except OSError as e:
                print(f"  {w}: tải lỗi ({e})", flush=True)
    if not todo:
        return save(folder, skit, sounds)
    try:
        keys = json_reply(chat(KEYWORDS.format(wanted="\n".join(f"{i}. {w}" for i, w in enumerate(todo))), MODEL, max_tokens=3000))
    except (LLMError, ValueError):
        keys = {}
    pools = {w: candidates(w, items, [k for k in keys.get(str(i), []) if isinstance(k, str) and k]) for i, w in enumerate(todo)}
    requests = "\n\n".join(f"Yêu cầu {i}: {w}\n" + "\n".join(f"  {j}. {it['title']} ({it['desc']})" for j, it in enumerate(pools[w]))
                           for i, w in enumerate(todo))
    print(f"Tìm {len(todo)} tiếng bằng {MODEL}...", flush=True)
    try:
        picks = json_reply(chat(PICK.format(requests=requests), MODEL, max_tokens=4000))
    except (LLMError, ValueError) as e:
        sys.exit(f"Không chọn được tiếng: {e}")
    for i, w in enumerate(todo):
        j = picks.get(str(i))
        item = pools[w][j] if isinstance(j, int) and 0 <= j < len(pools[w]) else None
        if item is None:
            sounds[w] = None
            print(f"  {w}: không có tiếng khớp, câu này để im", flush=True)
            continue
        try:
            sounds[w] = download(item).relative_to(ROOT).as_posix()
            print(f"  {w}: {item['title']} ({item['desc']})", flush=True)
        except OSError as e:
            sounds[w] = None
            print(f"  {w}: tải lỗi ({e}), để im", flush=True)
    save(folder, skit, sounds)


def save(folder, skit, sounds):
    skit["sounds"] = sounds
    (folder / "skit.json").write_text(json.dumps(skit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Tiếng: {sum(v is not None for v in sounds.values())}/{len(sounds)} tìm được")


if __name__ == "__main__":
    main()
