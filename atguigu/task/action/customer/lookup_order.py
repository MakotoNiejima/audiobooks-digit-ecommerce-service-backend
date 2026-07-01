from typing import Any

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import bound_user_id, fetch_order


ORDER_STATUS_CN = {
    "created": "待支付",
    "paying": "支付中",
    "paid": "已支付",
    "cancelled": "已取消",
    "refunding": "退款中",
    "refunded": "已退款",
}


class LookupOrderAction(Action):
    name = "action_lookup_order"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        order_number = state.active_task.slots.get("order_number")

        if bound_user_id(state) is None:
            return ActionResult(
                messages=[BotMessage(text="当前会话没有绑定业务用户，请使用数字用户 ID 登录后再查询订单。")],
                slot_updates={"order_found": False},
            )

        payload = await fetch_order(state, order_number)

        if payload is None or not payload.get("order"):
            return ActionResult(
                messages=[BotMessage(text=f"没有查到属于当前用户的订单 {order_number}，请确认订单号是否正确。")],
                slot_updates={"order_found": False},
            )

        order = payload.get("order") or {}
        items = payload.get("items") or []
        status_raw = order.get("orderStatus") or "未知"
        status_cn = ORDER_STATUS_CN.get(status_raw, status_raw)

        parts = [f"订单号 {order.get('orderNo', order_number)}，状态：{status_cn}"]
        if order.get("payableAmount") is not None:
            parts.append(f"金额 ¥{order['payableAmount']}")
        if order.get("orderType"):
            parts.append(f"类型 {order['orderType']}")
        if items:
            names = [str(it.get("itemName") or "").strip() for it in items if it.get("itemName")]
            if names:
                parts.append("购买：" + "、".join(names[:3]))

        return ActionResult(slot_updates={
            "order_found": True,
            "order_status": status_cn,
            "order_summary": "；".join(parts) + "。",
            "order_id": str(order.get("orderId") or order_number),
            "order_no": str(order.get("orderNo") or order_number),
        })
