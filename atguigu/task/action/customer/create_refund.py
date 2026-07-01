from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import fetch_order, create_refund


class CreateRefundAction(Action):
    name = "action_create_refund"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        order_number = slots.get("order_number")
        refund_reason = slots.get("refund_reason") or "用户申请退款"
        refund_type = (slots.get("refund_type") or "").strip()

        payload = await fetch_order(state, order_number)
        if payload is None or not payload.get("order"):
            return ActionResult(slot_updates={
                "refund_result": f"没有查到订单 {order_number}，无法提交退款申请，请确认订单号。"
            })

        order = payload.get("order") or {}
        payments = payload.get("payments") or []
        items = payload.get("items") or []

        # 找一笔成功支付
        success_payment = next((p for p in payments if p.get("paymentStatus") == "success"), None)
        if success_payment is None:
            return ActionResult(slot_updates={
                "refund_result": f"订单 {order.get('orderNo', order_number)} 没有成功支付记录，暂不支持退款。"
            })

        # 构建退款明细
        refund_items = []
        for it in items:
            refund_items.append({
                "orderItemId": it.get("itemId"),
                "refundQuantity": it.get("quantity", 1),
                "refundAmount": it.get("payableAmount", 0),
            })
        if "部分" in refund_type and refund_items:
            refund_items = refund_items[:1]

        if not refund_items:
            return ActionResult(slot_updates={
                "refund_result": f"订单 {order.get('orderNo', order_number)} 没有可退款的商品明细。"
            })

        result = await create_refund(
            state,
            payment_id=success_payment.get("paymentId"),
            refund_reason=refund_reason,
            items=refund_items,
        )

        if result is None or not result.get("refund"):
            return ActionResult(slot_updates={
                "refund_result": f"订单 {order.get('orderNo', order_number)} 的退款申请提交失败，请稍后再试或联系人工客服。"
            })

        refund = result.get("refund") or {}
        refund_no = refund.get("refundNo", "")
        refund_status = refund.get("refundStatus", "requested")
        refund_amount = refund.get("refundAmount", "")

        return ActionResult(slot_updates={
            "refund_result": (
                f"订单 {order.get('orderNo', order_number)} 的退款申请已提交，"
                f"退款单号 {refund_no}，退款金额 ¥{refund_amount}，"
                f"状态：{refund_status}。我们会在 1-3 个工作日处理，到账时间以支付渠道为准。"
            )
        })
