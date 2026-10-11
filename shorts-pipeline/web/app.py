"""Trang web điều khiển pipeline cho nhiều người dùng, mỗi người một tài khoản Kaggle / Hugging Face / Anthropic.

  cd web; npm install; npm run build    # một lần, và mỗi khi sửa giao diện (web/src, React)
  python web/app.py                    # http://127.0.0.1:8000, chỉ máy này mở được
  python web/app.py --host 0.0.0.0     # cho máy khác cùng mạng LAN mở, qua http://<IP máy này>:8000
  python web/app.py --add-user <tên> <mật khẩu> [--admin]    # tạo tài khoản đăng nhập hoặc đặt lại mật khẩu

Người dùng đăng nhập, nhập đề tài (hoặc cả câu chuyện); tools/auto.py chạy trọn từ kịch bản tới output.mp4.
Quyền: admin quản lý thành viên và mọi video; user chỉ sửa hồ sơ của mình và chạy / dừng / xóa video của mình.
Dữ liệu nằm ở data/ (đã có trong .gitignore): users.json (hồ sơ, mật khẩu đã băm, khóa), sessions.json,
runs.json (lịch sử chạy), logs/. Đề tài và người tạo của từng video lưu ở videos/<tên>/prompt.txt, meta.json.
Khóa API không bao giờ gửi ngược về trình duyệt.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import tomllib
import unicodedata
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "steps"))
from kaggle_quota import kaggle_env, quota   # noqa: E402
import llm                       # noqa: E402
from common import image_stamp, reject_image, review_items   # noqa: E402

DATA = ROOT / "data"
LOGS = DATA / "logs"
USERS = DATA / "users.json"
RUNS = DATA / "runs.json"
SESSIONS = DATA / "sessions.json"
SETTINGS = DATA / "settings.json"
FEEDBACK = DATA / "feedback.json"
CATEGORIES = {   # hạng mục góp ý: khớp với các bước của quy trình để biết cần sửa chỗ nào
    "script": "Kịch bản",
    "image": "Hình ảnh nhân vật",
    "background": "Ảnh nền",
    "animation": "Chuyển động",
    "voice": "Giọng đọc",
    "subtitle": "Phụ đề, chữ",
    "music": "Nhạc, âm thanh",
    "other": "Khác",
}
DEFAULT_SETTINGS = {           # admin sửa ở trang Cài đặt AI
    "ai_base_url": "https://api.shopaikey.com/v1",
    "models": ["claude-sonnet-5-5", "claude-sonnet-5", "gpt-5.6-luna"],
    "script_model": "claude-sonnet-5",
    "review_model": "claude-sonnet-5-5",
    "image_model": "gemini-2.5-flash-image",   # sửa ảnh lỗi của video đã xong (tools/fix_scenes.py)
    "telegram_bot_token": "",  # bot tạo qua @BotFather; trống = tắt thông báo Telegram
    "telegram_bot_username": "shorts_video_imgpro_bot",   # tự cập nhật (getMe) khi lưu token mới
    "public_url": "",          # địa chỉ trang web (vd link Cloudflare) để gắn vào tin nhắn; tùy chọn
    "pixabay_key": "",         # ảnh thật cho video so sánh (steps/fetch_photos.py), dùng trước Pexels
    "pexels_key": "",          # dự phòng; Pexels tạm ngừng cấp khóa mới (2026-10). Cả hai trống = dựng không có ảnh thật
}
NOTIFY_MODES = ("all", "errors", "")   # thông báo Telegram: lỗi + xong + chờ duyệt / chỉ lỗi / tắt
VIDEOS = ROOT / "videos"
STORY_MODES = ("auto", "twist", "sukatto", "touching", "comedy", "kaigai", "contrast")   # kiểu chuyện = steps/01_script.py STORY_MODES
SKITS = ROOT / "skits"                         # chức năng Tiểu phẩm (skit/), tách riêng khỏi videos/
DIST = Path(__file__).with_name("dist")        # bản build của giao diện React (npm run build)
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
         ".png": "image/png", ".jpg": "image/jpeg", ".mp4": "video/mp4"}
KEYS = ("kaggle_key", "hf_token", "ai_api_key")
ONLINE_SECONDS = 60          # trình duyệt báo danh mỗi 20 giây; quá 60 giây không thấy thì coi là đã rời
QUOTA_SECONDS = 300          # hỏi lại giờ GPU của Kaggle sau mỗi 5 phút (hoặc khi bấm làm mới)
SESSION_DAYS = 30

ACTIONS = {   # việc: (tên, lệnh chạy ở ROOT, khóa bắt buộc)
    "auto": ("Tạo video", lambda v: ["tools/auto.py", f"videos/{v}"], ["kaggle_key", "ai_api_key"]),
    "fix": ("Sửa cảnh bằng AI", lambda v: ["tools/fix_scenes.py", f"videos/{v}", "--edit"], ["ai_api_key"]),
    "fix_apply": ("Áp dụng ảnh sửa", lambda v: ["tools/fix_scenes.py", f"videos/{v}", "--apply"], []),
    "skit": ("Tạo tiểu phẩm", lambda v: ["skit/auto.py", f"skits/{v}"], ["kaggle_key", "ai_api_key"]),
    "upload_lora": ("Đưa LoRA lên Kaggle",
                    lambda v: ["tools/run_kaggle.py", "loras/style.safetensors", "--upload-lora"], ["kaggle_key"]),
}

lock = threading.Lock()
online = {}                  # tên người dùng -> lần báo danh cuối
procs = {}                   # id lần chạy -> Popen
quotas = {}                  # tên người dùng -> {"used", "remaining", "total", "refresh", "checked"} hoặc {"error"}


class Denied(Exception):
    """Chưa đăng nhập (401) hoặc không đủ quyền (403)."""

    def __init__(self, message, code=403):
        super().__init__(message)
        self.code = code


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def first_start():
    """Lần đầu: tạo hồ sơ đầu tiên từ config.toml cũ (nếu có). Lần chạy dở do tắt server thì đánh dấu bị ngắt."""
    if not USERS.exists() and (ROOT / "config.toml").exists():
        cfg = tomllib.loads((ROOT / "config.toml").read_text(encoding="utf-8"))
        kg, keys = cfg.get("kaggle", {}), cfg.get("keys", {})
        if kg.get("username"):
            save(USERS, {kg["username"]: {"kaggle_username": kg["username"], "kaggle_key": kg.get("key", ""),
                                          "hf_token": keys.get("hf_token", ""),
                                          "ai_api_key": keys.get("anthropic_api_key", ""),
                                          "role": "admin", "created": time.time()}})
    users = load(USERS, {})
    for u in users.values():                    # tên cũ của khóa AI
        if "anthropic_api_key" in u:
            u["ai_api_key"] = u.get("ai_api_key") or u.pop("anthropic_api_key")
            u.pop("anthropic_api_key", None)
    if users:
        save(USERS, users)
    runs = load(RUNS, [])
    for r in runs:
        if r["status"] == "running":
            if r.get("pid") and process_exit_code(r["pid"]) is None:     # tiến trình vẫn chạy: gắn lại, không coi là bị ngắt
                threading.Thread(target=watch_pid, args=(r["id"], r["pid"], r["user"]), daemon=True).start()
                print(f"Gắn lại việc đang chạy: {r['video'] or r['label']} (pid {r['pid']})", flush=True)
            else:
                r.update(status="interrupted", ended=r.get("ended") or time.time())
    save(RUNS, runs)
    if not any(u.get("password") for u in load(USERS, {}).values()):
        print("Chưa có tài khoản đăng nhập nào. Tạo bằng: python web/app.py --add-user <tên> <mật khẩu> --admin")


# ---------- tiến trình chạy nền ----------

def process_exit_code(pid):
    """None nếu tiến trình còn chạy, mã thoát nếu đã xong, -1 nếu không còn tìm thấy."""
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return None
        except OSError:
            return -1
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION; không dùng os.kill (trên Windows là giết)
    if not handle:
        return -1
    try:
        code = wintypes.DWORD()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return -1
        return None if code.value == 259 else code.value  # 259 = STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def finish_run(run_id, code, name):
    with lock:
        runs = load(RUNS, [])
        for r in runs:
            if r["id"] == run_id and r["status"] == "running":
                status = {0: "done", 3: "waiting"}.get(code, "failed")    # 3: tools/auto.py dừng chờ người duyệt ảnh
                r.update(status=status, code=code, ended=time.time())
                threading.Thread(target=notify_run, args=(dict(r),), daemon=True).start()
        save(RUNS, runs)
    refresh_quota(name, force=True)


# ---------- thông báo Telegram (tùy chọn) ----------

def telegram(method, token, payload=None):
    """Gọi Bot API của Telegram; trả về phần "result" hoặc ném ValueError có lời giải thích."""
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8", "replace"))
        except ValueError:
            body = {"description": str(e), "error_code": e.code}
    except OSError as e:
        raise ValueError(f"Không gọi được Telegram: {e}")
    if not body.get("ok"):
        hint = {401: " (token bot sai)", 404: " (token bot sai)",
                400: " (chat ID sai, hoặc chưa nhắn /start cho bot)",
                403: " (đã chặn bot, hoặc chưa nhắn /start cho bot)"}.get(body.get("error_code"), "")
        raise ValueError(f"Telegram báo lỗi: {body.get('description', 'không rõ')}{hint}")
    return body["result"]


def send_telegram(chat_id, text):
    token = settings().get("telegram_bot_token")
    if not token:
        raise ValueError("Admin chưa nhập token bot Telegram ở trang Cài đặt.")
    telegram("sendMessage", token, {"chat_id": chat_id, "text": text, "disable_web_page_preview": True})


def error_lines(run_id, count=6):
    """Mấy dòng cuối có nội dung của log: đủ để biết lỗi gì mà không phải mở trang."""
    path = LOGS / f"{run_id}.log"
    if not path.exists():
        return ""
    lines = [l.strip() for l in path.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    return "\n".join(l[:200] for l in lines[-count:])


def notify_run(run):
    """Báo cho chủ video (và người bấm chạy, nếu khác) khi việc xong / lỗi / chờ duyệt, theo lựa chọn trong hồ sơ."""
    conf = settings()
    if run["status"] not in ("done", "failed", "waiting") or not conf.get("telegram_bot_token"):
        return
    users = load(USERS, {})
    title = run.get("video") or run["label"]
    script = VIDEOS / run["video"] / "script.json" if run.get("video") else None
    if script and script.exists():
        try:
            title = " ".join(json.loads(script.read_text(encoding="utf-8")).get("title", [])) or title
        except ValueError:
            pass
    minutes = round(((run.get("ended") or time.time()) - run["started"]) / 60)
    head = {"done": "✅ Xong", "failed": "❌ Lỗi", "waiting": "👀 Chờ bạn duyệt ảnh"}[run["status"]]
    text = f"{head}: {title}\n📁 {run.get('video') or '-'} · 👤 {run['user']} · ⏱ {minutes} phút"
    if run["status"] == "failed":
        text += f"\n\n{error_lines(run['id'])}"
    if conf.get("public_url"):
        text += f"\n\n🔗 {conf['public_url']}"
    sent = set()
    for name in dict.fromkeys([run["user"], run.get("by") or run["user"]]):
        u = users.get(name, {})
        chat, mode = u.get("telegram_chat_id"), u.get("telegram_notify", "")
        if not chat or chat in sent or not mode or (mode == "errors" and run["status"] != "failed"):
            continue
        sent.add(chat)
        try:
            send_telegram(chat, text[:4000])
        except ValueError as e:
            print(f"Telegram ({name}): {e}", flush=True)


def telegram_chats():
    """Các cuộc trò chuyện vừa nhắn cho bot (getUpdates), để người dùng tìm chat ID của mình."""
    token = settings().get("telegram_bot_token")
    if not token:
        raise ValueError("Admin chưa nhập token bot Telegram ở trang Cài đặt.")
    chats = {}
    for update in telegram("getUpdates", token, {"limit": 100}):
        message = update.get("message") or update.get("my_chat_member") or {}
        chat = message.get("chat") or {}
        if chat.get("id"):
            name = chat.get("title") or " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
            chats[str(chat["id"])] = {"id": str(chat["id"]), "name": name, "username": chat.get("username", "")}
    return {"chats": list(chats.values())[::-1]}


def watch_pid(run_id, pid, name):
    """Theo dõi việc chạy từ trước khi server khởi động lại (không còn đối tượng Popen)."""
    while (code := process_exit_code(pid)) is None:
        time.sleep(5)
    finish_run(run_id, code, name)


# ---------- đăng nhập ----------

def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def check_password(password, stored):
    if not stored:
        return False
    _, salt, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, salt), stored)


def login(body):
    name, password = body.get("name", "").strip(), body.get("password", "")
    u = load(USERS, {}).get(name)
    if not u or not check_password(password, u.get("password", "")):
        time.sleep(1)                           # làm chậm đoán mật khẩu
        raise Denied("Sai tên đăng nhập hoặc mật khẩu.", 401)
    token = secrets.token_urlsafe(32)
    with lock:
        sessions = {t: s for t, s in load(SESSIONS, {}).items() if s["expires"] > time.time()}
        sessions[token] = {"user": name, "expires": time.time() + SESSION_DAYS * 86400}
        save(SESSIONS, sessions)
    online[name] = time.time()
    return token


def logout(token):
    with lock:
        sessions = load(SESSIONS, {})
        sessions.pop(token, None)
        save(SESSIONS, sessions)


def session_user(token):
    s = load(SESSIONS, {}).get(token or "")
    if not s or s["expires"] < time.time():
        return None
    u = load(USERS, {}).get(s["user"])
    return {"name": s["user"], "role": u.get("role", "user")} if u else None


def add_user_cli(args):
    name, password = args[0], args[1]
    with lock:
        users = load(USERS, {})
        u = users.setdefault(name, {"kaggle_username": "", "created": time.time()})
        u["password"] = hash_password(password)
        u["role"] = "admin" if "--admin" in args else u.get("role", "user")
        save(USERS, users)
    print(f"Đã lưu tài khoản {name} ({u['role']}).")


# ---------- cài đặt AI ----------

def settings():
    return {**DEFAULT_SETTINGS, **load(SETTINGS, {})}


def public_settings():
    """Cài đặt gửi về trình duyệt: không có token bot, chỉ báo đã có hay chưa."""
    conf = settings()
    return {**{k: v for k, v in conf.items() if k not in ("telegram_bot_token", "pexels_key", "pixabay_key")},
            "telegram_bot": bool(conf.get("telegram_bot_token")), "pexels": bool(conf.get("pexels_key")),
            "pixabay": bool(conf.get("pixabay_key"))}


def save_settings(me, body):
    if me["role"] != "admin":
        raise Denied("Chỉ admin sửa được cài đặt AI.")
    models = [m.strip() for m in re.split(r"[\n,]+", body.get("models", "")) if m.strip()]
    models = list(dict.fromkeys(models))
    if not models:
        raise ValueError("Cần ít nhất một model.")
    url = body.get("ai_base_url", "").strip().rstrip("/")
    if not re.match(r"https?://", url):
        raise ValueError("Endpoint phải bắt đầu bằng https://")
    old = settings()
    public_url = body.get("public_url", "").strip().rstrip("/")
    if public_url and not re.match(r"https?://", public_url):
        raise ValueError("Địa chỉ trang web phải bắt đầu bằng https://")
    new = {"ai_base_url": url, "models": models, "public_url": public_url,
           "telegram_bot_token": body.get("telegram_bot_token", "").strip() or old.get("telegram_bot_token", ""),
           "telegram_bot_username": old.get("telegram_bot_username", ""),
           "pexels_key": body.get("pexels_key", "").strip() or old.get("pexels_key", ""),
           "pixabay_key": body.get("pixabay_key", "").strip() or old.get("pixabay_key", ""),
           "script_model": body.get("script_model") if body.get("script_model") in models else models[0],
           "review_model": body.get("review_model") if body.get("review_model") in models else models[0],
           "image_model": (body.get("image_model") or "").strip() or old.get("image_model") or DEFAULT_SETTINGS["image_model"]}
    if new["telegram_bot_token"] and (new["telegram_bot_token"] != old.get("telegram_bot_token")
                                      or not new["telegram_bot_username"]):
        # token mới: hỏi Telegram tên bot (để hiện link t.me/<bot> cho mọi người); token sai thì báo ngay
        new["telegram_bot_username"] = telegram("getMe", new["telegram_bot_token"]).get("username", "")
    save(SETTINGS, new)


def fetch_models(me, body):
    """Hỏi cổng AI danh sách model, bằng khóa của người đang đăng nhập."""
    key = load(USERS, {}).get(me["name"], {}).get("ai_api_key")
    if not key:
        raise ValueError("Hồ sơ của bạn chưa có AI API key.")
    try:
        return {"models": llm.list_models(body.get("ai_base_url") or settings()["ai_base_url"], key)}
    except (llm.LLMError, OSError) as e:
        raise ValueError(str(e)[:300])


# ---------- duyệt ảnh bằng mắt ----------

def runner_for(me, name):
    """Tài khoản chạy việc của video: chủ video (khóa Kaggle, HF, AI và giờ GPU của chủ), kể cả khi admin bấm.
    Video không rõ chủ (tạo từ trước khi có đăng nhập) thì là người bấm."""
    owner_name = owner(VIDEOS / name, load(RUNS, []))
    return owner_name if owner_name in load(USERS, {}) else me["name"]


def review_action(me, body):
    """Người duyệt xem ảnh trên web rồi: approve (ảnh ổn, làm tiếp), regen (vẽ lại ảnh đã chọn),
    ai (AI chấm ảnh đã chọn, chỉ ảnh trượt bị vẽ lại). Sau đó chạy lại tools/auto.py."""
    d = video_dir(body.get("video", ""))
    can_manage_video(me, d.name)
    if any(r["video"] == d.name and r["status"] == "running" for r in load(RUNS, [])):
        raise ValueError("Video đang chạy, chờ xong đã.")
    action = body.get("action")
    valid = {it["key"] for it in review_items(d)}
    keys = [k for k in body.get("keys", []) if k in valid]
    runner = runner_for(me, d.name)
    notes = {k: str(v).strip()[:500] for k, v in (body.get("notes") or {}).items() if k in valid and str(v).strip()}
    if notes and action in ("regen", "ai"):        # ghi chú khi vẽ lại: make_jobs.py dịch và ghép vào prompt
        saved = load(d / "review" / "notes.json", {})
        for k, text in notes.items():
            saved[k] = {"text": text, "by": me["name"], "at": time.time()}
        save(d / "review" / "notes.json", saved)
    if action == "approve":
        from run_local import missing_images
        if missing_images(d):
            raise ValueError("Video còn thiếu ảnh, chưa duyệt được.")
        save(d / "review" / "approved.json", {"stamp": image_stamp(d), "by": me["name"], "at": time.time()})
        return start_run(runner, "auto", d.name, by=me["name"])
    if not keys and action != "ai_all":
        raise ValueError("Chọn ít nhất một ảnh.")
    if action == "regen":
        check_user(runner, "auto")                # thiếu khóa thì báo trước khi bỏ ảnh
        for k in keys:
            reject_image(d, k)
        return start_run(runner, "auto", d.name, by=me["name"])
    if action == "ai":
        return start_run(runner, "auto", d.name, extra_env={"SHORTS_AI_CHECK": ",".join(keys)}, by=me["name"])
    if action == "ai_all":                      # bận, để AI duyệt hết rồi tự làm tiếp
        meta = load(d / "meta.json", {})
        save(d / "meta.json", {**meta, "review_mode": "ai"})
        return start_run(runner, "auto", d.name, by=me["name"])
    raise ValueError("Thao tác không hợp lệ.")


# ---------- góp ý cho video ----------

REACTIONS = ("like", "love", "haha", "wow", "sad", "angry")


def feedback_items():
    """Đọc góp ý; bản cũ lưu "likes" (danh sách người thích) thì đổi sang "reactions" {người: cảm xúc}."""
    items = load(FEEDBACK, [])
    for f in items:
        if "reactions" not in f:
            f["reactions"] = {u: "like" for u in f.get("likes", [])}
        f.pop("likes", None)
    return items


def add_feedback(me, body):
    text = body.get("text", "").strip()
    if not 2 <= len(text) <= 4000:
        raise ValueError("Góp ý từ 2 đến 4000 ký tự.")
    with lock:
        items = feedback_items()
        parent = body.get("parent")
        if parent:
            root = next((f for f in items if f["id"] == parent), None)
            if not root:
                raise ValueError("Góp ý gốc không còn.")
            video = root["video"]
        else:
            video = video_dir(body.get("video", "")).name
        category = body.get("category") if body.get("category") in CATEGORIES else None
        rating = body.get("rating") if body.get("rating") in (1, 2, 3, 4, 5) else None
        at = body.get("at")
        at = round(float(at), 1) if isinstance(at, (int, float)) and 0 <= at < 36000 else None
        item = {"id": secrets.token_hex(6), "video": video, "user": me["name"], "text": text,
                "category": None if parent else category, "rating": None if parent else rating, "at": at,
                "parent": parent or None, "reactions": {}, "resolved": False, "created": time.time()}
        items.append(item)
        save(FEEDBACK, items)
    return item


def change_feedback(me, body, action):
    with lock:
        items = feedback_items()
        item = next((f for f in items if f["id"] == body.get("id")), None)
        if not item:
            raise ValueError("Góp ý không còn.")
        if action == "react":                   # bấm lại đúng cảm xúc đang chọn = bỏ
            reaction = body.get("reaction")
            if reaction not in REACTIONS:
                raise ValueError("Cảm xúc không hợp lệ.")
            if item["reactions"].get(me["name"]) == reaction:
                item["reactions"].pop(me["name"])
            else:
                item["reactions"][me["name"]] = reaction
        elif action == "resolve":
            if me["role"] != "admin":
                raise Denied("Chỉ admin đánh dấu đã xử lý.")
            item["resolved"] = not item["resolved"]
            item["resolved_by"] = me["name"] if item["resolved"] else None
            item["note"] = body.get("note", "").strip()[:1000] if item["resolved"] else ""
        elif action == "delete":
            if me["role"] != "admin" and item["user"] != me["name"]:
                raise Denied("Bạn chỉ xóa được góp ý của mình.")
            items = [f for f in items if f["id"] != item["id"] and f.get("parent") != item["id"]]
        save(FEEDBACK, items)


def export_feedback(query):
    """Bản tổng hợp Markdown để đọc lại hoặc dán cho AI phân tích cách cải thiện quy trình."""
    items = feedback_items()
    show_resolved = query.get("resolved", ["0"])[0] == "1"
    roots = [f for f in items if not f["parent"] and (show_resolved or not f["resolved"])]
    replies = {}
    for f in items:
        if f["parent"]:
            replies.setdefault(f["parent"], []).append(f)
    when = lambda t: time.strftime("%d/%m/%Y %H:%M", time.localtime(t))   # noqa: E731
    rated = [f["rating"] for f in roots if f["rating"]]
    lines = [f"# Tổng hợp góp ý video ({time.strftime('%d/%m/%Y')})", "",
             f"- {len(roots)} góp ý {'(gồm cả đã xử lý)' if show_resolved else 'chưa xử lý'}, "
             f"{len({f['video'] for f in roots})} video, {len({f['user'] for f in roots})} người góp ý",
             f"- Điểm trung bình: {sum(rated) / len(rated):.1f}/5 ({len(rated)} lượt chấm)" if rated else "- Chưa có lượt chấm điểm", ""]
    for key, label in CATEGORIES.items():
        group = [f for f in roots if (f["category"] or "other") == key]
        if not group:
            continue
        lines += [f"## {label} ({len(group)})", ""]
        for f in sorted(group, key=lambda f: (-len(f["reactions"]), f["created"])):
            meta = [f["video"], f["user"], when(f["created"])]
            if f["rating"]:
                meta.append(f"{f['rating']}/5")
            if f["at"] is not None:
                meta.append(f"tại {int(f['at'] // 60)}:{int(f['at'] % 60):02d}")
            if f["reactions"]:
                counts = {}
                for r in f["reactions"].values():
                    counts[r] = counts.get(r, 0) + 1
                names = {"like": "thích", "love": "yêu thích", "haha": "haha", "wow": "wow", "sad": "buồn", "angry": "phẫn nộ"}
                meta.append(", ".join(f"{n} {names[r]}" for r, n in sorted(counts.items(), key=lambda x: -x[1])))
            if f["resolved"]:
                meta.append("ĐÃ XỬ LÝ" + (f": {f['note']}" if f.get("note") else ""))
            lines.append(f"- **[{' · '.join(meta)}]** {f['text']}")
            lines += [f"  - ↳ {r['user']}: {r['text']}" for r in replies.get(f["id"], [])]
        lines.append("")
    return "\n".join(lines).encode("utf-8")


# ---------- giờ GPU từ Kaggle ----------

def refresh_quota(name, force=False):
    u = load(USERS, {}).get(name)
    old = quotas.get(name, {})
    if not u or (not force and time.time() - old.get("checked", 0) < QUOTA_SECONDS) or old.get("busy"):
        return
    quotas[name] = {**old, "busy": True}
    if u.get("kaggle_key"):
        quotas[name] = {**quota(u["kaggle_username"], u["kaggle_key"]), "checked": time.time()}
    else:
        quotas[name] = {"error": "Chưa có Kaggle token", "checked": time.time()}


def quota_loop():
    while True:
        for name in list(load(USERS, {})):
            refresh_quota(name)
        time.sleep(30)


# ---------- video ----------

def slug(text):
    text = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    words = re.sub(r"[^a-z0-9]+", " ", text.encode("ascii", "ignore").decode().lower()).split()
    return "-".join(words[:5]) or "video"


def new_video_name(prompt):
    numbers = [int(m[1]) for d in VIDEOS.iterdir() if (m := re.match(r"(\d{3})-", d.name))]
    return f"{max(numbers, default=0) + 1:03d}-{slug(prompt)}"


def thumbnail(d):
    for pattern in ("work/preview/001.png", "cutouts/001.png", "characters/001.png"):
        if (d / pattern).exists():
            return pattern
    return None


def owner(d, runs):
    meta = load(d / "meta.json", {})
    return meta.get("owner") or next((r["user"] for r in runs if r["video"] == d.name), "")


def review_info(d, script):
    """Ảnh cần duyệt bằng mắt (khi video đang chờ duyệt): đường dẫn, cảnh, kết quả AI chấm gần nhất nếu ảnh chưa đổi."""
    ai = load(d / "review" / "images.json", {})
    notes = load(d / "review" / "notes.json", {})
    scenes = {sc["id"]: sc for sc in script.get("scenes", [])}
    items = []
    for it in review_items(d, script):
        mtime = it["path"].stat().st_mtime_ns
        if it["kind"] == "background":
            url = f"/library/backgrounds/{it['path'].name}" if it["path"].parent.name == "backgrounds" and \
                it["path"].parent.parent.name == "library" else f"/videos/{d.name}/backgrounds/{it['path'].name}"
            caption = f"Nền: {Path(it['key']).stem}"
        else:
            url = f"/videos/{d.name}/{it['key']}"
            sc = scenes.get(it["scene"], {})
            caption = f"Cảnh {it['scene']}" + (" · tư thế 2" if it["key"].endswith("_alt.png") else "") + \
                f" · {sc.get('text', '').replace(chr(10), ' ')}"
        result = ai.get(it["key"])
        note = notes.get(it["key"], {}).get("text", "")
        items.append({"key": it["key"], "kind": it["kind"], "url": f"{url}?v={mtime}", "caption": caption, "note": note,
                      "ai": result if result and result.get("mtime") == mtime else None})
    return items


def scene_list(me, name):
    """Các cảnh của video đã xong, kèm ảnh bố cục (work/preview) để người xem chọn cảnh cần sửa."""
    d = video_dir(name)
    script = load(d / "script.json", {})
    times = {t["id"]: (t["start"], t["end"]) for t in load(d / "work" / "timings.json", [])}
    subs = d / "work" / "build" / "subs.ass"
    if not times and subs.exists():            # video dựng trước khi có timings.json: lấy giờ từ phụ đề (mỗi cảnh một dòng)
        clock = lambda t: sum(float(x) * m for x, m in zip(t.split(":"), (3600, 60, 1)))   # noqa: E731
        lines = re.findall(r"^Dialogue: 2,([\d:.]+),([\d:.]+),", subs.read_text(encoding="utf-8"), re.M)
        times = {sc["id"]: (clock(a), clock(b)) for sc, (a, b) in zip(script.get("scenes", []), lines)}
    scenes = []
    for sc in script.get("scenes", []):
        preview = d / "work" / "preview" / f"{sc['id']:03d}.png"
        images = [f.name for f in sorted((d / "characters").glob(f"{sc['id']:03d}*.png"))
                  if len(f.stem) == 3 or f.stem[3] == "_"]
        scenes.append({"id": sc["id"], "text": sc.get("text", ""), "images": images,
                       "start": times.get(sc["id"], (None, None))[0], "end": times.get(sc["id"], (None, None))[1],
                       "thumb": small_preview(d, preview)})
    return {"scenes": scenes}


kaggle_logs = {}             # tài khoản Kaggle -> (giờ lấy, kết quả): hỏi Kaggle tối đa 20 giây một lần


def kaggle_log(me, name):
    """Log đang chạy của kernel Kaggle (tài khoản của chủ video): trạng thái và các dòng in ra, để theo dõi trên trang."""
    d = video_dir(name)
    u = load(USERS, {}).get(owner(d, load(RUNS, [])), {})
    account = u.get("kaggle_username")
    if not account or not u.get("kaggle_key"):
        raise ValueError("Chủ video chưa có tài khoản Kaggle trong hồ sơ.")
    cached = kaggle_logs.get(account)
    if not cached or time.time() - cached[0] > 20:
        kernel, env = f"{account}/shorts-gen", kaggle_env(account, u["kaggle_key"])
        call = lambda *a: subprocess.run(["kaggle", "kernels", *a, kernel], env=env, capture_output=True, text=True,  # noqa: E731
                                         encoding="utf-8", errors="replace", timeout=60).stdout
        try:
            status = call("status")
            if "running" in status.lower() or "queued" in status.lower():   # đang chạy: `kernels logs` còn rỗng
                raw = ""
                text = subprocess.run([sys.executable, str(ROOT / "tools" / "kaggle_live.py"), kernel, "8"], env=env,
                                      capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90).stdout
            else:
                raw = call("logs")
                try:                            # log là mảng JSON {stream_name, time, data}
                    text = "".join(e.get("data", "") for e in json.loads(raw[raw.index("["):]))
                except ValueError:
                    text = raw
        except (OSError, subprocess.TimeoutExpired) as e:
            raise ValueError(f"Không hỏi được Kaggle: {e}")
        found = re.search(r'status "([^"]+)"', status)
        last = load(ROOT / "build" / account / "last_run.json", {})
        cached = (time.time(), {"kernel": kernel, "status": (found[1] if found else status.strip()).split(".")[-1].lower(),
                                "text": text[-60000:], "video": last.get("video", "")})
        kaggle_logs[account] = cached
    return {**cached[1], "checked": cached[0]}


def small_preview(d, preview):
    """Ảnh nhỏ của ảnh bố cục (PNG 1080x1920 ~2 MB -> JPEG 360 px ~25 KB) cho lưới chọn cảnh; 70 cảnh tải nhẹ, không lỗi."""
    if not preview.exists():
        return None
    thumb = d / "work" / "thumbs" / f"{preview.stem}.jpg"
    if not thumb.exists() or thumb.stat().st_mtime < preview.stat().st_mtime:
        from PIL import Image
        thumb.parent.mkdir(parents=True, exist_ok=True)
        tmp = thumb.with_name(f"{thumb.stem}.{threading.get_ident()}.tmp.jpg")   # ghi xong mới đổi tên: hai lần mở
        with Image.open(preview) as im:                                         # cùng lúc không đọc phải ảnh dở dang
            im.convert("RGB").resize((360, round(im.height * 360 / im.width)), Image.LANCZOS).save(tmp, quality=82)
        os.replace(tmp, thumb)
    return f"/videos/{d.name}/work/thumbs/{thumb.name}?v={thumb.stat().st_mtime_ns}"


def fix_scenes(me, body):
    """Bấm "Sửa cảnh bằng AI": model ảnh sửa ảnh của các cảnh đã chọn rồi dựng lại video (khóa AI của chủ video)."""
    name = video_dir(body.get("video", "")).name
    can_manage_video(me, name)
    scenes, images = {}, {}
    for item in body.get("scenes") or []:
        if str(item.get("id", "")).isdigit():
            scenes[str(int(item["id"]))] = str(item.get("note") or "")[:600]
    for item in body.get("images") or []:
        if re.fullmatch(r"\d{3}[\w.-]*\.png", str(item.get("name", ""))):
            images[item["name"]] = str(item.get("note") or "")[:600]
    if not scenes and not images:
        raise ValueError("Chọn ít nhất một cảnh cần sửa.")
    if len(scenes) > 15 or len(images) > 30:
        raise ValueError("Mỗi lần sửa tối đa 15 cảnh.")
    request = {"scenes": scenes, "images": images}
    return start_run(runner_for(me, name), "fix", name, extra_env={"SHORTS_FIX": json.dumps(request, ensure_ascii=False)},
                     by=me["name"])


def fix_apply(me, body):
    """Xem xong bản sửa: thay các ảnh được chọn vào video rồi dựng lại; không chọn ảnh nào thì chỉ bỏ các bản sửa."""
    name = video_dir(body.get("video", "")).name
    can_manage_video(me, name)
    folder = VIDEOS / name / "work" / "fix"
    names = [n for n in body.get("apply") or [] if re.fullmatch(r"[\w.-]+\.png", str(n)) and (folder / n).exists()]
    if not names:
        shutil.rmtree(folder, ignore_errors=True)
        return {"discarded": True}
    return start_run(runner_for(me, name), "fix_apply", name,
                     extra_env={"SHORTS_FIX": json.dumps({"apply": names})}, by=me["name"])


def fix_review(d):
    """Bản sửa AI đang chờ người xem: ảnh cũ / ảnh mới từng ảnh, cảnh, ghi chú, số lần vẽ."""
    items = load(d / "work" / "fix" / "state.json", {}).get("items", {})
    out = []
    for name, it in sorted(items.items()):
        after, before = d / "work" / "fix" / name, d / "characters" / name
        if after.exists() and before.exists():
            out.append({"name": name, "scene": it.get("scene"), "note": it.get("note", ""), "tries": it.get("tries", 1),
                        "before": f"/videos/{d.name}/characters/{name}?v={before.stat().st_mtime_ns}",
                        "after": f"/videos/{d.name}/work/fix/{name}?v={after.stat().st_mtime_ns}"})
    return out or None


def fix_info(d, run):
    """Tiến trình sửa cảnh của lần chạy này; file cũ (lần sửa trước) hoặc chưa có file thì chỉ báo là đang sửa."""
    data = load(d / "work" / "fix_progress.json", None)
    if not data or data.get("started", 0) < run["started"] - 5:
        return {"scenes": [], "total": 0, "done": 0, "phase": "ai", "current": ""}
    return data


def video_info(d, runs):
    script = load(d / "script.json", {})
    progress = load(d / "progress.json", None)
    if progress:
        kaggle = load(d / "work" / "kaggle_progress.json", None)
        if kaggle and progress["steps"].get("kaggle", {}).get("status") == "running":
            progress["kaggle"] = kaggle
    mine = [r for r in runs if r["video"] == d.name]
    prompt = d / "prompt.txt"
    return {"name": d.name, "title": " ".join(script.get("title", [])), "scenes": len(script.get("scenes", [])),
            "prompt": prompt.read_text(encoding="utf-8") if prompt.exists() else "",
            "output": (d / "output.mp4").exists(), "thumb": thumbnail(d), "progress": progress,
            "owner": owner(d, runs), "updated": d.stat().st_mtime, "run": mine[-1] if mine else None,
            # kiểu kể: meta.json (lúc tạo), không có thì lấy từ kịch bản (01_script.py ghi voice_mode khi viết)
            "models": {**{k: v for k, v in load(d / "meta.json", {}).items()
                          if k in ("script_model", "review_model", "review_mode", "voice_mode", "story_mode", "style", "country")},
                       **({} if "voice_mode" in load(d / "meta.json", {}) or not script.get("voice_mode")
                          else {"voice_mode": script["voice_mode"]})},
            # tên giọng VOICEVOX đã dùng: phải ghi ở mô tả khi đăng video
            "credits": (d / "credits.txt").read_text(encoding="utf-8").strip() if (d / "credits.txt").exists() else "",
            "posted": posted_info(d),
            # đang sửa cảnh bằng AI (tools/fix_scenes.py): cảnh nào, AI sửa được mấy ảnh, đang ở bước nào
            "fix": fix_info(d, mine[-1]) if mine and mine[-1]["status"] == "running"
            and mine[-1].get("action") in ("fix", "fix_apply") else None,
            "fix_review": fix_review(d) if not mine or mine[-1]["status"] != "running" else None,
            "review": review_info(d, script) if progress and progress["steps"].get("review", {}).get("status") == "waiting"
            and (not mine or mine[-1]["status"] != "running") else None}


STARTED = time.time()      # giờ server khởi động: app.py sửa sau giờ này thì server đang chạy code cũ (video 044)


def state(me):
    users, runs, now = load(USERS, {}), load(RUNS, []), time.time()
    public = []
    for name, u in users.items():
        mine = [r for r in runs if r["user"] == name]
        q = {k: v for k, v in quotas.get(name, {}).items() if k != "busy"}
        public.append({"name": name, "role": u.get("role", "user"), "kaggle_username": u.get("kaggle_username", ""),
                       **{k: bool(u.get(k)) for k in KEYS}, "can_login": bool(u.get("password")),
                       "telegram_chat_id": u.get("telegram_chat_id", "") if me["role"] == "admin" or me["name"] == name else "",
                       "telegram_notify": u.get("telegram_notify", ""),
                       "online": now - online.get(name, 0) < ONLINE_SECONDS,
                       "running": [r["video"] or r["label"] for r in mine if r["status"] == "running"],
                       "runs": len(mine), "videos": len({r["video"] for r in mine if r["video"]}),
                       "quota": q, "last_seen": max([online.get(name, 0)] + [r["started"] for r in mine])})
    videos = [video_info(d, runs) for d in VIDEOS.iterdir() if d.is_dir() and not d.name.startswith("_")]
    videos.sort(key=lambda v: v["name"], reverse=True)
    skits = sorted((skit_info(d, runs) for d in SKITS.iterdir() if d.is_dir()) if SKITS.exists() else [],
                   key=lambda v: v["name"], reverse=True)
    return {"me": me, "users": public, "videos": videos, "skits": skits, "runs": runs[-100:][::-1], "settings": public_settings(),
            "stale": Path(__file__).stat().st_mtime > STARTED,
            "feedback": feedback_items(), "categories": CATEGORIES,
            "stats": {"users": len(users), "online": sum(u["online"] for u in public),
                      "active": len({r["user"] for r in runs if r["status"] == "running"}),
                      "running": sum(r["status"] == "running" for r in runs),
                      "videos": sum(v["output"] for v in videos)}}


def posted_info(d):
    """Đã đăng TikTok chưa (người dùng tự đánh dấu): {"by", "at"} hoặc None. Lưu trong meta.json của video / tiểu phẩm."""
    meta = load(d / "meta.json", {})
    return meta.get("posted") or None


def set_posted(me, body):
    """Đánh dấu / bỏ đánh dấu đã đăng TikTok. Chủ video hoặc admin."""
    kind, name = body.get("kind"), body.get("name", "")
    if kind == "skit":
        d = skit_dir(name)
        can_manage_skit(me, name)
    else:
        d = video_dir(name)
        can_manage_video(me, name)
    if not (d / "output.mp4").exists():
        raise ValueError("Video chưa dựng xong.")
    with lock:
        meta = load(d / "meta.json", {})
        if body.get("posted"):
            meta["posted"] = {"by": me["name"], "at": time.time()}
        else:
            meta.pop("posted", None)
        save(d / "meta.json", meta)
    return {"posted": meta.get("posted")}


def can_manage_video(me, name):
    """Admin: mọi video. User: video mình tạo."""
    if me["role"] == "admin":
        return
    if owner(VIDEOS / name, load(RUNS, [])) != me["name"]:
        raise Denied("Bạn chỉ thao tác được trên video của mình.")


def video_dir(name):
    if not re.fullmatch(r"[\w.-]{1,80}", name or "") or not (VIDEOS / name).is_dir():
        raise ValueError("Không có video này.")
    return VIDEOS / name


def delete_video(me, name):
    """Xóa cả thư mục video cho nhẹ máy. Đang chạy thì dừng trước (lô đã gửi lên Kaggle vẫn chạy nốt trên Kaggle)."""
    d = video_dir(name)
    can_manage_video(me, name)
    for r in load(RUNS, []):
        if r["video"] == name and r["status"] == "running":
            stop_run(me, r["id"])
            time.sleep(1)                       # chờ tiến trình nhả file trên Windows
    for attempt in range(5):
        try:
            return shutil.rmtree(d)
        except OSError:
            time.sleep(1)
    raise ValueError("Chưa xóa hết được thư mục (có file đang mở?), thử lại sau ít giây.")


# ---------- tiểu phẩm (skit/) ----------

SKIT_FORMATS = ("loop", "list", "incident", "story", "misunderstanding", "interview", "reaction", "free")   # = skit/write.py

def skit_dir(name):
    if not re.fullmatch(r"skit-[\w.-]{1,80}", name or "") or not (SKITS / name).is_dir():
        raise ValueError("Không có tiểu phẩm này.")
    return SKITS / name


def skit_info(d, runs):
    skit = load(d / "skit.json", {})
    progress = load(d / "progress.json", None)
    if progress:
        kaggle = load(d / "work" / "kaggle_progress.json", None)
        if kaggle and progress["steps"].get("kaggle", {}).get("status") == "running":
            progress["kaggle"] = kaggle
    mine = [r for r in runs if r["video"] == d.name]
    meta = load(d / "meta.json", {})
    timing = load(d / "audio" / "timing.json", {})
    first = next(iter(skit.get("cast", {})), None)
    thumb = f"cutouts/{first}_normal.png" if first and (d / "cutouts" / f"{first}_normal.png").exists() else None
    faces = [f"cutouts/{n}_normal.png" for n in skit.get("cast", {}) if (d / "cutouts" / f"{n}_normal.png").exists()]
    steps = (progress or {}).get("steps", {})
    current = next((s for s in steps.values() if s.get("status") in ("running", "failed")), None)
    return {"name": d.name, "title": " ".join(skit.get("title", [])), "format": skit.get("format"),
            "lines": len(skit.get("lines", [])), "cast": len(skit.get("cast", {})),
            "inserts": len({l.get("insert") for l in skit.get("lines", []) if l.get("insert")}),
            "seconds": timing.get("total"), "prompt": (d / "prompt.txt").read_text(encoding="utf-8")
            if (d / "prompt.txt").exists() else "", "output": (d / "output.mp4").exists(), "thumb": thumb,
            "progress": progress, "owner": meta.get("owner", ""), "updated": d.stat().st_mtime,
            "run": mine[-1] if mine else None, "script_model": meta.get("script_model", ""),
            "poster": "work/poster.jpg" if (d / "work" / "poster.jpg").exists() else None, "faces": faces,
            "step": {"label": current["label"], "status": current["status"], "note": current.get("note", "")} if current else None,
            "steps_done": sum(s.get("status") in ("done", "skipped") for s in steps.values()), "steps_total": len(steps),
            "grade": skit.get("grade"), "directed": bool(skit.get("directed")), "structure": skit.get("structure") or [],
            "credits": (d / "credits.txt").read_text(encoding="utf-8").strip() if (d / "credits.txt").exists() else "",
            "posted": posted_info(d)}


def can_manage_skit(me, name):
    if me["role"] != "admin" and load(SKITS / name / "meta.json", {}).get("owner") != me["name"]:
        raise Denied("Bạn chỉ thao tác được trên tiểu phẩm của mình.")


def generate_skit(me, body):
    prompt = (body.get("prompt") or "").strip()
    if len(prompt) < 5:
        raise ValueError("Nhập ý tưởng tiểu phẩm (ít nhất vài chữ).")
    check_user(me["name"], "skit")
    conf = settings()
    with lock:
        SKITS.mkdir(exist_ok=True)
        numbers = [int(m[1]) for d in SKITS.iterdir() if (m := re.match(r"skit-(\d{3})-", d.name))]
        name = f"skit-{max(numbers, default=0) + 1:03d}-{slug(prompt)}"
        (SKITS / name).mkdir(parents=True)
        (SKITS / name / "prompt.txt").write_text(prompt, encoding="utf-8")
        save(SKITS / name / "meta.json", {"owner": me["name"], "created": time.time(),
                                          "script_model": body.get("script_model") or conf["script_model"],
                                          "format": body.get("format") if body.get("format") in SKIT_FORMATS else ""})
    try:
        return start_run(me["name"], "skit", name, prompt)
    except ValueError:
        shutil.rmtree(SKITS / name, ignore_errors=True)
        raise


def resume_skit(me, name):
    d = skit_dir(name)
    can_manage_skit(me, name)
    owner_name = load(d / "meta.json", {}).get("owner")
    return start_run(owner_name if owner_name in load(USERS, {}) else me["name"], "skit", name, by=me["name"])


def delete_skit(me, name):
    d = skit_dir(name)
    can_manage_skit(me, name)
    for r in load(RUNS, []):
        if r["video"] == name and r["status"] == "running":
            stop_run(me, r["id"])
            time.sleep(1)
    for attempt in range(5):
        try:
            return shutil.rmtree(d)
        except OSError:
            time.sleep(1)
    raise ValueError("Chưa xóa hết được thư mục (có file đang mở?), thử lại sau ít giây.")


# ---------- người dùng ----------

def save_user(me, body):
    name = body.get("name", "").strip()
    if not re.fullmatch(r"[\w.-]{1,40}", name):
        raise ValueError("Tên đăng nhập 1-40 ký tự: chữ, số, '.', '-', '_' (không dấu cách).")
    admin = me["role"] == "admin"
    if not admin and name != me["name"]:
        raise Denied("Bạn chỉ sửa được hồ sơ của mình.")
    with lock:
        users = load(USERS, {})
        if name not in users and not admin:
            raise Denied("Chỉ admin thêm được thành viên.")
        u = users.setdefault(name, {"created": time.time(), "role": "user"})
        u["kaggle_username"] = body.get("kaggle_username", "").strip() or u.get("kaggle_username", "")
        for k in KEYS:                          # ô khóa để trống = giữ khóa cũ
            if body.get(k, "").strip():
                u[k] = body[k].strip()
        if "telegram_chat_id" in body:          # không bí mật: hiện lại trên trang; để trống = tắt
            chat = str(body.get("telegram_chat_id") or "").strip()
            if chat and not re.fullmatch(r"-?\d{3,20}", chat):
                raise ValueError("Chat ID Telegram là một dãy số (nhóm thì có dấu - ở đầu).")
            u["telegram_chat_id"] = chat
            u["telegram_notify"] = body.get("telegram_notify") if chat and body.get("telegram_notify") in NOTIFY_MODES else ""
        if admin and body.get("role") in ("admin", "user") and name != me["name"]:
            u["role"] = body["role"]
        password = body.get("password", "")
        if password:
            if len(password) < 6:
                raise ValueError("Mật khẩu ít nhất 6 ký tự.")
            if not admin and not check_password(body.get("old_password", ""), u.get("password", "")):
                raise ValueError("Mật khẩu hiện tại không đúng.")
            u["password"] = hash_password(password)
        if not u.get("password"):
            raise ValueError("Cần đặt mật khẩu để thành viên đăng nhập được.")
        save(USERS, users)
    threading.Thread(target=refresh_quota, args=(name, True), daemon=True).start()


def delete_user(me, name):
    if me["role"] != "admin":
        raise Denied("Chỉ admin xóa được thành viên.")
    if name == me["name"]:
        raise ValueError("Không tự xóa tài khoản của mình được.")
    with lock:
        users = load(USERS, {})
        if any(r["user"] == name and r["status"] == "running" for r in load(RUNS, [])):
            raise ValueError("Người dùng này đang có việc chạy.")
        users.pop(name, None)
        save(USERS, users)
        sessions = {t: s for t, s in load(SESSIONS, {}).items() if s["user"] != name}
        save(SESSIONS, sessions)
    quotas.pop(name, None)


# ---------- chạy việc ----------

def generate(me, body):
    """Tạo video mới từ đề tài: lưu prompt.txt, meta.json rồi chạy tools/auto.py."""
    prompt = body.get("prompt", "").strip()
    if len(prompt) < 5:
        raise ValueError("Nhập đề tài hoặc câu chuyện (ít nhất vài chữ).")
    check_user(me["name"], "auto")
    conf = settings()
    chosen = {k: body.get(k) or conf[k] for k in ("script_model", "review_model")}
    chosen["review_mode"] = body.get("review_mode") if body.get("review_mode") in ("manual", "ai", "none") else "none"
    chosen["voice_mode"] = body.get("voice_mode") if body.get("voice_mode") in ("narration", "dialogue") else "narration"
    chosen["story_mode"] = body.get("story_mode") if body.get("story_mode") in STORY_MODES else "auto"
    chosen["country"] = str(body.get("country") or "CHN")[:3].upper()     # "Nhật Bản vs nước khác" (steps/compare_facts.py)
    chosen["style"] = "new" if body.get("style") == "new" else "classic"
    chosen["contrast_mode"] = bool(body.get("contrast_mode"))
    with lock:
        name = new_video_name(prompt)
        (VIDEOS / name).mkdir(parents=True)
        (VIDEOS / name / "prompt.txt").write_text(prompt, encoding="utf-8")
        save(VIDEOS / name / "meta.json", {"owner": me["name"], "created": time.time(), **chosen})
    try:
        return start_run(me["name"], "auto", name, prompt)
    except ValueError:
        shutil.rmtree(VIDEOS / name, ignore_errors=True)
        raise


def check_user(name, action):
    users = load(USERS, {})
    if name not in users:
        raise ValueError("Không có người dùng này.")
    labels = {"kaggle_key": "Kaggle token", "ai_api_key": "AI API key", "hf_token": "HF token"}
    missing = [labels[k] for k in ACTIONS[action][2] if not users[name].get(k)]
    if missing:
        raise ValueError(f"Việc này chạy bằng khóa của {name} (chủ video), nhưng hồ sơ của {name} chưa có: "
                         f"{', '.join(missing)}. {name} cần vào Hồ sơ và khóa API để bổ sung.")
    q = quotas.get(name, {})
    if action == "auto" and q.get("remaining") is not None and q["remaining"] < 0.5:
        raise ValueError(f"Tài khoản Kaggle của {name} chỉ còn {q['remaining']:.1f} giờ GPU, không đủ cho một lô.")
    return users[name]


def start_run(name, action, video="", prompt="", extra_env=None, by=None):
    if action not in ACTIONS:
        raise ValueError("Việc không hợp lệ.")
    u = check_user(name, action)
    if action == "auto" and not (VIDEOS / video / "prompt.txt").exists() and not (VIDEOS / video / "script.json").exists():
        raise ValueError(f"videos/{video} chưa có đề tài hay kịch bản.")
    label, command, _ = ACTIONS[action]
    with lock:
        runs = load(RUNS, [])
        busy = [r for r in runs if r["status"] == "running"]
        if video and any(r["video"] == video for r in busy):
            raise ValueError(f"{video} đang chạy rồi.")
        users = load(USERS, {})
        if "kaggle_key" in ACTIONS[action][2] and any(
                users.get(r["user"], {}).get("kaggle_username") == u["kaggle_username"] and "kaggle_key" in
                ACTIONS.get(r["action"], ("", None, []))[2] for r in busy):
            raise ValueError(f"Tài khoản Kaggle {u['kaggle_username']} đang chạy một việc khác, chờ xong đã.")
        run_id = time.strftime("%Y%m%d-%H%M%S") + f"-{len(runs)}"
        args = command(video)
        run = {"id": run_id, "user": name, "by": by or name, "action": action, "label": label, "video": video, "prompt": prompt,
               "command": "python " + " ".join(args), "status": "running", "started": time.time(),
               "ended": None, "code": None}
        runs.append(run)
        save(RUNS, runs)

    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1",
           "SHORTS_KAGGLE_USERNAME": u["kaggle_username"], "SHORTS_KAGGLE_KEY": u.get("kaggle_key", ""),
           "SHORTS_HF_TOKEN": u.get("hf_token", "")}
    for k in ("ANTHROPIC_API_KEY", "AI_API_KEY", "CLAUDE_MODEL"):   # chỉ dùng khóa của người chạy, không lấy nhầm của máy
        env.pop(k, None)
    conf = settings()
    meta = load((SKITS if action == "skit" else VIDEOS) / video / "meta.json", {}) if video else {}
    env.update(AI_BASE_URL=conf["ai_base_url"], AI_API_KEY=u.get("ai_api_key", ""),
               AI_MODEL_SCRIPT=meta.get("script_model") or conf["script_model"],
               AI_MODEL_REVIEW=meta.get("review_model") or conf["review_model"],
               AI_MODEL_IMAGE=conf.get("image_model") or DEFAULT_SETTINGS["image_model"],
               PEXELS_API_KEY=conf.get("pexels_key", ""), PIXABAY_API_KEY=conf.get("pixabay_key", ""),
               SHORTS_REVIEW_MODE=meta.get("review_mode", "manual"),
               SHORTS_VOICE_MODE=meta.get("voice_mode", "narration"), SHORTS_STORY_MODE=meta.get("story_mode", "auto"),
               SHORTS_COUNTRY=meta.get("country", "CHN"),
               SHORTS_CONTRAST_MODE="1" if meta.get("contrast_mode") else "0",
               SHORTS_STYLE=meta.get("style", "classic"),
               SKIT_FORMAT=meta.get("format", ""))
    env.update(extra_env or {})
    LOGS.mkdir(parents=True, exist_ok=True)
    log = open(LOGS / f"{run_id}.log", "w", encoding="utf-8")
    log.write(f"[{name}] {run['command']}\n\n")
    log.flush()
    proc = subprocess.Popen([sys.executable, *args], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    procs[run_id] = proc
    with lock:                                  # nhớ pid để server khởi động lại vẫn theo dõi được
        runs = load(RUNS, [])
        for r in runs:
            if r["id"] == run_id:
                r["pid"] = proc.pid
        save(RUNS, runs)
    threading.Thread(target=wait, args=(run_id, proc, log, name), daemon=True).start()
    return {"id": run_id, "video": video}


def wait(run_id, proc, log, name):
    code = proc.wait()
    log.close()
    procs.pop(run_id, None)
    finish_run(run_id, code, name)


def stop_run(me, run_id):
    proc = procs.get(run_id)
    run = next((r for r in load(RUNS, []) if r["id"] == run_id), None)
    pid = proc.pid if proc else (run or {}).get("pid")
    if not pid or not run or run["status"] != "running":
        raise ValueError("Việc này không còn chạy.")
    with lock:
        runs = load(RUNS, [])
        run = next((r for r in runs if r["id"] == run_id), None)
        if run and me["role"] != "admin" and run["user"] != me["name"]:
            raise Denied("Bạn chỉ dừng được việc của mình.")
        if run:
            run.update(status="stopped", ended=time.time())
        save(RUNS, runs)
    if os.name == "nt":      # dừng cả cây tiến trình (auto.py -> run_kaggle.py -> kaggle)
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True)
    else:
        os.kill(pid, 9)          # lô đã gửi lên Kaggle vẫn chạy tiếp trên Kaggle; bấm "Chạy tiếp" để lấy kết quả


# ---------- HTTP ----------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, kind="application/json; charset=utf-8", headers=()):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def token(self):
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        return cookie["sid"].value if "sid" in cookie else None

    def me(self):
        me = session_user(self.token())
        if not me:
            raise Denied("Chưa đăng nhập.", 401)
        return me

    def send_file(self, path, download_name=None):
        """Gửi file, hỗ trợ Range để trình phát video tua được. download_name: trình duyệt lưu file về máy người xem."""
        size = path.stat().st_size
        kind = TYPES.get(path.suffix, "application/octet-stream")
        if download_name:
            return self.reply(200, path.read_bytes(), kind,
                              [("Content-Disposition", f'attachment; filename="{download_name}"')])
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if not m or not (m[1] or m[2]):
            return self.reply(200, path.read_bytes(), kind, [("Accept-Ranges", "bytes")])
        start = int(m[1]) if m[1] else size - int(m[2])
        end = min(int(m[2]) if m[1] and m[2] else size - 1, size - 1)
        with open(path, "rb") as f:
            f.seek(start)
            data = f.read(end - start + 1)
        self.reply(206, data, kind, [("Accept-Ranges", "bytes"), ("Content-Range", f"bytes {start}-{end}/{size}")])

    def do_GET(self):
        url = urlparse(self.path)
        path = unquote(url.path)
        try:
            if path == "/" or path.startswith("/assets/"):
                file = (DIST / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
                if not file.is_relative_to(DIST) or not file.is_file():
                    return self.reply(404, "Chưa build giao diện: cd web; npm install; npm run build".encode("utf-8"),
                                      "text/plain; charset=utf-8")
                return self.send_file(file)
            me = self.me()
            if path == "/api/state":
                return self.reply(200, state(me))
            if path == "/api/feedback/export":
                name = f"gop-y-{time.strftime('%Y%m%d')}.md"
                return self.reply(200, export_feedback(parse_qs(url.query)), "text/markdown; charset=utf-8",
                                  [("Content-Disposition", f'attachment; filename="{name}"')])
            if path == "/api/kaggle_log":
                return self.reply(200, kaggle_log(me, parse_qs(url.query).get("video", [""])[0]))
            if path == "/api/scenes":
                return self.reply(200, scene_list(me, parse_qs(url.query).get("video", [""])[0]))
            if path == "/api/log":
                run_id = parse_qs(url.query).get("id", [""])[0]
                file = LOGS / f"{run_id}.log"
                if not re.fullmatch(r"[\w-]+", run_id) or not file.exists():
                    return self.reply(404, {"error": "Không có log."})
                return self.reply(200, {"text": file.read_text(encoding="utf-8", errors="replace")[-60000:]})
            m = re.fullmatch(r"/library/backgrounds/([\w.-]+\.png)", path)
            if m and (ROOT / "library" / "backgrounds" / m[1]).is_file():
                return self.send_file(ROOT / "library" / "backgrounds" / m[1])
            m = re.fullmatch(r"/videos/([\w.-]+)/(output\.mp4|work/preview/\d{3}\.png|work/thumbs/\d{3}\.jpg|work/fix/[\w.-]+\.png|cutouts/001\.png|"
                             r"(?:characters|backgrounds)/[\w.-]+\.png)", path)
            if m and (VIDEOS / m[1] / m[2]).is_file():
                download = "download" in parse_qs(url.query) and m[2] == "output.mp4"
                return self.send_file(VIDEOS / m[1] / m[2], f"{m[1]}.mp4" if download else None)
            m = re.fullmatch(r"/skits/(skit-[\w.-]+)/(output\.mp4|cutouts/[\w.-]+\.png|work/frames/[\w.-]+\.png|work/poster\.jpg)", path)
            if m and (SKITS / m[1] / m[2]).is_file():
                download = "download" in parse_qs(url.query) and m[2] == "output.mp4"
                return self.send_file(SKITS / m[1] / m[2], f"{m[1]}.mp4" if download else None)
            self.reply(404, {"error": "Không có."})
        except Denied as e:
            self.reply(e.code, {"error": str(e)})

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            path = urlparse(self.path).path
            if path == "/api/login":
                token = login(body)
                return self.reply(200, {}, headers=[("Set-Cookie", f"sid={token}; Path=/; HttpOnly; SameSite=Lax; "
                                                                   f"Max-Age={SESSION_DAYS * 86400}")])
            if path == "/api/logout":
                logout(self.token())
                return self.reply(200, {}, headers=[("Set-Cookie", "sid=; Path=/; Max-Age=0")])
            me = self.me()
            if path == "/api/ping":
                online[me["name"]] = time.time()
                return self.reply(200, {})
            if path == "/api/generate":
                return self.reply(200, generate(me, body))
            if path == "/api/resume":
                name = video_dir(body.get("video", "")).name
                can_manage_video(me, name)
                return self.reply(200, start_run(runner_for(me, name), "auto", name, by=me["name"]))
            if path == "/api/posted":
                return self.reply(200, set_posted(me, body))
            if path == "/api/skit/generate":
                return self.reply(200, generate_skit(me, body))
            if path == "/api/skit/resume":
                return self.reply(200, resume_skit(me, body.get("skit", "")))
            if path == "/api/skit/delete":
                delete_skit(me, body.get("skit", ""))
                return self.reply(200, {})
            if path == "/api/fix":
                return self.reply(200, fix_scenes(me, body))
            if path == "/api/fix/apply":
                return self.reply(200, fix_apply(me, body))
            if path == "/api/upload_lora":
                target = body.get("user") or me["name"]
                if target != me["name"] and me["role"] != "admin":
                    raise Denied("Bạn chỉ đưa LoRA lên tài khoản của mình.")
                return self.reply(200, start_run(target, "upload_lora"))
            if path == "/api/quota":
                refresh_quota(body.get("user") or me["name"], force=True)
            elif path == "/api/user":
                save_user(me, body)
            elif path == "/api/user/delete":
                delete_user(me, body.get("name", ""))
            elif path == "/api/stop":
                stop_run(me, body.get("id", ""))
            elif path == "/api/video/delete":
                delete_video(me, body.get("video", ""))
            elif path == "/api/review":
                return self.reply(200, review_action(me, body))
            elif path == "/api/feedback":
                return self.reply(200, add_feedback(me, body))
            elif path in ("/api/feedback/react", "/api/feedback/resolve", "/api/feedback/delete"):
                change_feedback(me, body, path.rsplit("/", 1)[1])
            elif path == "/api/settings":
                save_settings(me, body)
            elif path == "/api/telegram/test":
                chat = str(body.get("chat_id") or load(USERS, {}).get(me["name"], {}).get("telegram_chat_id") or "")
                if not chat:
                    raise ValueError("Nhập chat ID trước.")
                send_telegram(chat, f"🔔 Thử thông báo từ trang làm video: tin của {body.get('user') or me['name']} sẽ gửi về đây.")
            elif path == "/api/telegram/chats":
                return self.reply(200, telegram_chats())
            elif path == "/api/models":
                return self.reply(200, fetch_models(me, body))
            else:
                return self.reply(404, {"error": "Không có."})
            self.reply(200, {})
        except Denied as e:
            self.reply(e.code, {"error": str(e)})
        except ValueError as e:
            self.reply(400, {"error": str(e)})


def fresh_path():
    """PATH mới nhất của Windows (máy + tài khoản): chương trình cài sau khi mở cửa sổ (ffmpeg qua winget) vẫn chạy được."""
    if os.name != "nt":
        return
    import winreg
    parts = os.environ.get("PATH", "").split(os.pathsep)
    for root, key in [(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")]:
        try:
            with winreg.OpenKey(root, key) as k:
                value = os.path.expandvars(winreg.QueryValueEx(k, "Path")[0])
        except OSError:
            continue
        parts += [p for p in value.split(os.pathsep) if p and p not in parts]
    os.environ["PATH"] = os.pathsep.join(parts)


def main():
    sys.stdout.reconfigure(encoding="utf-8")    # console Windows mặc định không in được tiếng Việt
    if "--add-user" in sys.argv:
        return add_user_cli(sys.argv[sys.argv.index("--add-user") + 1:])
    fresh_path()
    if not shutil.which("ffmpeg"):
        print("Cảnh báo: không tìm thấy ffmpeg, bước giọng đọc và dựng video sẽ lỗi.", flush=True)
    host = sys.argv[sys.argv.index("--host") + 1] if "--host" in sys.argv else "127.0.0.1"
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    first_start()
    threading.Thread(target=quota_loop, daemon=True).start()
    print(f"Mở http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}  (Ctrl+C để tắt)", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
