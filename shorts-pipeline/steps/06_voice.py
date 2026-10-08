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
        body = r.read()
    request = urllib.request.Request(f"{VOICEVOX}/synthesis?speaker={voice['speaker']}", data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as r:
        path.write_bytes(r.read())


def main():
    video = video_dir()
    characters = load_json(CONFIG / "characters.json")
    out = video / "audio"
    out.mkdir(exist_ok=True)
    for scene in load_script(video)["scenes"]:
        wav = out / f"{scene['id']:03d}.wav"
        if wav.exists():
            continue
        if not speakable(clean(scene["text"])):  # im lặng có chủ ý: tạo khoảng lặng, không gọi TTS
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                            "-t", str(SILENT_SECONDS), str(wav)], check=True)
            print(f"audio/{wav.name}: (im lặng {SILENT_SECONDS}s) {scene['text']}")
            continue
        voice = characters[scene["speaker"]]["voice"]
        raw = out / f"{scene['id']:03d}_src.{'mp3' if voice['engine'] == 'edge' else 'wav'}"
        {"edge": edge, "voicevox": voicevox}[voice["engine"]](clean(scene["text"]), voice, raw)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", TRIM,
                        "-ar", "48000", "-ac", "1", str(wav)], check=True)
        raw.unlink()
        print(f"audio/{wav.name}: {scene['text']}")


if __name__ == "__main__":
    main()
