"""听书业务中台 (audio-data) HTTP 调用封装。

所有用户级接口需要请求头 X-User-Id（取自 state.sender_id）。
"""

from typing import Any

from atguigu.config.settings import settings
from atguigu.domain.state import DialogueState
from atguigu.infrastructure import http_client


def _base_url() -> str:
    return settings.audio_api_base_url.rstrip("/")


def user_headers(state: DialogueState) -> dict[str, str]:
    """sender_id 为合法数字时携带 X-User-Id。"""
    sender_id = (state.sender_id or "").strip()
    if sender_id.isdigit():
        return {"X-User-Id": sender_id}
    return {}


def _extract_data(result: Any) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def _extract_list(result: Any) -> list[dict]:
    data = _extract_data(result)
    if not data:
        return []
    items = data.get("list") or data.get("plans") or []
    return items if isinstance(items, list) else []


async def fetch_order(state: DialogueState, order_number: str) -> dict | None:
    """支持按订单 ID（数字）或订单号（ORD 开头）查询订单详情。"""
    order_number = (order_number or "").strip()
    if not order_number:
        return None
    headers = user_headers(state)

    # 1. 数字：直接按订单 ID 查
    if order_number.isdigit():
        try:
            r = await http_client.http_client.get(
                f"{_base_url()}/api/v1/orders/{order_number}", headers=headers)
            payload = _extract_data(r.json())
            if payload and payload.get("order"):
                return payload
        except Exception:
            pass

    # 2. 订单号（ORD...）：先列订单再匹配 orderNo
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/orders",
            params={"pageNo": 1, "pageSize": 100},
            headers=headers,
        )
        for item in _extract_list(r.json()):
            if str(item.get("orderNo")) == order_number or str(item.get("orderId")) == order_number:
                order_id = item.get("orderId")
                r2 = await http_client.http_client.get(
                    f"{_base_url()}/api/v1/orders/{order_id}", headers=headers)
                payload = _extract_data(r2.json())
                if payload and payload.get("order"):
                    return payload
    except Exception:
        pass
    return None


async def fetch_listening_progress(state: DialogueState, album_id: int | None = None) -> list[dict]:
    params: dict[str, Any] = {"pageNo": 1, "pageSize": 20}
    if album_id is not None:
        params["albumId"] = album_id
    try:
        r = await http_client.http_client.get(
            f"{_base_url()}/api/v1/listening-progress",
            params=params,
            headers=user_headers(state),
        )
        return _extract_list(r.json())
    except Exception:
        return []


async def create_refund(state: DialogueState, payment_id: int, refund_reason: str,
                        items: list[dict]) -> dict | None:
    try:
        r = await http_client.http_client.post(
            f"{_base_url()}/api/v1/refunds",
            json={"paymentId": payment_id, "refundReason": refund_reason, "items": items},
            headers=user_headers(state),
        )
        return _extract_data(r.json())
    except Exception:
        return None


async def create_ticket(state: DialogueState, ticket_type: str, title: str, content: str) -> dict | None:
    try:
        r = await http_client.http_client.post(
            f"{_base_url()}/api/v1/support-tickets",
            json={
                "ticketType": ticket_type,
                "relatedType": "none",
                "ticketTitle": title,
                "ticketContent": content,
            },
            headers=user_headers(state),
        )
        return _extract_data(r.json())
    except Exception:
        return None


# 工单类型中文 → 枚举映射
TICKET_TYPE_MAP = {
    "播放异常": "content_issue",
    "投诉": "usage_feedback",
    "退款": "payment_issue",
    "账号问题": "account_issue",
    "账号": "account_issue",
    "其他": "other",
}


def map_ticket_type(category: str) -> str:
    category = (category or "").strip()
    for key, value in TICKET_TYPE_MAP.items():
        if key in category:
            return value
    return "other"


def _fmt_seconds(seconds: Any) -> str:
    try:
        total = int(seconds or 0)
    except Exception:
        return "0秒"
    if total <= 0:
        return "0秒"
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}小时{m}分{s}秒"
    if m > 0:
        return f"{m}分{s}秒"
    return f"{s}秒"
