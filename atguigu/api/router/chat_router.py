import uuid
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from atguigu.api.dependencies import DialogueServiceDep
from atguigu.api.schemas import ChatRequest, ChatResponse, ChatBotMessage, ChatObject,ChatMessageResponse
from atguigu.domain.messages import ProcessResult, UserMessage, MessageType, FocusedObject,ChatHistoryMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.customer.shared import fetch_orders


router = APIRouter()

ORDER_STATUS_CN = {
    "created": "待支付",
    "paying": "支付中",
    "paid": "已支付",
    "cancelled": "已取消",
    "refunding": "退款中",
    "refunded": "已退款",
}


@router.get("/hello")
async def hello():
    return {"success": "ok"}


@router.get("/api/orders/recent")
async def recent_orders(sender_id: str, limit: int = Query(default=5, ge=1, le=10)):
    """返回当前数字用户最近的订单，供前端订单面板展示。"""
    if not sender_id.isdigit():
        raise HTTPException(status_code=400, detail="当前会话没有绑定数字业务用户 ID")

    orders = await fetch_orders(DialogueState(sender_id=sender_id), page_size=limit)
    if orders is None:
        raise HTTPException(status_code=503, detail="订单服务暂时不可用")

    result = []
    for order in orders:
        raw_status = str(order.get("orderStatus") or "")
        order_id = str(order.get("orderId") or "")
        order_no = str(order.get("orderNo") or order_id)
        result.append({
            "id": order_id,
            "type": "order",
            "title": order_no,
            "attributes": {
                "orderNo": order_no,
                "status": ORDER_STATUS_CN.get(raw_status, raw_status),
                "statusRaw": raw_status,
                "amount": order.get("payableAmount"),
                "orderType": order.get("orderType"),
                "itemName": order.get("firstItemName"),
                "itemCount": order.get("itemCount"),
                "createdAt": order.get("createdAt"),
                "refundable": raw_status == "paid",
            },
        })

    return {"sender_id": sender_id, "orders": result}


@router.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest,
                        service: DialogueServiceDep):
    # 1. 将接口数据模型转成领域数据模型
    user_message = _build_user_message(chat_request)

    # 2. 注入service使用
    process_result: ProcessResult = await service.hand_dialogue(user_message)

    # 3. 将领域数据模型转成接口数据模型
    chat_response = _build_chat_response(process_result)

    return chat_response


@router.post("/api/chat/stream")
async def chat_stream_endpoint(chat_request: ChatRequest,
                               service: DialogueServiceDep):
    """SSE 流式对话。事件以 `data: {json}\\n\\n` 推送，详见 DialogueService.hand_dialogue_stream。"""
    user_message = _build_user_message(chat_request)

    async def event_gen():
        async for event in service.hand_dialogue_stream(user_message):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    """
    将接口数据模型转成领域数据模型UserMessage
    :param chat_request:
    :return:
    """
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=str(uuid.uuid4()),
        type=MessageType.OBJECT if chat_request.object else MessageType.TEXT,
        text=chat_request.text,
        object=FocusedObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object else None
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    """
    将领域数据模型转成接口数据模型ChatResponse
    :param process_result:
    :return:
    """

    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(text=bot_message.text,
                                 object=ChatObject(
                                     id=bot_message.object.id,
                                     type=bot_message.object.type,
                                     title=bot_message.object.title,
                                     attributes=bot_message.object.attributes,
                                 ) if bot_message.object else None) for bot_message in process_result.messages]
    )



@router.get("/api/chat/history", response_model=ChatMessageResponse)
async def chat_history_endpoint(sender_id: str,
                                service: DialogueServiceDep) -> ChatMessageResponse:

    chat_message_response: list[ChatHistoryMessage] = await service.load_chat_history(sender_id)

    return ChatMessageResponse(sender_id=sender_id, messages=chat_message_response)
