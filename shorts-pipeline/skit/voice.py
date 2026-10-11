"""Tiểu phẩm, bước 2: VOICEVOX đọc từng câu (giọng + giọng điệu theo kịch bản), kèm mốc thời gian từng cụm từ để chữ hiện dần.

  python skit/voice.py skits/<tên>

Đầu ra: audio/NNN.wav (48 kHz mono) và audio/timing.json {"lines": [{"wav", "seconds", "reveal": [[giây, tỉ lệ chữ], ...]}]}.
Video phải ≥ 60 giây: tổng ngắn quá thì đọc lại chậm hơn (không dưới 1.0); vẫn ngắn thì thoát mã 5 để skit/auto.py nhờ AI viết thêm.
Dùng lại hàm của steps/06_voice.py (chọn kiểu giọng theo tone, bật VOICEVOX), không sửa file đó.
"""
import importlib.util
import json
import subprocess
import sys
import urllib.parse
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "steps"))
_spec = importlib.util.spec_from_file_location("voice06", ROOT / "steps" / "06_voice.py")
v06 = importlib.util.module_from_spec(_spec)
_argv, sys.argv = sys.argv, [sys.argv[0]]
_spec.loader.exec_module(v06)
sys.argv = _argv

SPEED = 1.3              # tiểu phẩm đọc nhanh, nối liền (video mẫu gần như không khoảng lặng)
EDGE = 0.04              # giây lặng đầu / cuối mỗi câu do VOICEVOX thêm
GAP = 0.12               # giây nghỉ giữa hai câu khi dựng (skit/build.py dùng cùng số này)
MIN_SECONDS = 60          # video phải >= 60 giây
TARGET = 61.5             # khi phải đọc chậm lại: nhắm dư một chút
MAX_PASSES = 6
SHORT = 5                # mã thoát: kịch bản quá ngắn


def synth(text, style, speed, path):
    """Đọc một câu; trả về (giây, [[giây, tỉ lệ chữ đã đọc], ...]) theo từng cụm trọng âm của VOICEVOX."""
    q = urllib.parse.urlencode({"text": text, "speaker": style})
    with urllib.request.urlopen(urllib.request.Request(f"{v06.VOICEVOX}/audio_query?{q}", method="POST")) as r:
        query = json.loads(r.read())
    query.update(speedScale=speed, prePhonemeLength=EDGE, postPhonemeLength=EDGE, outputSamplingRate=48000,
                 outputStereo=False)
    req = urllib.request.Request(f"{v06.VOICEVOX}/synthesis?speaker={style}", data=json.dumps(query).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as r:
        path.write_bytes(r.read())
    with wave.open(str(path)) as w:
        seconds = w.getnframes() / w.getframerate()
    # thời lượng từng cụm (mora + nghỉ), chia theo tốc độ; tỉ lệ chữ hiện = tỉ lệ mora đã đọc
    phrases = []
    for ap in query.get("accent_phrases", []):
        moras = ap.get("moras", [])
        length = sum((m.get("consonant_length") or 0) + (m.get("vowel_length") or 0) for m in moras)
        pause = ap.get("pause_mora")
        length += ((pause.get("vowel_length") or 0) if pause else 0)
        phrases.append((length / speed, len(moras)))
    total_moras = sum(n for _, n in phrases) or 1
    t, done, reveal = EDGE / speed, 0, [[0.0, 0.0]]
    for length, n in phrases:
        t += length
        done += n
        reveal.append([round(t, 3), round(done / total_moras, 3)])
    return seconds, reveal


def silence(seconds, path):
    """Câu không đọc (chỉ dẫn sân khấu 「（過呼吸）」): khoảng lặng đủ để người xem đọc chữ."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(48000)
        w.writeframes(bytes(2) * round(48000 * seconds))


def read_all(skit, out, speakers, speed, credits):
    lines = []
    for k, line in enumerate(skit["lines"], start=1):
        if line.get("silent"):
            wav, seconds = out / f"{k:03d}.wav", min(max(0.5 + 0.07 * len(line["text"]), 0.7), 1.4)
            silence(seconds, wav)
            lines.append({"wav": wav.name, "seconds": seconds, "reveal": [[0.0, 1.0]], "silent": True})
            print(f"audio/{wav.name} {seconds:4.2f}s [im lặng] {line['text']}", flush=True)
            continue
        voice = skit["cast"][line["speaker"]]["voice"]
        name, style = v06.voicevox_style(speakers, voice, line.get("tone"))
        credits.add(name)
        wav = out / f"{k:03d}.wav"
        seconds, reveal = synth(v06.clean(line["text"]) or "…", style, speed, wav)
        lines.append({"wav": wav.name, "seconds": round(seconds, 3), "reveal": reveal})
        print(f"audio/{wav.name} {seconds:4.2f}s [{name} · {line.get('tone')}] {line['text']}", flush=True)
    return lines


def main():
    folder = Path(sys.argv[1]).resolve()
    skit = json.loads((folder / "skit.json").read_text(encoding="utf-8"))
    out = folder / "audio"
    timing_file = out / "timing.json"
    if timing_file.exists() and len(json.loads(timing_file.read_text(encoding="utf-8"))["lines"]) == len(skit["lines"]):
        return print("Đã có giọng đọc, bỏ qua.")
    out.mkdir(parents=True, exist_ok=True)
    speakers = v06.voicevox_speakers() or v06.start_voicevox()
    if not speakers:
        sys.exit("VOICEVOX chưa chạy và không tự bật được ([voice] voicevox_engine trong settings.toml).")
    speed, credits = SPEED, set()
    for attempt in range(MAX_PASSES):
        lines = read_all(skit, out, speakers, speed, credits)
        total = sum(l["seconds"] for l in lines) + GAP * len(lines)
        print(f"Tổng {total:.1f} giây ở tốc độ {speed:.2f}", flush=True)
        if total >= MIN_SECONDS or speed <= 1.0 or attempt == MAX_PASSES - 1:
            break
        # đọc chậm lại vừa đủ, mỗi lần chậm hơn ít nhất 0,02 (làm tròn không được giữ nguyên tốc độ: từng lặp mãi ở 61,9 giây)
        speed = max(1.0, min(round(speed * total / TARGET, 2), round(speed - 0.02, 2)))
        print(f"Ngắn hơn {MIN_SECONDS} giây: đọc lại với tốc độ {speed}", flush=True)
    timing_file.write_text(json.dumps({"speed": speed, "total": round(total, 2), "lines": lines}, ensure_ascii=False,
                                      indent=1), encoding="utf-8")
    (folder / "credits.txt").write_text("\n".join(sorted(v06.CATALOG["voices"].get(n, {}).get("credit", f"VOICEVOX:{n}")
                                                                  for n in credits)) + "\n", encoding="utf-8")
    if total < MIN_SECONDS:
        timing_file.unlink()
        (folder / "work").mkdir(exist_ok=True)
        (folder / "work" / "short.json").write_text(json.dumps({"seconds": round(total, 2)}), encoding="utf-8")
        print(f"Kịch bản quá ngắn ({total:.1f} giây) dù đã đọc chậm nhất.", flush=True)
        sys.exit(SHORT)


if __name__ == "__main__":
    main()
