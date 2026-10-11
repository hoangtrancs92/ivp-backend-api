"""Benchmark clip image-to-video trên Kaggle trước khi chốt độ phân giải, quant, số video mỗi tuần
(tài liệu "Ảnh và clip trên Kaggle", mục "Benchmark trước, làm pipeline sau").

  python tools/i2v_bench.py videos/<tên> 3,7,12 [--sizes 576x1024,704x960,544x736] [--quant Q5_K_M] [--gpus 2]
                                                [--seconds 4] [--dry-run]

Chọn 3 cảnh có tranh cả cảnh (full/NNN.png): một cảnh đi, một cảnh nói cận mặt, một cảnh rộng có chữ ở nền.
Mỗi cảnh x mỗi cỡ một clip, 1 seed. Mặc định 1 GPU; --gpus 2 để thử 2 server song song (RAM có vượt không).
Kết quả về work/i2v_bench/clips/: <cảnh>_<cỡ>.mp4 và results.json (thời gian từng clip, điểm QA, "_peaks":
VRAM đỉnh từng GPU, RAM đỉnh). Clip đầu tiên mỗi GPU gồm cả thời gian nạp model. Chạy lần nữa với --quant khác để so.
Ghi chú hành động cho từng cảnh lấy từ "i2v_prompt" / "action" trong script.json.
"""
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def option(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    args = [a for k, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[k - 1].startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    video, ids = Path(args[0]).resolve(), [int(x) for x in args[1].split(",")]
    i2v = tomllib.loads((ROOT / "config" / "settings.toml").read_text(encoding="utf-8"))["i2v"]
    sizes = [tuple(map(int, s.split("x"))) for s in option("--sizes", "576x1024,704x960,544x736").split(",")]
    seconds = float(option("--seconds", 4))
    scenes = {s["id"]: s for s in json.loads((video / "script.json").read_text(encoding="utf-8"))["scenes"]}
    bench = ROOT / "work" / "i2v_bench"
    shutil.rmtree(bench, ignore_errors=True)
    (bench / "full").mkdir(parents=True)
    clips = []
    for sid in ids:
        source = video / "full" / f"{sid:03d}.png"
        if not source.exists():
            sys.exit(f"Không có {source}: benchmark cần tranh cả cảnh")
        shutil.copy(source, bench / "full" / source.name)
        scene = scenes.get(sid, {})
        for w, h in sizes:
            clips.append({"name": f"clip_{sid:03d}_{w}x{h}", "image": f"full__{source.name}", "width": w, "height": h,
                          "frames": round(seconds * i2v["fps"] / 4) * 4 + 1, "seed": sid * 10,
                          "prompt": scene.get("i2v_prompt") or scene.get("action") or "the people move slightly"})
    override = {"seeds": 1, "gpus": int(option("--gpus", 1))}
    if "--quant" in sys.argv:
        override["quant"] = option("--quant", i2v["quant"])
    (bench / "jobs.json").write_text(json.dumps({"jobs": [], "clips": clips, "i2v_override": override},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(clips)} clip benchmark, ghi đè {override}")
    cmd = [sys.executable, str(ROOT / "tools" / "run_kaggle.py"), str(bench)] + (["--dry-run"] if "--dry-run" in sys.argv else [])
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
