"""Tạo bộ hiệu ứng âm thanh kiểu gameshow / anime Nhật bằng code (không cần tải về, không lo bản quyền):
library/sfx/<tên>.wav, 48 kHz mono.

  python tools/make_sfx.py            # tạo các file còn thiếu; build_video.py tự gọi khi cần
  python tools/make_sfx.py --force    # tạo lại tất cả

  don      ドン   trống taiko: bất ngờ, rung khung, đường tốc độ, giận
  dodon    ドドン hai tiếng taiko: cú twist, chớp trắng
  gaan     ガーン hợp âm kèn đổ xuống: sốc, tuyệt vọng
  chiin    チーン chuông chùa (rin): buồn, khóc, thất bại
  pikon    ピコン tiếng "ting" quiz show: nhận ra, sticker "!"
  pon      ポン   gõ gỗ nhẹ: chữ tượng thanh, sticker bật ra
  boyon    ボヨン lò xo: nhảy, nhún
  kiran    キラーン lấp lánh đi lên: hào quang, lấp lánh, tim
  shakin   シャキーン kim loại sáng: tia sáng, quyết tâm
  jan      ジャン! dàn nhạc đánh mạnh: lộ bí mật
  hyu      ヒュ〜 còi trượt xuống: đổ mồ hôi, hụt hẫng
  hatena   ハテナ "pôw-ăn" đi lên: thắc mắc, sticker "?"
  chanchan チャンチャン hai nốt kết thúc kiểu hài
  whoosh   シュッ gió lướt (chuyển cảnh)          swish  ヒュン lia nhanh, ngắn
Muốn thay bằng âm thanh thật: chép file .wav cùng tên đè vào library/sfx/.
"""
import sys
import wave
from pathlib import Path

import numpy as np

RATE = 48000
OUT = Path(__file__).resolve().parent.parent / "library" / "sfx"
rng = np.random.default_rng(7)


def t(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def lowpass(x, width):
    kernel = np.hanning(max(int(width), 2))
    return np.convolve(x, kernel / kernel.sum(), mode="same")


def highpass(x, width):
    return x - lowpass(x, width)


def phase(freq):
    """Pha tích lũy cho tần số thay đổi theo thời gian (mảng hoặc số)."""
    return 2 * np.pi * np.cumsum(freq) / RATE


def glide(f0, f1, seconds, curve="exp"):
    tt = t(seconds)
    if curve == "exp":
        return f0 * (f1 / f0) ** (tt / seconds)
    return f0 + (f1 - f0) * tt / seconds


def saw(freq, harmonics=12):
    """Sóng răng cưa giới hạn dải (tiếng kèn, dàn nhạc)."""
    ph = phase(freq)
    return sum(np.sin(k * ph) / k for k in range(1, harmonics + 1))


def square(freq, harmonics=7):
    """Sóng vuông mềm (tiếng điện tử quiz show)."""
    ph = phase(freq)
    return sum(np.sin(k * ph) / k for k in range(1, 2 * harmonics, 2))


def env(seconds, attack=0.005, decay=6.0):
    tt = t(seconds)
    return np.minimum(1, tt / attack) * np.exp(-tt * decay)


def place(total, *parts):
    """Ghép các đoạn (giây bắt đầu, mẫu) vào một đoạn dài total giây."""
    out = np.zeros(len(t(total)))
    for start, x in parts:
        i = int(start * RATE)
        out[i:i + len(x)] += x[: len(out) - i]
    return out


# ---------- các tiếng ----------

def taiko(seconds=0.9, pitch=1.0):
    membrane = np.sin(phase(glide(150 * pitch, 70 * pitch, seconds))) * env(seconds, 0.002, 5.5)
    overtone = np.sin(phase(glide(345 * pitch, 170 * pitch, seconds))) * env(seconds, 0.002, 14) * 0.35
    skin = lowpass(rng.standard_normal(len(t(seconds))), 40) * env(seconds, 0.001, 45) * 3
    return membrane + overtone + skin


def don():
    return taiko()


def dodon():
    return place(1.2, (0, taiko(0.5, 1.05) * 0.7), (0.17, taiko(1.0, 0.95)))


def gaan():
    s = 1.5
    chord = sum(saw(glide(f, f * 0.82, s)) for f in (196.0, 233.1, 277.2, 392.0))   # hợp âm nghịch tai đổ xuống
    tremolo = 1 + 0.25 * np.sin(2 * np.pi * 7 * t(s))
    return lowpass(chord, 10) * tremolo * env(s, 0.01, 2.2)


def chiin():
    s = 2.6
    tt = t(s)
    bell = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d)
               for f, a, d in ((1046.0, 1.0, 1.4), (1049.5, 0.8, 1.5), (2884.0, 0.45, 2.6), (5650.0, 0.2, 4.0)))
    strike = lowpass(rng.standard_normal(len(tt)), 8) * np.exp(-tt * 120) * 0.3
    return bell * np.minimum(1, tt * 600) + strike


def pikon():
    return place(0.32, (0, square(np.full(len(t(0.07)), 1568.0)) * env(0.07, 0.002, 25)),
                 (0.07, square(np.full(len(t(0.25)), 2093.0)) * env(0.25, 0.002, 14)))


