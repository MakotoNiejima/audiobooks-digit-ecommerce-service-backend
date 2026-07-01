import uuid
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from atguigu.api.dependencies import DialogueServiceDep
from atguigu.api.schemas import ChatRequest, ChatResponse, ChatBotMessage, ChatObject,ChatMessageResponse
from atguigu.domain.messages import ProcessResult, UserMessage, MessageType, FocusedObject,ChatHistoryMessage


router = APIRouter()


@router.get("/hello")
async def hello():
    return {"success": "ok"}


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