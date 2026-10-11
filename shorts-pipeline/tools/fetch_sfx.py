"""Tải bộ hiệu ứng âm thanh thật từ 効果音ラボ (https://soundeffect-lab.info/) vào library/sfx/lab/<nhóm>/.

  python tools/fetch_sfx.py           # tải các tiếng còn thiếu (nghỉ 1 giây giữa hai lần tải)

Điều khoản 効果音ラボ (đọc 2026-10-08, https://soundeffect-lab.info/agreement/): dùng được trong video YouTube có kiếm tiền,
không cần ghi nguồn; CẤM phát tán lại file gốc (không đưa thư mục lab/ lên git công khai, không chia sẻ bộ file) và cấm dùng
làm dữ liệu học AI. Thư mục library/sfx/lab/ đã nằm trong .gitignore.

Mỗi nhóm có nhiều phiên bản; build_video.py chọn luân phiên theo cảnh để không nghe lặp. Nhóm không có file tải về
thì dùng tiếng tạo bằng code (library/sfx/<nhóm>.wav, tools/make_sfx.py).
"""
import re
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np

SITE = "https://soundeffect-lab.info/sound"
OUT = Path(__file__).resolve().parent.parent / "library" / "sfx" / "lab"
RATE = 48000
BANNED = {l.strip() for l in (OUT.parent / "banned.txt").read_text(encoding="utf-8").splitlines()
          if l.strip() and not l.startswith("#")} if (OUT.parent / "banned.txt").exists() else set()   # tiếng bị loại
MAX_SECONDS = 3.0           # cắt bớt đuôi dài (chuông, nhạc) cho vừa một cảnh
AMBIENT_SECONDS = 40.0      # tiếng nền (nhóm amb_*): giữ dài để lặp lại suốt các cảnh cùng bối cảnh

