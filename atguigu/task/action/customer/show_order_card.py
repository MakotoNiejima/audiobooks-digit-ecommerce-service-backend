from typing import Any

from atguigu.domain.messages import BotMessage, FocusedObject
from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult


class ShowOrderCardAction(Action):
    """输出订单摘要文本 + 可点击的订单对象卡片，供前端点击后发起退款等流程。"""

    name = "action_show_order_card"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots if state.active_task else {}
        order_id = str(slots.get("order_id") or "")
        if not slots.get("order_found") or not order_id:
            return ActionResult(messages=[BotMessage(text="订单信息不完整，暂时无法生成订单卡片。")])

        order_no = str(slots.get("order_no") or order_id)
        summary = slots.get("order_summary") or f"订单 {order_no} 查询完成。"
        status = slots.get("order_status")

        obj = FocusedObject(
            id=order_id,
            type="order",
            title=order_no,
            attributes={"orderNo": order_no, "status": status or ""},
        )
        return ActionResult(messages=[BotMessage(text=summary, object=obj)])
