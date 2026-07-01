from typing import Any

from atguigu.domain.state import DialogueState
from atguigu.task.action.base import Action, ActionResult
from atguigu.task.action.customer.shared import fetch_listening_progress, _fmt_seconds


class LookupPlaybackAction(Action):
    name = "action_lookup_playback"

    async def run(self, state: DialogueState, action_args: dict[str, Any]) -> ActionResult:
        book_name = (state.active_task.slots.get("book_name") or "").strip()
        recent_only = book_name in ("", "最近听的", "最近", "最近收听")

        progress_list = await fetch_listening_progress(state, album_id=None)

        if not progress_list:
            summary = "没有找到你的收听记录，可能你还没有收听过任何内容。"
            return ActionResult(slot_updates={"playback_summary": summary})

        if not recent_only:
            # 按书名模糊匹配
            matched = [p for p in progress_list
                       if book_name in str(p.get("albumTitle") or "")]
            if not matched:
                summary = f"没有找到《{book_name}》的播放进度。你可以试试查询最近的收听记录。"
                return ActionResult(slot_updates={"playback_summary": summary})
            progress_list = matched

        # 取最近一条
        p = progress_list[0]
        album_title = p.get("albumTitle") or "未知有声书"
        track_title = p.get("trackTitle") or "未知章节"
        position = _fmt_seconds(p.get("positionSeconds"))
        duration = _fmt_seconds(p.get("durationSeconds"))
        last_at = p.get("lastPlayedAt") or ""
        finished = "已听完" if p.get("finishedFlag") else "未听完"

        summary = (
            f"你最近在听《{album_title}》的「{track_title}」，"
            f"播放进度 {position}/{duration}（{finished}），最后播放时间 {last_at}。"
        )
        return ActionResult(slot_updates={"playback_summary": summary})