# nhóm -> [(trang, tên tiếng trên trang)]; tên giống nhau xuất hiện nhiều lần thì lấy tất cả
PICKS = {
    "don": [("anime", "和太鼓でドン"), ("anime", "ドーン"), ("anime", "バーン"), ("anime", "文字表示の衝撃音1"),
            ("anime", "文字表示の衝撃音2")],
    "dodon": [("anime", "和太鼓でドドン"), ("anime", "文字表示の衝撃音3")],
    "jan": [("anime", "ジャジャーン"), ("anime", "運命1"), ("anime", "運命2")],
    "gaan": [("anime", f"ショック{i}") for i in range(1, 7)] + [("anime", "絶望")],
    "shoboon": [("anime", "落ち込む"), ("anime", "しょげる")],
    "chiin": [("anime", "チーン1"), ("anime", "チーン2"), ("anime", "木魚ポク・ポク・ポク")],
    "pikon": [("anime", "ピコッ"), ("anime", "ひらめく1"), ("anime", "ひらめく2"), ("anime", "クイズ正解1"),
              ("anime", "クイズ正解2")],
    "bikkuri": [("anime", "驚く")],
    "hatena": [("anime", "目が点になる"), ("anime", "クイズ出題1")],
    "pon": [("anime", "パッ"), ("anime", "パパッ"), ("anime", "ペタッ"), ("anime", "ニュッ1"), ("anime", "ニュッ2"),
            ("anime", "ちょこっと触る")],
    "boyon": [("anime", "ボヨヨーン"), ("anime", "ボヨン"), ("anime", "ぷよん"), ("anime", "ジャンプ")],
    "kiran": [("anime", "きらーん1"), ("anime", "きらーん2"), ("anime", "キラッ1"), ("anime", "キラッ2"),
              ("anime", "きらきら輝く1"), ("anime", "きらきら輝く2"), ("anime", "可愛く輝く1")],
    "shakin": [("anime", "シャキーン1"), ("anime", "シャキーン2"), ("anime", "シャキーン3"), ("anime", "ヒーローの決めポーズ")],
    "hyu": [("anime", "ヒューンと落下"), ("anime", "ピューンと逃げる"), ("anime", "間抜け1"), ("anime", "間抜け2")],
    "chanchan": [("anime", "ちゃんちゃん♪1"), ("anime", "ちゃんちゃん♪2"), ("anime", "ちゃんちゃん♪3")],
    "whoosh": [("anime", "シーン切り替え1"), ("anime", "シーン切り替え2")],
    "heartbeat": [("anime", "心臓の鼓動1"), ("anime", "心臓の鼓動2")],
    "kaisou": [("anime", "回想"), ("anime", "過去を思い出す")],
    "tsukkomi": [("anime", "ビシッとツッコミ1"), ("anime", "ビシッとツッコミ3")],
    "shiver": [("anime", "カタカタ震える")],
    "guki": [("anime", "足首がグキッ")],
    "tear": [("anime", "涙のしずく")],
    "dash": [("anime", "超高速ダッシュ"), ("various", "アスファルトの上を走る1")],
    "zukkoke": [("anime", "ずっこける")],
    "gogogo": [("anime", "ゴゴゴゴ")],
    "door": [("various", "ドアを開ける1"), ("various", "自動ドアが開く"), ("various", "引き戸を開ける1")],
    "knock": [("various", "木のドアをノック1")],
    "money": [("various", "お金がジャラジャラ"), ("various", "レジスターで精算")],
    "walk": [("various", "アスファルトの上を歩く1")],
    "drop": [("various", "水滴1")],
    "train": [("machine", "電車走行中1"), ("machine", "電車走行中2"), ("machine", "電車発車1")],
    "train_door": [("machine", "電車のドアが開く"), ("machine", "電車の圧搾空気排出")],
    "bell": [("machine", "電車の発車ベル"), ("machine", "黒電話のベルが鳴る")],
    "phone": [("machine", "携帯電話の着信音1"), ("machine", "携帯電話の着信音2"), ("machine", "電話の着信音")],
    "vibe": [("machine", "携帯電話のバイブレーション1")],
    "camera": [("machine", "カメラのシャッター1"), ("machine", "記者会見のシャッター音")],
    "keyboard": [("machine", "キーボード1"), ("machine", "キーボードの早打ち1")],
    "click": [("machine", "クリック")],
    # hành động, phản ứng
    "punch": [("battle", "軽いパンチ1"), ("battle", "重いパンチ1"), ("battle", "打撃1"), ("battle", "打撃2"), ("battle", "打撃3")],
    "slap": [("battle", "平手打ち1")],
    "fall": [("battle", "バタンと倒れる"), ("battle", "倒れる")],
    "swish": [("battle", "パンチの素振り1"), ("battle", "パンチの素振り2"), ("battle", "刀の素振り1"), ("battle", "剣の素振り1")],
    "aura": [("battle", "オーラ1"), ("battle", "オーラ2"), ("battle", "パワーチャージ")],
    "warp": [("battle", "ワープ")],
    "slowmo": [("battle", "スローモーション")],
    "heal": [("battle", "回復魔法1"), ("battle", "回復魔法2")],
    "correct": [("anime", "クイズ正解3"), ("anime", "クイズ正解4")],
    "wrong": [("anime", "クイズ不正解1"), ("anime", "クイズ不正解2")],
    "message": [("button", "メッセージ表示音1"), ("button", "メッセージ表示音2")],
    "beep": [("button", "ビープ音1"), ("button", "決定ボタンを押す1")],
    "warning": [("button", "警告音1")],
    "success": [("button", "成功音")],
    "timer": [("anime", "制限時間タイマー")],
    "drumroll": [("anime", "ドラムロール"), ("anime", "ロールの閉め")],
    "horror": [("anime", "恐怖"), ("anime", "恐怖の不協和音"), ("anime", "迫り来る恐怖")],
    "fanfare": [("anime", "ラッパのファンファーレ"), ("anime", "レベルアップ")],
    "eat": [("anime", "食べ物をパクッ")],
    "stretch": [("anime", "伸びる")],
    # tiếng nền theo bối cảnh (build_video.py chọn theo tên bối cảnh, âm lượng [video] ambient_volume)
    "amb_rain": [("environment", "雨が降る1"), ("environment", "雨の街の道路")],
    "amb_storm": [("environment", "雷雨")],
    "amb_street": [("environment", "街の道路"), ("environment", "閑静な住宅街1")],
    "amb_city": [("environment", "大都会"), ("environment", "夜の繁華街")],
    "amb_station": [("environment", "駅改札口"), ("environment", "駅前広場")],
    "amb_train": [("machine", "電車走行中1"), ("machine", "電車走行中2")],
    "amb_school": [("environment", "騒がしい高校の教室")],
    "amb_ground": [("environment", "高校のグラウンド")],
    "amb_park": [("environment", "公園1"), ("environment", "公園2")],
    "amb_sea": [("environment", "海岸1"), ("environment", "カモメが鳴くビーチ")],
    "amb_port": [("environment", "港")],
    "amb_river": [("environment", "河原"), ("environment", "小川")],
    "amb_store": [("environment", "スーパーマーケット1"), ("environment", "スーパーマーケット2")],
    "amb_restaurant": [("environment", "レストラン")],
    "amb_airport": [("environment", "空港ロビー")],
    "amb_festival": [("environment", "花火大会")],
    "amb_country": [("environment", "夏の田舎道"), ("environment", "ミンミンゼミが鳴く雑木林")],
    "amb_night": [("environment", "夏の田舎の夜")],
    "amb_morning": [("environment", "スズメが鳴く朝")],
    "amb_evening": [("environment", "カラスが鳴く夕方")],
    "amb_wind": [("environment", "風が吹く1"), ("environment", "吹雪")],
    "amb_home_meal": [("environment", "家で食事")],
}


