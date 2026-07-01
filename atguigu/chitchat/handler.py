from typing import Callable

from atguigu.chitchat.responder import ChitChatResponder
from atguigu.domain.messages import BotMessage

Emitter = Callable[[dict], None] | None


class ChitChatHandler:
    def __init__(self, chitchat_responder: ChitChatResponder):
        self.chitchat_responder = chitchat_responder

    async def hand(self, state, emitter: Emitter = None) -> list[BotMessage]:
        return await self.chitchat_responder.respond(state, emitter=emitter)
