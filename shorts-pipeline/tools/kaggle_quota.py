"""Giờ GPU Kaggle của một tài khoản, lấy thẳng từ Kaggle (`kaggle quota`), không tự ước lượng.

  python tools/kaggle_quota.py            # tài khoản trong config.toml / đăng nhập đã lưu
"""
import json
import os
import subprocess


def kaggle_env(username="", key=""):
    """Biến môi trường để lệnh `kaggle` chạy bằng đúng tài khoản (giống tools/run_kaggle.py)."""
    env = {**os.environ, "PYTHONUTF8": "1"}
    for k in ("KAGGLE_API_TOKEN", "KAGGLE_USERNAME", "KAGGLE_KEY"):
        env.pop(k, None)
    if key.startswith("KGAT_"):
        env["KAGGLE_API_TOKEN"] = key
    elif key:
        env.update(KAGGLE_USERNAME=username, KAGGLE_KEY=key)
    return env


def quota(username="", key=""):
    """{"used", "remaining", "total"} theo giờ và "refresh" (ISO), hoặc {"error": ...}."""
    try:
        result = subprocess.run(["kaggle", "quota", "--format", "json"], env=kaggle_env(username, key),
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        out = result.stdout
        rows = json.loads(out[out.index("["):])
    except (ValueError, OSError, subprocess.TimeoutExpired) as e:
        return {"error": (locals().get("result") and (result.stderr or result.stdout).strip()[-300:]) or str(e)}
    gpu = next(r for r in rows if r["resource"] == "GPU")
    hours = lambda v: float(v.rstrip("h"))        # noqa: E731
    return {"used": hours(gpu["used"]), "remaining": hours(gpu["remaining"]), "total": hours(gpu["total"]),
            "refresh": gpu.get("refreshAt", "")}


if __name__ == "__main__":
    print(quota(os.environ.get("SHORTS_KAGGLE_USERNAME", ""), os.environ.get("SHORTS_KAGGLE_KEY", "")))
