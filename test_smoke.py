"""听书客服闭环冒烟测试。uv run python test_smoke.py"""
import json
import httpx

BASE = "http://127.0.0.1:8002"


def chat(sender_id: str, text: str, obj: dict | None = None):
    payload = {"sender_id": sender_id, "text": text}
    if obj:
        payload["object"] = obj
    r = httpx.post(f"{BASE}/api/chat", json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    msgs = [m["text"] for m in data.get("messages", []) if m.get("text")]
    return msgs


def show(tag, msgs):
    print(f"\n【{tag}】")
    for m in msgs:
        print("  BOT:", m)


# 1. 闲聊
show("1.闲聊", chat("1", "你好"))

# 2. 有声书咨询（知识轨）
show("2.有声书咨询", chat("1", "推荐几本高评分的有声书"))

# 3. 订单查询（用户2 拥有订单 ORD000000000001，已支付）
show("3.订单查询-首轮(带订单号)", chat("2", "帮我查一下订单 ORD000000000001"))

# 4. 播放记录查询（用户1 有 9 条进度）—— 先说意图，再回答书名
show("4.播放查询-触发", chat("1", "我最近听到哪一章了？"))
show("4.播放查询-回答书名", chat("1", "最近听的"))

# 5. 退款申请（用户2 订单1 已支付，可退款）—— 多轮
show("5.退款-触发", chat("2", "我要退款"))
show("5.退款-订单号", chat("2", "ORD000000000001"))
show("5.退款-原因", chat("2", "内容不符合预期"))
show("5.退款-类型", chat("2", "全额退款"))

# 6. 工单提交（多轮）
show("6.工单-触发", chat("1", "我购买的课程一直播放不了"))
show("6.工单-类型", chat("1", "播放异常"))
show("6.工单-描述", chat("1", "打开章节就黑屏，无法播放"))

# 7. 会话历史
r = httpx.get(f"{BASE}/api/chat/history", params={"sender_id": "2"}, timeout=30)
print("\n【7.用户2会话历史】")
for m in r.json().get("messages", [])[-6:]:
    print(f"  {m.get('role')}: {m.get('text')}")
