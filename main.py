# -*- coding: utf-8 -*-
"""
SmartRecall - 仅管理员可通过引用消息撤回指定消息

触发条件：@机器人 + 引用某条消息 + 消息文本包含撤回关键词
撤回关键词：撤回 / 撤回这条 / 撤回消息
"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import At, Plain, Reply
from astrbot.api import logger, AstrBotConfig


@register("SmartRecall", "Zxin-Pro", "仅管理员可通过引用消息撤回", "1.1.0")
class SmartRecall(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        # 撤回指令关键词
        self.keywords = ("撤回", "撤回这条", "撤回消息")

    # ==================== 判断辅助方法 ====================

    def _is_bot_mentioned(self, event: AstrMessageEvent) -> bool:
        """判断本条消息是否 @ 了机器人"""
        bot_id = getattr(event.message_obj, "self_id", None)
        if not bot_id:
            return False
        for seg in event.message_obj.message:
            if isinstance(seg, At) and str(seg.qq) == str(bot_id):
                return True
        return False

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        """
        判断发送者是否为管理员：
        1. 插件配置的管理员QQ号列表（优先）
        2. 兜底使用 AstrBot 全局管理员（event.role == 'admin'）
        """
        sender_id = str(event.get_sender_id() or "")
        plugin_admins = self.config.get("admins") or []
        for aid in plugin_admins:
            if str(aid) == sender_id and sender_id:
                return True
        return getattr(event, "role", None) == "admin"

    def _get_replied_message_id(self, event: AstrMessageEvent):
        """获取被引用（回复）消息的 ID，未引用时返回 None"""
        for seg in event.message_obj.message:
            if isinstance(seg, Reply):
                return seg.id
        return None

    def _hit_keyword(self, text) -> bool:
        """判断消息文本是否包含撤回关键词"""
        t = (text or "").strip()
        return any(k in t for k in self.keywords)

    # ==================== 撤回核心逻辑 ====================

    async def _do_unsend(self, event: AstrMessageEvent, message_id: str):
        """
        撤回指定消息。
        优先使用 event.bot.unsend()（aiocqhttp/telegram/lark/discord 通用），
        适配器不支持时回退到 OneBot v11 的 delete_msg()。
        注意：多数平台撤回有时间窗口限制（QQ 通常 2 分钟内），超时/权限不足会抛异常。
        """
        bot = getattr(event, "bot", None)
        if bot is None:
            raise RuntimeError("当前平台适配器不支持撤回操作")

        bot_cls = type(bot).__name__
        # aiocqhttp（CQHttp）：必须走 OneBot v11 的 delete_msg，
        # 且 CQHttp.__getattr__ 对任意 API 名都动态返回调用器（hasattr 恒为 True），
        # 所以不能用 hasattr(bot, "unsend") 判断，必须按适配器类型区分
        if bot_cls == "CQHttp" or hasattr(bot, "call_action"):
            try:
                await bot.delete_msg(message_id=int(message_id))
            except (ValueError, TypeError):
                # 消息 ID 非纯数字时按原样传
                await bot.delete_msg(message_id=message_id)
            return

        # 其他平台（telegram/lark/discord 等）优先 unsend，全部关键字传参
        if hasattr(bot, "unsend"):
            await bot.unsend(message_id=message_id)
            return

        # 兜底：尝试 delete_msg
        if hasattr(bot, "delete_msg"):
            await bot.delete_msg(message_id=message_id)
            return

        raise RuntimeError("当前平台适配器不支持撤回操作")

    # ==================== 消息监听入口 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """
        监听所有消息，按以下严格顺序执行：
        1. 未 @ 机器人 -> 直接忽略
        2. 非管理员    -> 回复"权限不足"
        3. 不含撤回关键词 -> 忽略
        4. 未引用消息  -> 回复"请引用要撤回的消息"
        5. 执行撤回，成功回复"已撤回"，失败回复"撤回失败：<原因>"
        """
        try:
            # 1. 未 @ 机器人，不响应
            if not self._is_bot_mentioned(event):
                return

            # 2. 非管理员，静默忽略，不响应
            if not self._is_admin(event):
                return

            # 3. 文本必须包含撤回关键词，否则不响应
            if not self._hit_keyword(event.message_str):
                return

            # 4. 必须引用要撤回的消息
            message_id = self._get_replied_message_id(event)
            if not message_id:
                yield event.plain_result("请引用要撤回的消息")
                event.stop_event()
                return

            # 5. 执行撤回
            try:
                await self._do_unsend(event, message_id)
            except Exception as e:
                # 常见失败：超过撤回时间窗口（约 2 分钟）、机器人无管理员权限、消息不存在
                logger.error(f"[SmartRecall] 撤回消息 {message_id} 失败: {e!r}")
                yield event.plain_result(f"撤回失败：{e}")
                event.stop_event()
                return

            logger.info(f"[SmartRecall] 已撤回消息 {message_id}")
            yield event.plain_result("已撤回")
            event.stop_event()
        except Exception as e:
            # 监听器整体兜底，避免异常影响 AstrBot 消息管线
            logger.error(f"[SmartRecall] 处理消息时发生未预期异常: {e!r}")
