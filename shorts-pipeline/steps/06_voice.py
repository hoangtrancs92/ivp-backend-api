"""Bước 6: giọng đọc cho từng cảnh. Chạy trên CPU, cần ffmpeg.

  python steps/06_voice.py videos/<tên>

Giọng của mỗi speaker lấy từ trường "voice" trong config/characters.json:
  {"engine": "edge", "name": "ja-JP-NanamiNeural", "rate": "+10%", "pitch": "+0Hz"}   cần mạng, không cần khóa
  {"engine": "voicevox", "speaker": 3}       cần VOICEVOX đang chạy ở máy (mặc định http://127.0.0.1:50021)
Đầu ra audio/001.wav. File đã có thì bỏ qua; xóa file để đọc lại câu đó.
"""
import asyncio
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from common import CONFIG, SETTINGS, load_json, load_script, video_dir

VOICEVOX = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
# cắt khoảng lặng ở đầu và cuối câu, vì độ dài file quyết định độ dài cảnh; ngưỡng ở [voice] trong settings.toml
_CUT = f"silenceremove=start_periods=1:start_threshold={SETTINGS['voice']['silence_db']}dB"
TRIM = f"{_CUT},areverse,{_CUT},areverse,atempo={SETTINGS['voice'].get('tempo', 1.0)}"   # atempo: nhanh hơn, giữ cao độ


def clean(text):
    """Bỏ ngoặc và ký hiệu trước khi đọc; phụ đề vẫn giữ nguyên."""
    text = re.sub(r"[「」『』（）()【】\[\]〈〉《》\"“”…・♪★☆]", "", text.replace("\n", ""))
    return text.strip()


SILENT_SECONDS = 0.5   # câu không có chữ để đọc ("……。", "…！？"): chỉ một nhịp ngắn (1,2 giây người dùng thấy quá lâu)


def silent_seconds(scene):
    """Cảnh không lời: thẻ so sánh cần thời gian đọc số, clip minh họa cần thời gian chạy; còn lại một nhịp ngắn."""
    if scene.get("compare"):          # 2,5 giây ở video 045 thành khoảng lặng dài, nhịp chậm: chỉ đủ liếc thẻ
        return 1.2
    return SILENT_SECONDS


def speakable(text):
    """Có chữ để đọc không (kana, kanji, chữ cái, số); chỉ có dấu câu thì edge-tts báo NoAudioReceived."""
    return bool(re.search(r"[\w぀-ヿ一-鿿]", text))


def edge(text, voice, path):
    import edge_tts
    for attempt in range(3):                    # lỗi mạng tạm thời của dịch vụ đọc: thử lại
        try:
            tts = edge_tts.Communicate(text, voice["name"], rate=voice.get("rate", "+0%"), pitch=voice.get("pitch", "+0Hz"))
            asyncio.run(tts.save(str(path)))
            return
        except edge_tts.exceptions.NoAudioReceived:
            if attempt == 2:
                raise
            time.sleep(3)


