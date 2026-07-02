"""AI-assisted menu photo parsing (v0.9).

Sends a photo of a paper/printed menu to a vision-capable LLM and asks it to
extract a structured list of menu items (name, price, and any 口味/加購-style
option groups), in the exact shape `schemas.MenuItemIn` already expects.
The result is handed back to the frontend as *draft* items for a human to
review/fix on the 品項清單 editor before actually saving the restaurant --
this never writes to the database itself.

Provider order: Gemini first (GEMINI_API_KEY), falling back to OpenAI
(OPENAI_API_KEY) if Gemini isn't configured or the call fails for any
reason (missing key, network error, rate limit, model refused, malformed
response, ...). If neither key is set (or both fail), raises MenuParseError
with a message meant to be shown directly to the user.

Both providers are called via plain REST (httpx) instead of pulling in
their official SDKs -- one small dependency instead of two heavier ones, and
"send an image + ask for JSON matching this schema" is simple enough that
the SDKs don't buy much here.
"""
import json
import os
import re

import httpx

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

REQUEST_TIMEOUT = 60  # vision calls are slower than a normal text completion

PROMPT = (
    "這是一張餐廳菜單的照片。請幫我把上面每一個品項整理成 JSON 陣列,每個品項包含:\n"
    "- name:品項名稱(去掉多餘符號,用繁體中文)\n"
    "- price:價格(整數,台幣;看不清楚就填 0)\n"
    "- options:這個品項的客製化選項群組陣列(沒有就給空陣列 []),每個群組包含:\n"
    "  - option_group:群組名稱,例如「口味」「甜度」「熟度」「加購」\n"
    "  - option_type:只能是 radio(單選,例如口味/甜度/熟度)或 checkbox(可多選,例如加購配料)\n"
    "  - option_name:選項名稱,例如「原味」「半糖」「加大」\n"
    "  - extra_price:這個選項要額外加價的金額(整數),沒有加價就填 0\n"
    "只回傳 JSON 本身,不要加任何說明文字、不要用 markdown 的 ```區塊包起來。"
    "如果照片完全看不出任何品項,回傳空陣列 []。"
)

# Gemini's responseSchema dialect (its own OpenAPI-style Schema object --
# note the UPPERCASE type names, this is NOT standard JSON Schema).
_GEMINI_SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "price": {"type": "INTEGER"},
            "options": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "option_group": {"type": "STRING"},
                        "option_type": {"type": "STRING", "enum": ["radio", "checkbox"]},
                        "option_name": {"type": "STRING"},
                        "extra_price": {"type": "INTEGER"},
                    },
                    "required": ["option_group", "option_type", "option_name", "extra_price"],
                },
            },
        },
        "required": ["name", "price", "options"],
    },
}

# OpenAI structured outputs (strict mode) require standard JSON Schema
# (lowercase types), every property listed in "required", and
# additionalProperties: false at every object level. Top-level must be an
# object, not a bare array, hence the {"items": [...]} wrapper.
_OPENAI_SCHEMA = {
    "name": "menu_items",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "price": {"type": "integer"},
                        "options": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "option_group": {"type": "string"},
                                    "option_type": {"type": "string", "enum": ["radio", "checkbox"]},
                                    "option_name": {"type": "string"},
                                    "extra_price": {"type": "integer"},
                                },
                                "required": ["option_group", "option_type", "option_name", "extra_price"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["name", "price", "options"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


class MenuParseError(Exception):
    pass


def _split_data_url(data_url: str) -> tuple[str, str]:
    """"data:image/jpeg;base64,/9j/4AA..." -> ("image/jpeg", "/9j/4AA...")"""
    m = re.match(r"^data:([^;]+);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        raise MenuParseError("圖片格式錯誤,請重新上傳照片")
    return m.group(1), m.group(2)


def _call_gemini(mime_type: str, b64_data: str) -> list[dict]:
    if not GEMINI_API_KEY:
        raise MenuParseError("Gemini API key not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                {"text": PROMPT},
            ],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _GEMINI_SCHEMA,
        },
    }
    resp = httpx.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _call_openai(mime_type: str, b64_data: str) -> list[dict]:
    if not OPENAI_API_KEY:
        raise MenuParseError("OpenAI API key not configured")
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": OPENAI_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}},
            ],
        }],
        "response_format": {"type": "json_schema", "json_schema": _OPENAI_SCHEMA},
    }
    resp = httpx.post(url, headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                       json=body, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return json.loads(text)["items"]


def parse_menu_photo(image_data_url: str) -> list[dict]:
    mime_type, b64_data = _split_data_url(image_data_url)

    last_error: Exception | None = None
    if GEMINI_API_KEY:
        try:
            return _call_gemini(mime_type, b64_data)
        except Exception as exc:  # noqa: BLE001 -- any failure here should fall back, not crash
            print(f"[ai_menu] Gemini call failed, falling back to OpenAI: {exc}")
            last_error = exc
    if OPENAI_API_KEY:
        try:
            return _call_openai(mime_type, b64_data)
        except Exception as exc:  # noqa: BLE001
            print(f"[ai_menu] OpenAI call failed: {exc}")
            last_error = exc
    if last_error is not None:
        raise MenuParseError("AI 解析失敗,請稍後再試或手動輸入品項")
    raise MenuParseError("尚未設定 GEMINI_API_KEY 或 OPENAI_API_KEY,無法使用 AI 解析菜單功能")
