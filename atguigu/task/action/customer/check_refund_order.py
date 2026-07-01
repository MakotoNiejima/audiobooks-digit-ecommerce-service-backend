from typing import Any

from atguigu.domain.messages import BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import bound_user_id, fetch_order


class CheckRefundOrderAction(Action):
    """在询问退款原因前检查订单归属、状态和支付记录。"""

    name = "action_check_refund_order"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        order_number = slots.get("order_number")

        if bound_user_id(state) is None:
            return self._reject("当前会话没有绑定业务用户，请使用数字用户 ID 登录后再申请退款。")

        payload = await fetch_order(state, order_number)
        if payload is None or not payload.get("order"):
            return self._reject(f"没有查到属于当前用户的订单 {order_number}，无法申请退款。")

        order = payload.get("order") or {}
        if order.get("orderStatus") != "paid":
            return self._reject(f"订单 {order.get('orderNo', order_number)} 当前状态不可申请退款。")

        payments = payload.get("payments") or []
        if not any(p.get("paymentStatus") == "success" for p in payments):
            return self._reject(f"订单 {order.get('orderNo', order_number)} 没有成功支付记录，暂不支持退款。")

        if not (payload.get("items") or []):
            return self._reject(f"订单 {order.get('orderNo', order_number)} 没有可退款的商品明细。")

        items = payload.get("items") or []
        item_names = [
            str(item.get("itemName") or "").strip()
            for item in items
            if item.get("itemName")
        ]
        detail_parts = [
            f"订单号：{order.get('orderNo', order_number)}",
            "状态：已支付",
        ]
        if order.get("payableAmount") is not None:
            detail_parts.append(f"金额：¥{order['payableAmount']}")
        if order.get("orderType"):
            detail_parts.append(f"类型：{order['orderType']}")
        if item_names:
            detail_parts.append("购买内容：" + "、".join(item_names[:3]))

        return ActionResult(
            messages=[BotMessage(text="已选择退款订单：\n" + "\n".join(detail_parts))],
            slot_updates={
                "refund_order_valid": True,
                "order_id": str(order.get("orderId") or order_number),
                "order_no": str(order.get("orderNo") or order_number),
            },
        )

    @staticmethod
    def _reject(message: str) -> ActionResult:
        return ActionResult(
            messages=[BotMessage(text=message)],
            slot_updates={"refund_order_valid": False},
        )
