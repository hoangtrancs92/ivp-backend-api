"""Gọi model AI qua cổng chuẩn OpenAI (/v1/chat/completions): ShopAIKey, OpenAI, OpenRouter, cổng tương thích của Anthropic...

Biến môi trường (web/app.py truyền theo người dùng và lựa chọn ở trang Tạo video):
  AI_BASE_URL   mặc định https://api.shopaikey.com/v1
  AI_API_KEY    khóa của cổng (cũ: ANTHROPIC_API_KEY vẫn dùng được)
  AI_MODEL_SCRIPT, AI_MODEL_REVIEW   model viết kịch bản / duyệt ảnh (cần đọc được ảnh)

  python steps/llm.py models        # in danh sách model cổng đang có
"""
import base64
import json
import os
import sys
import time

import requests

BASE_URL = os.environ.get("AI_BASE_URL", "https://api.shopaikey.com/v1").rstrip("/")
API_KEY = os.environ.get("AI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
RETRY_CODES = {408, 409, 429, 500, 502, 503, 504, 520, 524, 529}


class LLMError(RuntimeError):
    pass


# Cổng AI tạm hết đường chạy cho một model (503 "No available channel ... model_not_found"): dùng model gần nhất còn chạy
FALLBACK = {"claude-sonnet-5-5": "claude-sonnet-5"}


class EmptyReply(LLMError):
    """Cổng AI đóng luồng mà không gửi chữ nào, không báo lỗi (ShopAIKey thỉnh thoảng bị): thử lại được."""


def headers(key=None):
    key = key or API_KEY
    if not key:
        raise LLMError("Chưa có AI API key (AI_API_KEY).")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def edit_image(image_bytes, prompt, model, mime="image/png"):
    """Sửa một ảnh bằng model ảnh qua chat/completions (gemini-*-image, gpt-image-*): gửi ảnh + lời dặn, nhận ảnh mới.
    Cổng trả ảnh trong nội dung dạng ![image](data:image/png;base64,...) hoặc trong message.images. Trả về bytes ảnh."""
    import re
    body = {"model": model, "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:{mime};base64," + base64.b64encode(image_bytes).decode()}},
        {"type": "text", "text": prompt}]}]}
    for attempt in range(4):
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", headers=headers(), json=body, timeout=(30, 600))
        except requests.RequestException as e:
            if attempt == 3:
                raise LLMError(f"Không gọi được {model}: {e}")
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code in RETRY_CODES and attempt < 3:
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code != 200:
            raise LLMError(f"{model} lỗi {r.status_code}: {r.text[:300]}")
        message = (r.json().get("choices") or [{}])[0].get("message", {})
        texts = [message.get("content") or ""] + [str(i) for i in message.get("images") or []]
        for text in texts:
            found = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", text)
            if found:
                return base64.b64decode(found.group(1))
        raise LLMError(f"{model} không trả về ảnh. Câu trả lời: {(message.get('content') or '')[:300]}")


def list_models(base_url=None, key=None):
    r = requests.get(f"{(base_url or BASE_URL).rstrip('/')}/models", headers=headers(key), timeout=30)
    if r.status_code != 200:
        raise LLMError(f"Lấy danh sách model lỗi {r.status_code}: {r.text[:300]}")
    return sorted(m["id"] for m in r.json().get("data", []))