def voicevox(text, voice, path):
    query = urllib.parse.urlencode({"text": text, "speaker": voice["speaker"]})
    with urllib.request.urlopen(urllib.request.Request(f"{VOICEVOX}/audio_query?{query}", method="POST")) as r:
        params = json.loads(r.read())
    # VOICEVOX đọc chậm hơn edge-tts (video 022: 5,7 ký tự/giây sau khi đã tăng 1,2 lần, edge ~8): tăng tốc ngay trong
    # VOICEVOX ([voice] voicevox_speed), giữ ngữ điệu tự nhiên hơn là chỉ tua nhanh file
    params["speedScale"] = voice.get("speed", SETTINGS["voice"].get("voicevox_speed", 1.2))
    body = json.dumps(params).encode("utf-8")
    request = urllib.request.Request(f"{VOICEVOX}/synthesis?speaker={voice['speaker']}", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as r:
        path.write_bytes(r.read())


CATALOG = load_json(CONFIG / "voicevox_voices.json")        # giọng AI được chọn + bảng tone -> tên kiểu giọng


def voicevox_speakers():
    """{tên giọng: {tên kiểu: id}} của VOICEVOX đang chạy ở máy, hoặc None nếu chưa mở."""
    try:
        with urllib.request.urlopen(f"{VOICEVOX}/speakers", timeout=5) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    return {sp["name"]: {st["name"]: st["id"] for st in sp["styles"]} for sp in data}


def start_voicevox():
    """VOICEVOX chưa chạy: tự bật engine (chạy nền, không mở cửa sổ) theo [voice] voicevox_engine, chờ tối đa 90 giây."""
    exe = Path(os.path.expandvars(SETTINGS["voice"].get("voicevox_engine", "")))
    if not exe.is_file():
        return None
    print(f"Bật VOICEVOX: {exe}", flush=True)
    subprocess.Popen([str(exe), "--host", "127.0.0.1", "--port", "50021"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                     | getattr(subprocess, "DETACHED_PROCESS", 0))
    for _ in range(45):
        time.sleep(2)
        speakers = voicevox_speakers()
        if speakers:
            return speakers
    return None


def voicevox_style(speakers, name, tone):
    """id kiểu giọng của giọng `name` hợp với `tone` (happy, sad...); giọng không có thì lấy giọng cùng giới tính."""
    styles = speakers.get(name)
    if styles is None:
        gender = CATALOG["voices"].get(name, {}).get("gender", "female")
        name = next((n for n, v in CATALOG["voices"].items() if v["gender"] == gender and n in speakers),
                    next(iter(speakers)))
        styles = speakers[name]
    for wanted in CATALOG["tones"].get(tone or "normal", []) + CATALOG["tones"]["normal"]:
        if wanted in styles:
            return name, styles[wanted]
    return name, next(iter(styles.values()))


def main():
    video = video_dir()
    characters = load_json(CONFIG / "characters.json")
    out = video / "audio"
    out.mkdir(exist_ok=True)
    script = load_script(video)
    chosen = script.get("voices") or {}               # giọng VOICEVOX do AI chọn khi viết kịch bản
    speakers = None
    if chosen and SETTINGS["voice"].get("engine", "voicevox") == "voicevox":
        speakers = voicevox_speakers() or start_voicevox()
    if chosen and speakers is None:
        print("CẢNH BÁO: VOICEVOX chưa mở (http://127.0.0.1:50021): đọc bằng edge-tts. Mở VOICEVOX rồi xóa audio/ "
              "để đọc lại bằng giọng đã chọn.", flush=True)
    credits = set()
    speed = script.get("voice_speed") or SETTINGS["voice"].get("voicevox_speed", 1.2)   # video so sánh: 1.35
    made = synthesize(script, out, characters, chosen, speakers, credits, speed)
    # video phải trên 1 phút: giọng + nghỉ mỗi cảnh ngắn quá thì đọc lại các câu VOICEVOX chậm hơn vừa đủ (không dưới 1.0)
    total = sum(wav_seconds(w) for w in out.glob("*.wav")) + len(script["scenes"]) * SETTINGS["video"].get("pad", 0.08)
    goal = SETTINGS["voice"].get("min_video_seconds", 62)
    if made and total < goal and speed > 1.0 and not script.get("voice_speed"):   # đã chọn nhịp nhanh: không đọc chậm lại
        others = total - sum(wav_seconds(w) for w in made)
        slower = max(1.0, speed * sum(wav_seconds(w) for w in made) / max(goal - others, 1.0))
        print(f"Giọng chỉ {total:.1f} giây (< {goal}): đọc lại {len(made)} câu VOICEVOX với tốc độ {slower:.2f} "
              f"(thay {speed})", flush=True)
        for w in made:
            w.unlink()
        synthesize(script, out, characters, chosen, speakers, credits, slower)
        total = sum(wav_seconds(w) for w in out.glob("*.wav")) + len(script["scenes"]) * SETTINGS["video"].get("pad", 0.08)
    print(f"Tổng giọng + nghỉ: {total:.1f} giây", flush=True)
    if credits:                                       # khi đăng video phải ghi tên giọng VOICEVOX ở phần mô tả
        path = video / "credits.txt"
        # theo dòng (không theo khoảng trắng): giữ nguyên dòng nguồn ảnh "写真: tác giả / giấy phép (link)" của fetch_photos.py
        old = {x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()} if path.exists() else set()
        path.write_text("\n".join(sorted(old | {CATALOG["voices"].get(n, {}).get("credit", f"VOICEVOX:{n}") for n in credits})) + "\n", encoding="utf-8")


def wav_seconds(path):
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def synthesize(script, out, characters, chosen, speakers, credits, speed):
    """Đọc mọi câu chưa có file; trả về các file đọc bằng VOICEVOX (để đọc lại chậm hơn nếu video quá ngắn)."""
    made = []
    for scene in script["scenes"]:
        wav = out / f"{scene['id']:03d}.wav"
        if wav.exists():
            try:
                if wav_seconds(wav) > 0:
                    continue
            except (wave.Error, EOFError, ZeroDivisionError):
                pass
            print(f"audio/{wav.name}: WAV rỗng/hỏng, tạo lại", flush=True)
            wav.unlink()
        text = scene.get("text") or ""
        if not speakable(clean(text)):          # im lặng có chủ ý: tạo khoảng lặng, không gọi TTS
            seconds = silent_seconds(scene)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                            "-t", str(seconds), str(wav)], check=True)
            print(f"audio/{wav.name}: (im lặng {seconds}s) {text}")
            continue
        label = ""
        speech_text = clean(text)
        if re.search(r"[\u0400-\u04ff]", text):
            # Giữ phụ đề nguyên bản, nhưng chuyển câu tiếng Nga sang tiếng Nhật để giọng Nhật đọc được.
            speech_text = "友達のいない一つの力"
            label = " [日本語読み]"
        if speakers and scene["speaker"] in chosen:
            name, style = voicevox_style(speakers, chosen[scene["speaker"]], scene.get("tone"))
            voice = {"engine": "voicevox", "speaker": style, "speed": speed}
            label = f" [{name} · {scene.get('tone', 'normal')}]" + (" [日本語読み]" if speech_text != clean(text) else "")
            credits.add(name)
        else:
            voice = characters[scene["speaker"]]["voice"]
        raw = out / f"{scene['id']:03d}_src.{'mp3' if voice['engine'] == 'edge' else 'wav'}"
        {"edge": edge, "voicevox": voicevox}[voice["engine"]](speech_text, voice, raw)
        trim = f"{_CUT},areverse,{_CUT},areverse,atempo={script['voice_tempo']}" if script.get("voice_tempo") else TRIM
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", trim,
                        "-ar", "48000", "-ac", "1", str(wav)], check=True)
        try:
            seconds = wav_seconds(wav)
        except (wave.Error, EOFError):
            seconds = 0.0
        if seconds <= 0:                         # không để silenceremove tạo WAV rỗng
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
                            "-ar", "48000", "-ac", "1", str(wav)], check=True)
            try:
                seconds = wav_seconds(wav)
            except (wave.Error, EOFError):
                seconds = 0.0
            if seconds <= 0:
                raise RuntimeError(f"TTS không tạo được âm thanh cho cảnh {scene['id']} ({scene['speaker']}); "
                                   "kiểm tra nội dung và giọng đọc.")
        raw.unlink()
        if voice["engine"] == "voicevox":
            made.append(wav)
        print(f"audio/{wav.name}: {scene['text']}{label}")
    return made


if __name__ == "__main__":
    main()