def pon():
    s = 0.22
    wood = np.sin(phase(glide(640, 430, s))) * env(s, 0.001, 26)
    body = np.sin(phase(glide(320, 230, s))) * env(s, 0.001, 30) * 0.6
    click = highpass(rng.standard_normal(len(t(s))), 6) * env(s, 0.0005, 200) * 0.25
    return wood + body + click


def boyon():
    s = 0.55
    tt = t(s)
    freq = 230 + 160 * np.sin(2 * np.pi * 11 * tt) * np.exp(-tt * 5) + 90 * (1 - tt / s)
    return np.sin(phase(freq)) * env(s, 0.004, 4.5)


def kiran():
    s = 0.9
    sweep_up = np.sin(phase(glide(1400, 4200, 0.35))) * env(0.35, 0.01, 3) * 0.6
    ping = sum(np.sin(2 * np.pi * f * t(0.6)) * a for f, a in ((4186, 1), (6272, 0.4))) * env(0.6, 0.001, 7)
    shimmer = np.zeros(len(t(s)))
    for _ in range(9):
        i = int(rng.uniform(0, 0.6) * RATE)
        blip = np.sin(2 * np.pi * rng.uniform(3000, 6500) * t(0.12)) * env(0.12, 0.001, 30) * rng.uniform(0.2, 0.5)
        shimmer[i:i + len(blip)] += blip[: len(shimmer) - i]
    return place(s, (0, sweep_up), (0.3, ping)) + shimmer


def shakin():
    s = 0.8
    tt = t(s)
    metal = sum(np.sin(2 * np.pi * f * tt) * a * np.exp(-tt * d)
                for f, a, d in ((3150, 1, 4), (4730, 0.7, 5), (6890, 0.5, 6), (2210, 0.4, 3.5)))
    scrape = highpass(rng.standard_normal(len(tt)), 3) * np.exp(-tt * 9) * 0.6 * np.minimum(1, tt * 60)
    return (metal + scrape) * np.minimum(1, tt * 300)


def jan():
    s = 1.0
    chord = sum(saw(np.full(len(t(s)), f)) * a for f, a in ((130.8, 1), (196.0, 0.9), (261.6, 0.8), (329.6, 0.7), (523.3, 0.5)))
    hit = lowpass(rng.standard_normal(len(t(s))), 5) * env(s, 0.001, 30) * 1.5
    return (lowpass(chord, 6) * env(s, 0.004, 3.2) + hit + taiko(s) * 0.6)


def hyu():
    s = 0.7
    tt = t(s)
    freq = glide(1900, 520, s) * (1 + 0.015 * np.sin(2 * np.pi * 9 * tt))
    return np.sin(phase(freq)) * np.minimum(1, tt * 40) * np.exp(-tt * 1.5)


def hatena():
    s = 0.5
    tt = t(s)
    freq = glide(380, 760, s, "lin") * (1 + 0.04 * np.sin(2 * np.pi * 14 * tt))
    return (np.sin(phase(freq)) + 0.3 * np.sin(2 * phase(freq))) * env(s, 0.01, 3)


def chanchan():
    note = lambda f, s: lowpass(saw(np.full(len(t(s)), f), 8), 5) * env(s, 0.004, 9)   # noqa: E731
    return place(0.75, (0, note(784.0, 0.2)), (0.22, note(1046.5, 0.5)))


def whoosh(seconds=0.42, bright=1.0):
    n = len(t(seconds))
    noise = rng.standard_normal(n)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    a, b = lowpass(noise, 60 / bright), lowpass(noise, 14 / bright)
    mix = np.linspace(0, 1, n) ** 1.5
    return (a * (1 - mix) + b * mix) * shape * 3.2


def shiver_fallback():
    return hyu()


SOUNDS = {"don": don, "dodon": dodon, "gaan": gaan, "chiin": chiin, "pikon": pikon, "pon": pon, "boyon": boyon,
          "kiran": kiran, "shakin": shakin, "jan": jan, "hyu": hyu, "hatena": hatena, "chanchan": chanchan,
          "whoosh": whoosh, "swish": lambda: whoosh(0.22, 1.6),
          # dự phòng cho nhóm tiếng thật (tools/fetch_sfx.py) khi chưa tải: dùng tiếng gần nghĩa
          "bikkuri": pikon, "shoboon": hyu, "tear": chiin, "kaisou": kiran, "heartbeat": lambda: place(0.9, (0, taiko(0.3, 0.6)), (0.28, taiko(0.4, 0.55))),
          "gogogo": gaan, "dash": lambda: whoosh(0.3, 1.2), "shiver": hyu, "guki": don, "tsukkomi": pon, "zukkoke": hyu,
          "door": pon, "knock": pon, "money": kiran, "walk": pon, "drop": pon, "train": lambda: whoosh(1.0, 0.6),
          "train_door": lambda: whoosh(0.5, 2.0), "bell": pikon, "phone": pikon, "vibe": shiver_fallback,
          "camera": pon, "keyboard": pon, "click": pon}


def save(name, samples):
    samples = samples / max(np.abs(samples).max(), 1e-6) * 0.85          # chuẩn hóa, chừa khoảng trống
    fade = min(len(samples), int(0.01 * RATE))
    samples[-fade:] *= np.linspace(1, 0, fade)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((samples * 32767).astype("<i2").tobytes())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    force = "--force" in sys.argv
    for name, make in SOUNDS.items():
        if force or not (OUT / f"{name}.wav").exists():
            save(name, make())
            print(f"library/sfx/{name}.wav")


if __name__ == "__main__":
    main()
