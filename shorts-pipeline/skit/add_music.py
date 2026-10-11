"""Chèn nhạc nền vào output.mp4 của một skit sau khi dựng xong (mã nguồn bộ dựng skit đã mất, chỉ còn bytecode).

  python skit/add_music.py skits/<tên>

Nhạc lấy ở library/bgm/<thể loại> (mặc định "comical", đổi bằng "bgm" trong skit.json), nhỏ hơn giọng
music_below_voice dB (config/settings.toml, cùng mức với video truyện). Bản không nhạc giữ ở work/output_khong_nhac.mp4.
Chạy lại không trộn thêm lần hai: work/music_done.txt nhớ file output đã có nhạc; dựng lại ra output mới thì trộn lại.
"""
import json
import re
import shutil
import subprocess
import sys
import tomllib
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def mean_volume(path):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.search(r"mean_volume: (-?[\d.]+) dB", out).group(1))


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True).stdout)


def add_music(project):
    project = Path(project).resolve()
    out, work = project / "output.mp4", project / "work"
    if not out.exists():
        return print("Không có output.mp4, bỏ qua nhạc nền.")
    stamp = work / "music_done.txt"
    if stamp.exists() and stamp.read_text().strip() == str(out.stat().st_mtime_ns):
        return print("output.mp4 đã có nhạc nền, bỏ qua.")
    skit = json.loads((project / "skit.json").read_text(encoding="utf-8")) if (project / "skit.json").exists() else {}
    folder = ROOT / "library" / "bgm" / skit.get("bgm", "comical")
    tracks = sorted(folder.glob("*.mp3"))
    if not tracks:
        return print(f"Không có nhạc trong {folder}, bỏ qua nhạc nền.")
    track = tracks[zlib.crc32(project.name.encode()) % len(tracks)]      # mỗi skit một bài, cố định theo tên
    below = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))["video"]["music_below_voice"]
    gain = mean_volume(out) - below - mean_volume(track)
    length = duration(out)
    work.mkdir(exist_ok=True)
    plain = work / "output_khong_nhac.mp4"
    shutil.copyfile(out, plain)
    mixed = work / "output_nhac.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(plain), "-stream_loop", "-1", "-i", str(track), "-filter_complex",
                    f"[1:a]volume={gain:.1f}dB,afade=t=in:d=1.5,afade=t=out:st={max(length - 2.5, 0):.2f}:d=2.5[m];"
                    "[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.2f}",
                    "-movflags", "+faststart", str(mixed)], check=True)
    shutil.move(mixed, out)
    stamp.write_text(str(out.stat().st_mtime_ns))
    print(f"Nhạc nền: {track.parent.name}/{track.name}, giảm {gain:.1f} dB (nhỏ hơn giọng {below} dB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    add_music(sys.argv[1])
