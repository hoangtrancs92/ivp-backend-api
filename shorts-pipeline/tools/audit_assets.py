"""Rà mọi kịch bản ảnh mà không gọi AI/Kaggle; --apply lưu các chuẩn hóa xác định được."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "skit")]
from common import asset_problems, missing_script_images, normalize_script  # noqa: E402
from assets import missing_images, normalize_assets  # noqa: E402


def audit(apply=False):
    report = []
    for group, filename in (("videos", "script.json"), ("skits", "skit.json")):
        for path in sorted((ROOT / group).glob(f"*/{filename}")):
            entry = {"path": path.relative_to(ROOT).as_posix()}
            try:
                spec = json.loads(path.read_text(encoding="utf-8"))
                before = json.dumps(spec, ensure_ascii=False)
                if group == "videos":
                    entry["changes"] = normalize_script(spec, path.parent)
                    entry["errors"] = asset_problems(spec, path.parent)
                    entry["missing"] = missing_script_images(path.parent, spec)
                else:
                    entry["changes"], entry["errors"] = normalize_assets(spec)
                    entry["missing"] = missing_images(path.parent, spec)
                entry["applied"] = apply and json.dumps(spec, ensure_ascii=False) != before
                if entry["applied"]:
                    path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                entry["errors"] = [str(error)]
            report.append(entry)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "work" / "asset_audit.json")
    args = parser.parse_args()
    report = audit(args.apply)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for entry in report:
        if entry.get("changes") or entry.get("errors") or entry.get("missing"):
            print(f"{entry['path']}: {len(entry.get('changes', []))} sửa, "
                  f"{len(entry.get('errors', []))} lỗi khai báo, {len(entry.get('missing', []))} ảnh thiếu")
    print(f"Đã rà {len(report)} kịch bản. Báo cáo: {args.output}")


if __name__ == "__main__":
    main()
