import json
from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.knowledge.providers.base import KnowledgeProvider, KnowledgeChunk
from atguigu.config.settings import settings
from atguigu.infrastructure import http_client


def _base_url() -> str:
    return settings.audio_api_base_url.rstrip("/")


def _user_headers(state: DialogueState) -> dict[str, str]:
    """仅在 sender_id 为合法数字时携带 X-User-Id，否则匿名访问公共接口。"""
    sender_id = (state.sender_id or "").strip()
    if sender_id.isdigit():
        return {"X-User-Id": sender_id}
    return {}


def _extract_data(result: Any) -> dict | None:
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


def _extract_list(result: Any) -> list[dict]:
    data = _extract_data(result)
    if not data:
        return []
    items = data.get("list") or data.get("plans") or data.get("albums") or []
    return items if isinstance(items, list) else []


class AlbumAPIProvider(KnowledgeProvider):
    """有声书/专辑咨询。有聚焦对象时查详情，否则浏览高评分专辑。"""

    provider_id = 'api.album'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        focused = state.focused_object
        headers = _user_headers(state)

        if focused is not None and focused.type == "audiobook" and str(focused.id).isdigit():
            try:
                r = await http_client.http_client.get(
                    f"{_base_url()}/api/v1/albums/{focused.id}", headers=headers)
                data = _extract_data(r.json())
                if data:
                    return [KnowledgeChunk(content="有声书详情:\n" + json.dumps(data, ensure_ascii=False, indent=2))]
            except Exception:
                pass

        # 无具体对象：浏览高评分有声书
        try:
            r = await http_client.http_client.get(
                f"{_base_url()}/api/v1/albums",
                params={"sortBy": "rating", "albumType": "audiobook", "pageSize": 5},
                headers=headers,
            )
            items = _extract_list(r.json())
            if items:
                brief = [
                    {"albumId": it.get("albumId"), "title": it.get("albumTitle"),
                     "summary": it.get("summary"), "trackCount": it.get("trackCount")}
                    for it in items
                ]
                return [KnowledgeChunk(content="高评分有声书推荐:\n" + json.dumps(brief, ensure_ascii=False, indent=2))]
        except Exception:
            pass

        return [KnowledgeChunk(content="暂未检索到相关有声书信息")]


class MembershipAPIProvider(KnowledgeProvider):
    """会员套餐咨询。"""

    provider_id = 'api.membership'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        try:
            r = await http_client.http_client.get(
                f"{_base_url()}/api/v1/vip-plans", headers=_user_headers(state))
            data = _extract_data(r.json())
            if data:
                return [KnowledgeChunk(content="会员套餐信息:\n" + json.dumps(data, ensure_ascii=False, indent=2))]
        except Exception:
            pass
        return [KnowledgeChunk(content="暂未检索到会员套餐信息")]


class OrderAPIProvider(KnowledgeProvider):
    """订单咨询（需用户发送订单对象卡片）。"""

    provider_id = 'api.order'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        focused = state.focused_object
        if focused is None or not str(focused.id).isdigit():
            return [KnowledgeChunk(content="未收到具体订单对象，无法查询")]
        try:
            r = await http_client.http_client.get(
                f"{_base_url()}/api/v1/orders/{focused.id}", headers=_user_headers(state))
            data = _extract_data(r.json())
            if data:
                return [KnowledgeChunk(content="订单信息:\n" + json.dumps(data, ensure_ascii=False, indent=2))]
        except Exception:
            pass
        return [KnowledgeChunk(content="暂未检索到该订单信息")]


# 听书平台静态 FAQ / 规则知识库（无外部 FAQ 接口时的兜底语料）
FAQ_KNOWLEDGE = """听书平台常见规则与 FAQ：

【退款规则】
1. 已购买的有声书/专辑，购买后 7 天内且收听进度不足 20% 可申请全额退款。
2. 超过 7 天或收听进度超过 20%，仅支持部分退款，具体以平台审核结果为准。
3. 会员 VIP 套餐一经开通、产生权益消费后不支持退款；未使用的充值余额可申请退回。
4. 退款一般 1-3 个工作日原路退回，到账时间以支付渠道为准。

【下载规则】
1. 已购买或有播放权益的有声书支持离线下载，下载文件仅限本 App 内播放。
2. 免费内容可试听，部分免费内容不支持下载。
3. 会员到期后，已下载的付费内容将无法继续播放，需重新开通权益。

【版权说明】
1. 平台所有音频内容版权归原版权方或创作者所有，用户不得录屏、转录、二次传播。
2. 未经授权传播音频内容将封禁账号并追究法律责任。

【会员权益】
1. VIP 会员可免费收听标有"会员免费"的内容，并享受付费内容折扣。
2. SVIP 会员在 VIP 权益基础上，每月赠送专属优惠券、享有更高音质。
3. 会员有效期以订单支付成功之日起算，到期后权益自动失效。

【播放规则】
1. 免费章节可直接播放；付费章节需购买专辑或单章，或开通会员。
2. 播放进度自动云端同步，切换设备可继续收听。
"""


class FAQProvider(KnowledgeProvider):
    """FAQ / 平台规则知识库（静态语料兜底）。"""

    provider_id = 'faq.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content=FAQ_KNOWLEDGE)]


class RAGProvider(KnowledgeProvider):
    """RAG 知识库（预留接入点，当前复用 FAQ 兜底）。"""

    provider_id = 'rag.default'

    async def retrieve(self, state: DialogueState) -> list[KnowledgeChunk]:
        return [KnowledgeChunk(content=FAQ_KNOWLEDGE)]
