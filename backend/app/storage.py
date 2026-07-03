"""Object storage (MinIO, S3-compatible) for restaurant photos -- v0.11.

Previously every uploaded photo was stored as a full `data:` base64 URL
directly in the `restaurant_photos.image_url` TEXT column. That's simple
but doesn't scale: every photo bloats the Postgres row (and every backup of
it) by however many MB the original image was, base64-encoded on top of
that (~33% bigger than the raw file). This module uploads the decoded image
bytes to a self-hosted MinIO bucket instead and stores only a short path
(`/media/<restaurant_id>/<uuid>.<ext>`) in the database -- `nginx.conf`
proxies that path straight through to MinIO (see its `/media/` location
block), so the browser and the rest of the frontend never need to know
MinIO exists as a separate service; `image_url` just looks like any other
relative URL, exactly like it always has.

MinIO runs as its own container (`food_order_minio` in docker-compose.yml).
The bucket is created (idempotently) and given an anonymous-read policy on
startup -- writes still require the access key (only the backend can
upload/delete), but reads don't need any auth, which is what lets nginx
proxy GET requests straight through without forwarding credentials.
"""
import base64
import os
import re
import time
import uuid

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://food_order_minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "restaurant-photos")

_EXT_BY_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}

_client = None


class StorageError(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
    return _client


def _public_read_policy() -> str:
    return (
        '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*",'
        '"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::%s/*"]}]}' % MINIO_BUCKET
    )


def ensure_bucket() -> None:
    """Idempotent -- safe to call every startup (same philosophy as
    app/migrations.py's _add_column_if_missing). Creates the bucket if it
    doesn't exist yet and (re)applies the anonymous-read policy."""
    client = _get_client()
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=MINIO_BUCKET)
        print(f"[storage] created bucket {MINIO_BUCKET!r}")
    client.put_bucket_policy(Bucket=MINIO_BUCKET, Policy=_public_read_policy())


def wait_for_minio(retries: int = 20, delay: float = 1.5) -> None:
    """Best-effort -- unlike wait_for_db(), this never raises. If
    MINIO_ACCESS_KEY isn't set yet (fresh deploy, .env not filled in) or
    MinIO genuinely isn't reachable, photo upload/delete will just fail
    with a clear error when actually used -- the rest of the app (orders,
    votes, viewing existing restaurants) has nothing to do with MinIO and
    shouldn't be blocked by it not being ready."""
    if not MINIO_ACCESS_KEY:
        print("[storage] MINIO_ACCESS_KEY not set, skipping MinIO setup for now")
        return
    for attempt in range(retries):
        try:
            ensure_bucket()
            print("[storage] MinIO ready")
            return
        except Exception as exc:  # noqa: BLE001
            if attempt == retries - 1:
                print(f"[storage] MinIO never became ready, giving up for now: {exc}")
                return
            time.sleep(delay)


def upload_data_url(data_url: str, restaurant_id: int) -> str:
    """"data:image/jpeg;base64,/9j/..." -> "/media/5/ab12cd34ef.jpg" """
    if not MINIO_ACCESS_KEY:
        raise StorageError("尚未設定 MinIO(MINIO_ACCESS_KEY),無法上傳照片")
    m = re.match(r"^data:([^;]+);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        raise StorageError("圖片格式錯誤,請重新上傳照片")
    mime_type, b64_data = m.group(1), m.group(2)
    ext = _EXT_BY_MIME.get(mime_type, "bin")
    key = f"{restaurant_id}/{uuid.uuid4().hex}.{ext}"
    try:
        body = base64.b64decode(b64_data)
        _get_client().put_object(Bucket=MINIO_BUCKET, Key=key, Body=body, ContentType=mime_type)
    except Exception as exc:
        raise StorageError(f"上傳照片到儲存空間失敗:{exc}") from exc
    return f"/media/{key}"


def delete_object(image_url: str) -> None:
    """No-op for anything that isn't one of our own /media/... paths --
    covers seed data's "placeholder:#hex" sentinel values and any
    not-yet-migrated legacy `data:` URL rows."""
    if not image_url.startswith("/media/"):
        return
    key = image_url[len("/media/"):]
    try:
        _get_client().delete_object(Bucket=MINIO_BUCKET, Key=key)
    except Exception as exc:  # noqa: BLE001
        print(f"[storage] failed to delete object {key!r}: {exc}")