def get(url, referer=None):
    headers = {"User-Agent": "Mozilla/5.0 (shorts-pipeline; personal use)"}
    if referer:                                 # file mp3 chỉ tải được từ trang của nó (như bấm nút tải trên trang)
        headers["Referer"] = referer
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as r:
        return r.read()


def page_items(page):
    html = get(f"{SITE}/{page}/").decode("utf-8", "replace")
    return re.findall(r'<li><span>([^<]+)</span>[^<]*<a href="(mp3/[^"]+\.mp3)"', html)


def to_wav(mp3, wav):
    """mp3 -> wav 48 kHz mono, cắt đuôi dài, chuẩn hóa đỉnh -1.5 dB."""
    seconds = AMBIENT_SECONDS if wav.parent.name.startswith("amb_") else MAX_SECONDS
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(RATE),
                    "-t", str(seconds), str(wav)], check=True)
    with wave.open(str(wav), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
    x = x / max(np.abs(x).max(), 1e-6) * 0.84
    fade = min(len(x), int((0.5 if wav.parent.name.startswith("amb_") else 0.05) * RATE))
    x[-fade:] *= np.linspace(1, 0, fade)
    if wav.parent.name.startswith("amb_"):      # tiếng nền lặp lại: mờ vào đầu để chỗ nối không bị giật
        x[:fade] *= np.linspace(0, 1, fade)
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    pages = {page: page_items(page) for page in {p for picks in PICKS.values() for p, _ in picks}}
    done = missing = 0
    for group, picks in PICKS.items():
        folder = OUT / group
        folder.mkdir(parents=True, exist_ok=True)
        for page, title in picks:
            urls = [url for name, url in pages[page] if name == title]
            if not urls:
                print(f"  không thấy '{title}' trên trang {page}")
                missing += 1
                continue
            for url in urls:
                wav = folder / f"{Path(url).stem}.wav"
                if Path(url).stem in BANNED:
                    continue
                if wav.exists():
                    continue
                mp3 = wav.with_suffix(".mp3")
                mp3.write_bytes(get(f"{SITE}/{page}/{url}", referer=f"{SITE}/{page}/"))
                to_wav(mp3, wav)
                mp3.unlink()
                done += 1
                print(f"{group}/{wav.name}  ({title})", flush=True)
                time.sleep(1)                       # tải chậm, lịch sự với trang
    total = sum(len(list((OUT / g).glob("*.wav"))) for g in PICKS)
    print(f"Tải mới {done} tiếng; tổng {total} tiếng trong {len(PICKS)} nhóm; {missing} tên không thấy.")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
