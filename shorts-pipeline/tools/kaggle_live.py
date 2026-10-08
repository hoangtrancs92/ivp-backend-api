"""Log ĐANG CHẠY của kernel Kaggle (lệnh `kaggle kernels logs` chỉ có log khi kernel đã chạy xong).

  python tools/kaggle_live.py <owner>/<kernel> [giây]     # in log từ đầu tới giờ, rồi thoát

Tài khoản lấy từ biến môi trường như lệnh `kaggle` (KAGGLE_API_TOKEN hoặc KAGGLE_USERNAME + KAGGLE_KEY); gọi qua
subprocess với env của từng người (tools/kaggle_quota.py: kaggle_env), như web/app.py và tools/run_kaggle.py làm.
Cách làm: mở luồng GetKernelSessionLogsStream (text/event-stream, phát lại log từ đầu), đọc tối đa vài giây rồi đóng.
"""
import json
import sys
import time


def live_log(kernel, seconds=8.0, max_bytes=2_000_000):
    from kaggle.api.kaggle_api_extended import KaggleApi
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelSessionLogsStreamRequest

    owner, slug = kernel.split("/")[:2]
    api = KaggleApi()
    api.authenticate()
    with api.build_kaggle_client() as client:
        http = client if hasattr(client, "_prepare_request") else \
            next(v for v in vars(client).values() if hasattr(v, "_prepare_request"))
        http._init_session()
        req = ApiGetKernelSessionLogsStreamRequest()
        req.user_name, req.kernel_slug, req.wait_for_logs_url_seconds = owner, slug, 10
        prepared = http._prepare_request("kernels.KernelsApiService", "GetKernelSessionLogsStream", req)
        resp = http._session.send(prepared, stream=True, timeout=(20, seconds))
        if resp.status_code != 200:
            raise RuntimeError(f"Kaggle trả {resp.status_code}: {resp.text[:200]}")
        chunks, size, start = [], 0, time.time()
        try:
            for chunk in resp.iter_content(4096):     # luồng không tự kết thúc khi kernel còn chạy: đọc đủ thì dừng
                chunks.append(chunk)
                size += len(chunk)
                if time.time() - start > seconds or size > max_bytes:
                    break
        except Exception:  # noqa: BLE001  hết thời gian đọc (luồng im lặng): dùng phần đã có
            pass
        resp.close()
    text = []
    for line in b"".join(chunks).decode("utf-8", "replace").splitlines():
        if line.startswith("data:"):
            try:
                text.append(json.loads(line[5:]).get("data", ""))
            except ValueError:
                pass
    return "".join(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(live_log(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 8.0), end="")
