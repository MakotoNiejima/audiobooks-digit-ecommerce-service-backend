from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import create_ticket, map_ticket_type


class CreateTicketAction(Action):
    name = "action_create_ticket"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        slots = state.active_task.slots
        category = slots.get("ticket_category") or "其他"
        description = (slots.get("problem_description") or "").strip() or "用户未填写详细描述"

        ticket_type = map_ticket_type(category)
        title = f"{category}问题"[:30]
        # 正文带上用户描述
        content = f"【{category}】{description}"

        result = await create_ticket(state, ticket_type=ticket_type, title=title, content=content)

        if result is None:
            return ActionResult(slot_updates={
                "ticket_id": "工单提交失败，请稍后再试或联系人工客服。"
            })

        ticket_no = result.get("ticketNo", "")
        ticket_status = result.get("ticketStatus", "submitted")

        return ActionResult(slot_updates={
            "ticket_id": (
                f"你的工单已提交，工单编号 {ticket_no}，"
                f"类型 {category}，状态 {ticket_status}。"
                f"客服会在 1-2 个工作日内处理，请留意站内消息。"
            )
        })
