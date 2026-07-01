from dataclasses import dataclass, field
@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids: list[str] = field(default_factory=list)
    requires_object: str | None = None



KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "audiobook_info": KnowledgeIntent(
        id="audiobook_info", description="有声书/专辑咨询（书名、作者、主播、章节数、评分、简介等）",
        provider_ids=["api.album"],
    ),
    "membership_info": KnowledgeIntent(
        id="membership_info", description="会员权益咨询（VIP 套餐、价格、权益、当前会员状态）",
        provider_ids=["api.membership"],
    ),
    "order_info": KnowledgeIntent(
        id="order_info", description="订单信息咨询（订单状态、支付情况、购买内容）",
        provider_ids=["api.order"], requires_object="order",
    ),
    "refund_policy": KnowledgeIntent(
        id="refund_policy", description="退款规则咨询（退款条件、退款流程、退款时效）",
        provider_ids=["faq.default"],
    ),
    "platform_rule": KnowledgeIntent(
        id="platform_rule", description="平台规则咨询（下载规则、版权说明、播放规则、会员使用规则等）",
        provider_ids=["faq.default"],
    ),
    "general_audiobook_info": KnowledgeIntent(
        id="general_audiobook_info", description="听书平台通用信息咨询",
        provider_ids=["faq.default"],
    ),
}
