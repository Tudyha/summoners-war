"""Send light/dark summon-result notifications to Feishu."""

import json
import time

import cv2
import requests

from ascript.android.screen import capture_cv
from ascript.android.system import Device

try:
    from .. import feishu_credentials
except ImportError:
    feishu_credentials = None


TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/"
    "tenant_access_token/internal"
)
IMAGE_URL = "https://open.feishu.cn/open-apis/im/v1/images"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
REQUEST_TIMEOUT_SECONDS = 12


def _response_data(response, operation):
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(
            "{} failed: {} {}".format(
                operation,
                payload.get("code"),
                payload.get("msg", "unknown error"),
            )
        )
    return payload.get("data") or {}


def _tenant_access_token():
    response = requests.post(
        TOKEN_URL,
        json={
            "app_id": feishu_credentials.APP_ID,
            "app_secret": feishu_credentials.APP_SECRET,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(
            "tenant token failed: {} {}".format(
                payload.get("code"),
                payload.get("msg", "unknown error"),
            )
        )
    token = payload.get("tenant_access_token")
    if not token:
        raise RuntimeError("tenant token response is missing token")
    return token


def _device_label():
    try:
        ip_address = str(Device.ip() or "").strip()
        last_part = ip_address.rsplit(".", 1)[-1]
        if last_part.isdigit():
            return "Android-{}".format(last_part)
        if ip_address:
            return ip_address
    except Exception:
        pass
    try:
        return str(Device.name() or Device.model() or "Android")
    except Exception:
        return "Android"


def _upload_screenshot(token):
    image = capture_cv()
    if image is None:
        return None
    encoded_ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), 90],
    )
    if not encoded_ok:
        return None
    response = requests.post(
        IMAGE_URL,
        headers={"Authorization": "Bearer {}".format(token)},
        data={"image_type": "message"},
        files={
            "image": (
                "summon-result.jpg",
                encoded.tobytes(),
                "image/jpeg",
            )
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _response_data(response, "image upload").get("image_key")


def _send_post(token, device_label, is_five_star, image_key):
    result_text = "五星" if is_five_star else "非五星"
    rows = [
        [
            {
                "tag": "text",
                "text": "设备：{}\n判定：{}\n时间：{}".format(
                    device_label,
                    result_text,
                    time.strftime("%Y-%m-%d %H:%M:%S"),
                ),
            }
        ]
    ]
    if image_key:
        rows.append([{"tag": "img", "image_key": image_key}])
    post = {
        "zh_cn": {
            "title": "光暗召唤结果 - {}".format(device_label),
            "content": rows,
        }
    }
    response = requests.post(
        MESSAGE_URL,
        params={"receive_id_type": "chat_id"},
        headers={"Authorization": "Bearer {}".format(token)},
        json={
            "receive_id": feishu_credentials.CHAT_ID,
            "msg_type": "post",
            "content": json.dumps(post, ensure_ascii=False),
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _response_data(response, "message send").get("message_id")


def send_summon_result(is_five_star):
    """Send one summon-result notification without changing runner state."""
    if feishu_credentials is None:
        return False, "credentials file is missing"
    if not getattr(feishu_credentials, "ENABLED", False):
        return False, "notification is disabled"
    try:
        token = _tenant_access_token()
        image_key = None
        image_error = None
        try:
            image_key = _upload_screenshot(token)
        except Exception as exc:
            # Text notification is still valuable if the app has not yet
            # been granted the separate image-upload permission.
            image_error = str(exc)
        message_id = _send_post(
            token,
            _device_label(),
            is_five_star,
            image_key,
        )
        detail = message_id or "sent"
        if image_error:
            detail += "; screenshot omitted: {}".format(image_error)
        return True, detail
    except Exception as exc:
        return False, str(exc)
