"""Dựng video dọc từ ảnh cảnh + giọng đọc + kịch bản.

Đầu vào (cùng thư mục dự án):
  script.json       kịch bản (xem ví dụ bên dưới)
  scenes/001.png    ảnh cảnh đã ghép, tỉ lệ 9:16 (nên 1080x1920 trở lên)
  audio/001.wav     giọng đọc của từng cảnh
  music.mp3         nhạc nền (không bắt buộc)
Đầu ra:
  output.mp4        1080x1920, 30fps

Chạy:  python build_video.py            (cần ffmpeg và ffprobe trong PATH)

script.json:
{
  "title": ["Dòng tiêu đề 1", "Dòng tiêu đề 2"],
  "font": "Noto Sans CJK JP",
  "speakers": {"narrator": "#4FC3F7", "boy": "#7CD992", "mother": "#F48FB1"},
  "scenes": [
    {"id": 1, "text": "Câu thoại", "speaker": "narrator", "motion": "zoom_in"}
  ]
}
motion: zoom_in | zoom_out | pan_left | pan_right | shake | none
"""
import json
import subprocess
from pathlib import Path

W, H, FPS = 1080, 1920, 30
PAD = 0.15           # giây nghỉ sau mỗi câu
MUSIC_VOLUME = 0.12  # nhạc nền so với giọng đọc
TMP = Path("build_tmp")


def run(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def motion_filter(kind, frames):
    """Trả về chuỗi filter tạo chuyển động cho một ảnh tĩnh."""
    big = f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2}"
    centre = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    zp = lambda z, pos=centre: f"{big},zoompan=z='{z}':{pos}:d={frames}:s={W}x{H}:fps={FPS}"
    step = 0.12 / max(frames, 1)
    if kind == "zoom_in":
        return zp(f"1+{step}*on")
    if kind == "zoom_out":
        return zp(f"1.12-{step}*on")
    if kind in ("pan_left", "pan_right"):
        travel = f"(iw-iw/zoom)*on/{frames}"
        x = travel if kind == "pan_right" else f"(iw-iw/zoom)-{travel}"
        return zp("1.1", f"x='{x}':y='ih/2-(ih/zoom/2)'")
    if kind == "shake":
        return (f"{zp('1.06')},crop={W - 40}:{H - 40}:"
                f"20+14*sin(2*PI*t*9):20+14*cos(2*PI*t*7),scale={W}:{H}")
    return zp("1")


def ass_colour(hex_colour):
    r, g, b = hex_colour[1:3], hex_colour[3:5], hex_colour[5:7]
    return f"&H00{b}{g}{r}".upper()


def ass_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_subtitles(script, timings, total, path):
    font = script.get("font", "Arial")
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
        f"Style: Title,{font},92,&H0066D9FF,&H00000000,&H00000000,1,1,8,0,8,40,40,90",
    ]
    for name, colour in script["speakers"].items():
        lines.append(f"Style: {name},{font},72,&H00FFFFFF,{ass_colour(colour)},&H00000000,1,1,9,0,8,70,70,470")
    lines += ["", "[Events]", "Format: Layer, Start, End, Style, Text"]
    title = r"\N".join(script.get("title", []))
    if title:
        lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,{title}")
    for scene, (start, end) in zip(script["scenes"], timings):
        text = scene["text"].replace("\n", r"\N")
        lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},{scene['speaker']},{text}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    script = json.loads(Path("script.json").read_text(encoding="utf-8"))
    TMP.mkdir(exist_ok=True)
    clips, timings, clock = [], [], 0.0

    for scene in script["scenes"]:
        name = f"{scene['id']:03d}"
        audio = Path("audio") / f"{name}.wav"
        length = duration(audio) + PAD
        frames = round(length * FPS)
        clip = TMP / f"{name}.mp4"
        run("-i", Path("scenes") / f"{name}.png", "-i", audio,
            "-vf", motion_filter(scene.get("motion", "zoom_in"), frames) + ",format=yuv420p",
            "-af", f"apad=whole_dur={frames / FPS}", "-frames:v", frames, "-r", FPS,
            "-c:v", "libx264", "-preset", "fast", "-crf", 18, "-c:a", "aac", "-ar", 48000, "-ac", 2, clip)
        clips.append(clip)
        timings.append((clock, clock + frames / FPS))
        clock += frames / FPS
        print(f"cảnh {name}: {length:.2f}s")

    concat = TMP / "concat.txt"
    concat.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    joined = TMP / "joined.mp4"
    run("-f", "concat", "-safe", 0, "-i", concat, "-c", "copy", joined)

    subs = TMP / "subs.ass"
    write_subtitles(script, timings, clock, subs)
    video_filter = f"ass={subs.as_posix()}"
    common = ["-c:v", "libx264", "-preset", "medium", "-crf", 20, "-c:a", "aac", "-b:a", "192k",
              "-movflags", "+faststart", "output.mp4"]
    if Path("music.mp3").exists():
        run("-i", joined, "-stream_loop", -1, "-i", "music.mp3", "-filter_complex",
            f"[0:v]{video_filter}[v];[1:a]volume={MUSIC_VOLUME}[m];"
            f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "[v]", "-map", "[a]", "-t", clock, *common)
    else:
        run("-i", joined, "-vf", video_filter, *common)
    print(f"Xong: output.mp4 ({clock:.1f}s, {len(clips)} cảnh)")


if __name__ == "__main__":
    main()
