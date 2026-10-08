"""Tải nhạc nền theo cảm xúc từ 甘茶の音楽工房 (https://amachamusic.chagasi.com/) vào library/bgm/<nhóm>/.

  python tools/fetch_bgm.py            # tải các bài còn thiếu (nghỉ 2 giây giữa hai lần tải)

Điều khoản (đọc 2026-10-08, https://amachamusic.chagasi.com/terms.html): dùng thương mại được (YouTube có kiếm tiền),
không bắt buộc ghi nguồn; CẤM bán / phát tán lại nhạc, CẤM đăng ký video vào Content ID, cấm nhận là nhạc của mình.
Thư mục library/bgm/ đã nằm trong .gitignore.

build_video.py chọn nhóm theo thể loại kịch bản ("genre"), chọn bài trong nhóm theo tên video (mỗi video một bài, cố định).
Video có music.mp3 riêng thì dùng file đó.
"""
import re
import sys
import time
import urllib.request
from pathlib import Path

SITE = "https://amachamusic.chagasi.com"
OUT = Path(__file__).resolve().parent.parent / "library" / "bgm"
PER_GROUP = 4
# nhóm nhạc của mình -> trang cảm xúc trên 甘茶の音楽工房
GROUPS = {
    "kandou": "image_shimijimi",   # しみじみ: cảm động, gia đình, ngụ ngôn
    "kanashii": "image_kanashii",  # 悲しい: buồn
    "comical": "image_comical",    # コミカル: hài
    "ayashii": "image_ayashii",    # 怪しい: bí ẩn, hồi hộp
    "honobono": "image_honobono",  # ほのぼの: tình yêu, thanh xuân, đời thường ấm áp
    "serious": "image_serious",    # シリアス: công sở, xã hội, trả thù
}


def get(url, referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (shorts-pipeline; personal use)"}
    if referer:
        headers["Referer"] = referer
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
        return r.read()


def main():
    total = 0
    for group, page in GROUPS.items():
        folder = OUT / group
        folder.mkdir(parents=True, exist_ok=True)
        html = get(f"{SITE}/{page}.html").decode("utf-8", "replace")
        mp3s = list(dict.fromkeys(re.findall(r"(mp3/[^\"']+\.mp3)", html)))[:PER_GROUP]
        for mp3 in mp3s:
            target = folder / Path(mp3).name
            if not target.exists():
                target.write_bytes(get(f"{SITE}/{mp3}", referer=f"{SITE}/{page}.html"))
                print(f"{group}/{target.name}", flush=True)
                time.sleep(2)                       # tải chậm, lịch sự với trang
        total += len(list(folder.glob("*.mp3")))
    print(f"Tổng {total} bài trong {len(GROUPS)} nhóm.")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
