"""剧本杀预约海报发送服务。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_BOOKING_POSTER_API_URL = "https://www.shisan.ink/api/booking/poster"


class BookingPosterError(RuntimeError):
    """预约海报请求、下载或发送失败。"""


def send_booking_poster_to_chat(
    who: str,
    *,
    wx: Any | None = None,
    exact: bool = False,
    api_url: str = DEFAULT_BOOKING_POSTER_API_URL,
    download_dir: str | os.PathLike[str] | None = None,
    timeout: int = 30,
) -> str:
    """请求预约海报，下载图片，并发送到指定微信聊天对象。

    返回下载后的本地图片绝对路径，方便调用方调试和日志记录。
    """
    if not str(who or "").strip():
        raise BookingPosterError("发送对象 who 不能为空")
    if wx is None:
        raise BookingPosterError("wx 必须传入已初始化的 WeChat 实例")

    local_path = generate_booking_poster(
        download_dir=download_dir,
        api_url=api_url,
        timeout=timeout,
    )
    return send_poster_to_chat(local_path, who=who, wx=wx, exact=exact)


def generate_booking_poster(
    *,
    api_url: str = DEFAULT_BOOKING_POSTER_API_URL,
    download_dir: str | os.PathLike[str] | None = None,
    timeout: int = 30,
) -> str:
    """请求接口生成海报并下载图片，返回本地图片绝对路径。"""
    poster_url = fetch_booking_poster_url(api_url=api_url, timeout=timeout)
    return download_poster_image(
        poster_url,
        download_dir=download_dir,
        timeout=timeout,
    )


def send_poster_to_chat(
    filepath: str,
    *,
    who: str,
    wx: Any | None = None,
    exact: bool = False,
) -> str:
    """使用已初始化的微信实例发送本地海报文件。"""
    if wx is None:
        raise BookingPosterError("wx 必须传入已初始化的 WeChat 实例")
    if not str(filepath or "").strip():
        raise BookingPosterError("海报文件路径不能为空")

    try:
        wx.SendFiles(filepath=filepath, who=who, exact=exact)
    except Exception as exc:  # noqa: BLE001
        raise BookingPosterError(f"发送微信文件失败: {exc}") from exc
    return filepath


def fetch_booking_poster_url(
    *,
    api_url: str = DEFAULT_BOOKING_POSTER_API_URL,
    timeout: int = 30,
) -> str:
    """请求海报接口并返回 data.url。"""
    try:
        with urlopen(_build_request(api_url), timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise BookingPosterError(f"请求预约海报接口失败: {exc}") from exc

    if not isinstance(payload, dict):
        raise BookingPosterError("预约海报接口返回格式错误: 根节点不是对象")

    code = payload.get("code")
    if code != 200:
        msg = payload.get("msg", "")
        raise BookingPosterError(f"预约海报接口返回失败: code={code}, msg={msg}")

    data = payload.get("data")
    poster_url = data.get("url") if isinstance(data, dict) else None
    if not isinstance(poster_url, str) or not poster_url.strip():
        raise BookingPosterError("预约海报接口返回缺少 data.url")

    return poster_url.strip()


def download_poster_image(
    poster_url: str,
    *,
    download_dir: str | os.PathLike[str] | None = None,
    timeout: int = 30,
) -> str:
    """把海报 URL 下载为本地图片文件。"""
    if not str(poster_url or "").strip():
        raise BookingPosterError("海报 url 不能为空")

    target_dir = Path(download_dir or Path(tempfile.gettempdir()) / "wechat-posters")
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = _filename_from_url(poster_url)
    target_path = target_dir / filename

    try:
        with urlopen(_build_request(poster_url), timeout=timeout) as response:
            image_bytes = response.read()
    except Exception as exc:  # noqa: BLE001
        raise BookingPosterError(f"下载海报图片失败: {exc}") from exc

    if not image_bytes:
        raise BookingPosterError("下载海报图片失败: 内容为空")

    target_path.write_bytes(image_bytes)
    return str(target_path.resolve())


def _build_request(url: str) -> Request:
    return Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36"
            )
        },
    )


def _filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    filename = os.path.basename(parsed.path).strip()
    if not filename:
        return "booking-poster.png"
    return filename
