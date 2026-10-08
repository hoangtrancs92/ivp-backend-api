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
                return read_stream(r, model)
            error = f"{r.status_code}: {r.text[:400]}"
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
        raise LLMError(f"Model {model} không trả về chữ nào (finish_reason={finish}).")
    return text


def json_reply(text):
    """Lấy đối tượng JSON trong câu trả lời (bỏ chữ thừa, khối ```json)."""
    return json.loads(text[text.index("{"):text.rindex("}") + 1])


if __name__ == "__main__":
    if sys.argv[1:] == ["models"]:
        print("\n".join(list_models()))
