from typing import Callable

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.domain.messages import BotMessage, UserMessage
from atguigu.domain.state import Turn
from atguigu.infrastructure.llm_client import llm_client
from atguigu.knowledge.providers.base import KnowledgeChunk
from atguigu.history.builder import ChatHistoryBuilder
from atguigu.prompts.loader import load_prompt_template

Emitter = Callable[[dict], None] | None


class KnowledgeResponder:
    async def respond(
            self,
            user_message: UserMessage,
            recent_turns: list[Turn],
            chunks: list[KnowledgeChunk],
            emitter: Emitter = None,
    ) -> list[BotMessage]:
        # 准备提示词上下文
        user_message = ChatHistoryBuilder.process_user_message(user_message)
        history = ChatHistoryBuilder.build(recent_turns)
        knowledge_content = "\n\n".join([chunk.content for chunk in chunks])

        # 构造chain
        prompt_text = load_prompt_template("knowledge_respond")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2"
        )
        chain = prompt | llm_client | StrOutputParser()

        inputs = {
            "user_message": user_message,
            "history": history,
            "knowledge_content": knowledge_content,
        }

        # 运行chain（流式 / 非流式）
        if emitter is None:
            response = await chain.ainvoke(inputs)
        else:
            parts: list[str] = []
            async for chunk in chain.astream(inputs):
                parts.append(chunk)
                emitter({"type": "token", "text": chunk})
            response = "".join(parts)

        return [BotMessage(text=response)]
