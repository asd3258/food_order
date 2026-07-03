"""AI helpers: menu photo parsing (v0.9, now includes categorization since
v0.11) + standalone item categorization (v0.10).

Two features share the same Gemini-first/OpenAI-fallback plumbing:

- parse_menu_photo(image_data_url, reference_pairs): sends a photo of a
  menu to a vision-capable LLM, gets back a structured list of items
  (name, price, category, option groups) matching schemas.MenuItemIn.
  `reference_pairs` (already-categorized (name, category) pairs from
  elsewhere in the DB) is folded into the SAME prompt/call so uploading a
  photo doesn't also need a separate classify_menu_categories() round trip
  right after -- one AI call instead of two per upload (v0.11).
- classify_menu_categories(item_names, reference_pairs): text-only (no
  image) -- same category-suggestion logic, but for items that already
  exist without a photo re-upload (e.g. "AI自動分類品項類型" on
  EditRestaurantView, for manually-typed/edited items).

Neither function writes to the database. Provider order: Gemini first
(GEMINI_API_KEY), falling back to OpenAI (OPENAI_API_KEY) if Gemini isn't
configured or the call fails for any reason. If neither key is set (or both
fail), raises MenuParseError with a message meant to be shown to the user.

Both providers are called via plain REST (httpx) instead of pulling in
their official SDKs.
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


class MenuParseError(Exception):
    pass


# ---------------------------------------------------------------------------
# Generic Gemini / OpenAI structured-JSON callers, shared by both features
# below. `gemini_parts` / `openai_content` are the provider-specific
# "message content" arrays (text-only, or text + image).
# ---------------------------------------------------------------------------

def _call_gemini(parts: list[dict], schema: dict) -> object:
    if not GEMINI_API_KEY:
        raise MenuParseError("Gemini API key not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    resp = httpx.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _call_openai(content: list[dict], json_schema: dict) -> object:
    if not OPENAI_API_KEY:
        raise MenuParseError("OpenAI API key not configured")
    url = "https://api.openai.com/v1/chat/completions"
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": content}],
        "response_format": {"type": "json_schema", "json_schema": json_schema},
    }
    resp = httpx.post(url, headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                       json=body, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    return json.loads(text)


def _generate_with_fallback(gemini_call, openai_call):
    """`gemini_call`/`openai_call` are zero-arg closures. Tries Gemini first
    (if configured), then OpenAI (if configured), raising MenuParseError
    only once both options are exhausted."""
    last_error: Exception | None = None
    if GEMINI_API_KEY:
        try:
            return gemini_call()
        except Exception as exc:  # noqa: BLE001 -- any failure here should fall back, not crash
            print(f"[ai_menu] Gemini call failed, falling back to OpenAI: {exc}")
            last_error = exc
    if OPENAI_API_KEY:
        try:
            return openai_call()
        except Exception as exc:  # noqa: BLE001
            print(f"[ai_menu] OpenAI call failed: {exc}")
            last_error = exc
    if last_error is not None:
        raise MenuParseError("AI 服務呼叫失敗,請稍後再試或手動輸入")
    raise MenuParseError("尚未設定 GEMINI_API_KEY 或 OPENAI_API_KEY,無法使用這個 AI 功能")


# ---------------------------------------------------------------------------
# Feature 1 (v0.9): parse a menu photo into draft items
# ---------------------------------------------------------------------------

def _build_menu_prompt(reference_pairs: list[tuple[str, str]]) -> str:
    # v0.11: 分類建議併進同一次呼叫 -- 跟 _build_category_prompt 用同一套「優先
    # 沿用資料庫已有分類」邏輯,省得上傳照片後還要再打一次 AI API 才能分類。
    ref_lines = "\n".join(f"- {name} -> {category}" for name, category in reference_pairs) or "(目前資料庫還沒有任何分類紀錄)"
    return (
        "這是一張餐廳菜單的照片。請幫我把上面每一個品項整理成 JSON 陣列,每個品項包含:\n"
        "- name:品項名稱(去掉多餘符號,用繁體中文)\n"
        "- price:價格(整數,台幣;看不清楚就填 0)\n"
        "- category:這個品項的分類(2~6個字,例如:主餐、飲料、小菜、湯品、加購、甜點)。"
        "以下是資料庫裡其他餐廳「已經有分類」的品項名稱,請優先沿用裡面已經出現過的分類名稱"
        "(名稱相同或非常相似的品項,直接套用同一個分類),只有真的沒有適合的分類時才自己想一個新的:\n"
        f"{ref_lines}\n"
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
_MENU_SCHEMA_GEMINI = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "price": {"type": "INTEGER"},
            "category": {"type": "STRING"},
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
        "required": ["name", "price", "category", "options"],
    },
}

# OpenAI structured outputs (strict mode) require standard JSON Schema
# (lowercase types), every property listed in "required", and
# additionalProperties: false at every object level. Top-level must be an
# object, not a bare array, hence the {"items": [...]} wrapper.
_MENU_SCHEMA_OPENAI = {
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
                        "category": {"type": "string"},
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
                    "required": ["name", "price", "category", "options"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


def _split_data_url(data_url: str) -> tuple[str, str]:
    """"data:image/jpeg;base64,/9j/4AA..." -> ("image/jpeg", "/9j/4AA...")"""
    m = re.match(r"^data:([^;]+);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        raise MenuParseError("圖片格式錯誤,請重新上傳照片")
    return m.group(1), m.group(2)


def parse_menu_photo(image_data_url: str, reference_pairs: list[tuple[str, str]] | None = None) -> list[dict]:
    mime_type, b64_data = _split_data_url(image_data_url)
    prompt = _build_menu_prompt(reference_pairs or [])

    def gemini_call():
        parts = [
            {"inline_data": {"mime_type": mime_type, "data": b64_data}},
            {"text": prompt},
        ]
        return _call_gemini(parts, _MENU_SCHEMA_GEMINI)

    def openai_call():
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}},
        ]
        return _call_openai(content, _MENU_SCHEMA_OPENAI)["items"]

    return _generate_with_fallback(gemini_call, openai_call)


# ---------------------------------------------------------------------------
# Feature 2 (v0.10): suggest a 分類 (category) per item name
# ---------------------------------------------------------------------------

_CATEGORY_SCHEMA_GEMINI = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "category": {"type": "STRING"},
        },
        "required": ["name", "category"],
    },
}

_CATEGORY_SCHEMA_OPENAI = {
    "name": "categories",
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
                        "category": {"type": "string"},
                    },
                    "required": ["name", "category"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


def _build_category_prompt(item_names: list[str], reference_pairs: list[tuple[str, str]]) -> str:
    ref_lines = "\n".join(f"- {name} -> {category}" for name, category in reference_pairs) or "(目前資料庫還沒有任何分類紀錄)"
    names_lines = "\n".join(f"- {n}" for n in item_names)
    return (
        "你是一個餐廳菜單分類助手。以下是資料庫裡其他餐廳「已經有分類」的品項名稱,做為你分類時的"
        "參考,請優先沿用裡面已經出現過的分類名稱(名稱相同或非常相似的品項,直接套用同一個分類),"
        "只有真的沒有適合的分類時才自己想一個新的簡短分類名稱(2~6個字,例如:主餐、飲料、小菜、"
        "湯品、加購、甜點):\n\n"
        f"{ref_lines}\n\n"
        "現在請幫我把以下這間餐廳的品項名稱分類,每一個都要給一個分類,直接回傳 JSON 陣列,"
        "每個元素包含 name(品項名稱,要跟輸入一模一樣,不要修改)與 category(分類名稱):\n\n"
        f"{names_lines}"
    )


def classify_menu_categories(item_names: list[str], reference_pairs: list[tuple[str, str]]) -> list[dict]:
    names = [n.strip() for n in item_names if n and n.strip()]
    if not names:
        raise MenuParseError("沒有品項可以分類")
    prompt = _build_category_prompt(names, reference_pairs)

    def gemini_call():
        return _call_gemini([{"text": prompt}], _CATEGORY_SCHEMA_GEMINI)

    def openai_call():
        return _call_openai([{"type": "text", "text": prompt}], _CATEGORY_SCHEMA_OPENAI)["items"]

    return _generate_with_fallback(gemini_call, openai_call)
