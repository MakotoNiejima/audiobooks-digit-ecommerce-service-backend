from typing import Any

from atguigu.domain.messages import BotMessage, FocusedObject
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import bound_user_id, fetch_orders


ORDER_STATUS_CN = {
    "created": "待支付",
    "paying": "支付中",
    "paid": "已支付",
    "cancelled": "已取消",
    "refunding": "退款中",
    "refunded": "已退款",
}


class ListUserOrdersAction(Action):
    """没有指定订单时，列出当前用户最近的几个订单供点击选择。"""

    name = "action_list_user_orders"

    async def run(self, state: DialogueState, action_args: dict[str, Any] | None) -> ActionResult:
        slots = state.active_task.slots

        if slots.get("order_number"):
            return ActionResult(slot_updates={"order_candidates_available": True})

        # 用户刚刚点击过订单卡片时，直接复用该订单，不再重复列出候选订单。
        focused_object = state.focused_object
        if focused_object is not None and focused_object.type == "order":
            return ActionResult(slot_updates={
                "order_number": focused_object.id,
                "order_candidates_available": True,
            })

        if bound_user_id(state) is None:
            return ActionResult(
                messages=[BotMessage(text="当前会话没有绑定业务用户，请使用数字用户 ID 登录后再查询订单。")],
                slot_updates={"order_candidates_available": False},
            )

        args = action_args or {}
        refundable_only = bool(args.get("refundable_only"))
        orders = await fetch_orders(
            state,
            page_size=3,
            order_status="paid" if refundable_only else None,
        )

        if orders is None:
            return ActionResult(
                messages=[BotMessage(text="订单服务暂时不可用，请稍后再试。")],
                slot_updates={"order_candidates_available": False},
            )

        if not orders:
            text = "当前账号没有可申请退款的已支付订单。" if refundable_only else "当前账号还没有订单记录。"
            return ActionResult(
                messages=[BotMessage(text=text)],
                slot_updates={"order_candidates_available": False},
            )

        intro = "请选择要申请退款的订单：" if refundable_only else "找到以下最近订单，请选择要查询的订单："
        messages = [BotMessage(text=intro)]
        for order in orders:
            order_id = str(order.get("orderId") or "")
            order_no = str(order.get("orderNo") or order_id)
            status_raw = str(order.get("orderStatus") or "")
            status = ORDER_STATUS_CN.get(status_raw, status_raw)
            messages.append(BotMessage(object=FocusedObject(
                id=order_id,
                type="order",
                title=order_no,
                attributes={
                    "orderNo": order_no,
                    "status": status,
                    "amount": order.get("payableAmount"),
                },
            )))

        return ActionResult(
            messages=messages,
            slot_updates={"order_candidates_available": True},
        )