def chat(prompt, model, image=None, max_tokens=16000, images=None):
    """Gửi một câu hỏi kèm ảnh JPEG (image: một ảnh, images: danh sách ảnh theo thứ tự "ảnh 1, ảnh 2..."), trả về chữ
    model trả lời. Chạy dạng stream để câu trả lời dài không bị quá hạn."""
    pictures = list(images or []) + ([image] if image is not None else [])
    content = prompt
    if pictures:
        content = [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(p).decode()}}
                   for p in pictures] + [{"type": "text", "text": prompt}]
    body = {"model": model, "messages": [{"role": "user", "content": content}], "stream": True, "max_tokens": max_tokens}
    for attempt in range(4):
        try:
            r = requests.post(f"{BASE_URL}/chat/completions", headers=headers(), json=body, stream=True, timeout=(30, 600))
        except requests.RequestException as e:
            error = f"mạng: {e}"
        else:
            if r.status_code == 200:
                try:
                    return read_stream(r, model)
                except EmptyReply as e:
                    error = str(e)
                    if body["model"] in FALLBACK:          # luồng rỗng thường là dấu hiệu cổng sắp báo hết đường chạy model này
                        print(f"  {body['model']}: luồng trả lời rỗng, thử lại bằng {FALLBACK[body['model']]}", flush=True)
                        body["model"] = FALLBACK[body["model"]]
                    else:
                        print(f"  {body['model']}: luồng trả lời rỗng, thử lại ({attempt + 1}/4)", flush=True)
                    continue
                except requests.RequestException as e:        # đứt kết nối giữa luồng
                    error = f"mạng giữa luồng: {e}"
                    print(f"  {model}: đứt luồng ({e.__class__.__name__}), thử lại ({attempt + 1}/4)", flush=True)
                    continue
            error = f"{r.status_code}: {r.text[:400]}"
            if r.status_code == 503 and ("No available channel" in r.text or "model_not_found" in r.text)                     and body["model"] in FALLBACK:
                print(f"  {body['model']} đang không có trên cổng AI, dùng {FALLBACK[body['model']]}", flush=True)
                body["model"] = FALLBACK[body["model"]]
                continue
            if r.status_code == 400 and "max_tokens" in r.text and "max_tokens" in body:
                body["max_completion_tokens"] = body.pop("max_tokens")   # model OpenAI đời mới đổi tên tham số này
                continue
            if r.status_code not in RETRY_CODES:
                raise LLMError(f"Model {model} lỗi {error}")
        print(f"  gọi {model} lỗi ({error[:120]}), thử lại sau {5 * (attempt + 1)} giây", flush=True)
        time.sleep(5 * (attempt + 1))
    raise LLMError(f"Model {model} lỗi sau nhiều lần thử: {error}")


def read_stream(r, model):
    r.encoding = "utf-8"    # stream "text/event-stream" thường không khai charset; requests mặc định Latin-1 làm vỡ chữ Nhật, Việt
    parts, finish = [], None
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except ValueError:
            continue
        if chunk.get("error"):
            raise LLMError(f"Model {model} lỗi: {chunk['error']}")
        for choice in chunk.get("choices", []):
            parts.append((choice.get("delta") or {}).get("content") or "")
            finish = choice.get("finish_reason") or finish
    text = "".join(parts).strip()
    if finish == "length":
        raise LLMError(f"Model {model} hết max_tokens giữa chừng, câu trả lời bị cắt.")
    if not text:
        if finish is None:                                  # luồng bị cắt, không có lý do kết thúc: lỗi tạm thời
            raise EmptyReply(f"Model {model} không trả về chữ nào (finish_reason=None).")
        raise LLMError(f"Model {model} không trả về chữ nào (finish_reason={finish}).")
    return text


def json_reply(text):
    """Lấy đối tượng JSON trong câu trả lời (bỏ chữ thừa, khối ```json). Model hay viết vài câu giải thích trước JSON (video 044),
    có khi có cả dấu ngoặc trong đó: thử từng dấu "{" và lấy đối tượng hợp lệ lớn nhất."""
    try:
        return json.loads(text[text.index("{"):text.rindex("}") + 1])
    except ValueError:
        pass
    decoder, best = json.JSONDecoder(), None
    for start in (i for i, ch in enumerate(text) if ch == "{"):
        try:
            found, end = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(found, dict) and (best is None or end - start > best[0]):
            best = (end - start, found)
    if best is None:
        raise ValueError("không có JSON trong câu trả lời")
    return best[1]


if __name__ == "__main__":
    if sys.argv[1:] == ["models"]:
        print("\n".join(list_models()))
