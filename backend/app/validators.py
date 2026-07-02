"""User-name validation (v0.8).

Two separate concerns bundled together because both requests landed at once:

1. Reserved-name prefixes -- nobody should be able to self-register as
   "admin...", "root...", "ubuntu...", "sysop...", "sysadmin..." (case
   insensitive) via the ordinary login/rename flows. This is about not
   letting a regular team member confuse people by naming themselves
   something that looks like a system/admin account.
2. Injection prevention -- rather than trying to blacklist dangerous
   sequences (quotes, semicolons, <script>, SQL keywords, etc. -- always a
   losing game), this uses an allow-list: a name may only contain letters
   (any language, so Chinese names still work), digits, spaces, and
   `-_.`. Anything else (`<`, `>`, `;`, `'`, `"`, backtick, `/`, `\`, ...) is
   rejected outright. SQLAlchemy's ORM already parameterizes every query
   (no raw SQL string-building happens anywhere in this app), so classic SQL
   injection isn't actually reachable today -- but this allow-list is cheap
   defense-in-depth, and also rules out stored-XSS-style payloads before
   they ever reach the database.

Only applied when a name is being newly *created* or *renamed* (login-as an
already-existing exact-match name skips this, so pre-existing roster
entries created before this check existed keep working).
"""
import re

from fastapi import HTTPException

RESERVED_PREFIXES = ["admin", "root", "ubuntu", "sysop", "sysadmin"]

# Unicode letters/digits/underscore (\w in Python 3 is unicode-aware by
# default) plus space, hyphen, dot. 1-30 characters.
NAME_PATTERN = re.compile(r"^[\w\-. ]{1,30}$")


def validate_user_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        raise HTTPException(400, "請輸入使用者名稱")
    if not NAME_PATTERN.match(cleaned):
        raise HTTPException(
            400, "名稱包含不允許的字元,只能使用中文/英文/數字/空格與 - _ .,且長度需在30字以內")
    lowered = cleaned.lower()
    for prefix in RESERVED_PREFIXES:
        if lowered.startswith(prefix):
            raise HTTPException(400, f"不可使用「{prefix}」開頭的名稱,請改用其他名稱")
    return cleaned
