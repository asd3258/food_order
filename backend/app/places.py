"""Google Places (New) lookup -- v0.10.

Given a Google Maps share link the user already pasted in (short
`maps.app.goo.gl/...` links or full `google.com/maps/place/...` URLs), fetch
that place's phone number, address, and opening hours to auto-fill the
restaurant form. This is a *separate* Google product from Gemini -- it
needs its own API key (GOOGLE_MAPS_API_KEY) from a Google Cloud project
with the "Places API (New)" enabled and a billing account attached (Google
requires a card on file to use it at all, even though normal usage for a
small team should stay within the $200/month Maps Platform free credit).

There is deliberately NO attempt here to pull "the menu photos" off a Maps
listing -- Google's official Places API doesn't expose photos categorized
as "menu" or sortable by upload date (that's only presented in the Maps
website/app UI, backed by internal APIs). Doing that reliably would require
an unofficial third-party scraper, which was explicitly ruled out. If no
menu photo is uploaded, this app simply doesn't auto-generate menu items --
the user uploads one manually.

Resolution strategy (arbitrary Maps URLs don't map directly to a place_id):
1. Follow redirects (resolves maps.app.goo.gl short links) to get the
   canonical URL.
2. Pull the place name and lat/lng out of that URL
   (".../maps/place/<name>/@<lat>,<lng>,...").
3. Places API Text Search for that name, biased to those coordinates so we
   land on the exact pin the user picked rather than a same-named place
   elsewhere -- this avoids needing to reverse-engineer Google's internal
   Feature ID encoding.
4. Places API Place Details on the resulting place_id for phone/address/hours.
"""
import os
import re
import urllib.parse

import httpx

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
REQUEST_TIMEOUT = 20


class PlacesError(Exception):
    pass


_BROWSER_HEADERS = {
    # Google's redirect handler behaves differently for non-browser clients
    # (httpx's default "python-httpx/x.x" UA can land on a stripped-down
    # response instead of the normal /maps/place/... redirect) -- send a
    # realistic desktop UA to make this resolve the same way a browser would.
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def _resolve_name_and_coords(map_url: str) -> tuple[str | None, float | None, float | None]:
    try:
        resp = httpx.get(map_url, follow_redirects=True, timeout=REQUEST_TIMEOUT,
                          headers=_BROWSER_HEADERS)
        final_url = str(resp.url)
    except Exception as exc:
        print(f"[places] failed to resolve {map_url!r}: {exc}")
        final_url = map_url

    print(f"[places] resolved {map_url!r} -> {final_url!r}")

    if "consent.google.com" in final_url:
        # EU/某些地區的 cookie 同意頁 -- 沒有真的瀏覽器 session 通過同意流程,
        # 純 HTTP 請求會卡在這裡，永遠拿不到真正的 /maps/place/... 網址。
        raise PlacesError("Google 要求先通過 Cookie 同意頁,無法自動解析這個連結,請改用電腦版網頁的網址")

    name = None
    m = re.search(r"/maps/place/([^/@]+)", final_url)
    if m:
        name = urllib.parse.unquote(m.group(1)).replace("+", " ")
    else:
        # 手機分享連結有時會解析成 .../maps/@lat,lng,zoom?q=店名&... 或
        # .../maps?q=店名 這種沒有 /place/ 路徑的格式 -- 從 q= 參數撈店名。
        parsed = urllib.parse.urlparse(final_url)
        q = urllib.parse.parse_qs(parsed.query).get("q")
        if q:
            name = q[0]

    lat = lng = None
    m2 = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", final_url)
    if m2:
        lat, lng = float(m2.group(1)), float(m2.group(2))

    print(f"[places] extracted name={name!r} lat={lat!r} lng={lng!r}")
    return name, lat, lng


def _text_search_place_id(query: str, lat: float | None, lng: float | None) -> str | None:
    url = "https://places.googleapis.com/v1/places:searchText"
    # v0.10 follow-up: languageCode/regionCode -- without these Google
    # defaults to English results (English address format, English weekday
    # names in opening hours), which isn't what a Taiwan-based team wants.
    body: dict = {"textQuery": query, "languageCode": "zh-TW", "regionCode": "TW"}
    if lat is not None and lng is not None:
        # Small radius (200m) -- we already have a specific pin from the
        # Maps URL, this is just about landing on that exact place instead
        # of a similarly-named one across town.
        body["locationBias"] = {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 200.0}}
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id",
    }
    resp = httpx.post(url, json=body, headers=headers, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    places = resp.json().get("places", [])
    return places[0]["id"] if places else None


def _place_details(place_id: str) -> dict:
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        # displayName costs nothing extra (Essentials tier); nationalPhoneNumber
        # + formattedAddress = Pro tier ($17/1k) same as opening hours, so no
        # cost saved by trimming the field mask further.
        "X-Goog-FieldMask": "displayName,nationalPhoneNumber,formattedAddress,regularOpeningHours.weekdayDescriptions",
    }
    # languageCode/regionCode -- same reasoning as the text search call: get
    # a Taiwan-formatted address ("...路...號" style) and 星期X 開頭的營業時間,
    # not the English defaults.
    params = {"languageCode": "zh-TW", "regionCode": "TW"}
    resp = httpx.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def fetch_place_info(map_url: str) -> dict:
    if not GOOGLE_MAPS_API_KEY:
        raise PlacesError("尚未設定 GOOGLE_MAPS_API_KEY,無法從 Google Map 自動讀取店家資訊")

    map_url = (map_url or "").strip()
    if not map_url:
        raise PlacesError("請先輸入 Google Map 連結")

    name, lat, lng = _resolve_name_and_coords(map_url)
    query = name or map_url

    try:
        place_id = _text_search_place_id(query, lat, lng)
    except Exception as exc:
        raise PlacesError(f"呼叫 Google Places API 失敗:{exc}") from exc
    if not place_id:
        raise PlacesError("找不到這個 Google Map 連結對應的地點,請確認網址正確")

    try:
        data = _place_details(place_id)
    except Exception as exc:
        raise PlacesError(f"讀取地點詳細資料失敗:{exc}") from exc

    hours_lines = data.get("regularOpeningHours", {}).get("weekdayDescriptions", [])
    return {
        "name": data.get("displayName", {}).get("text", ""),
        "phone": data.get("nationalPhoneNumber", ""),
        "address": data.get("formattedAddress", ""),
        "hours": "\n".join(hours_lines),
    }
