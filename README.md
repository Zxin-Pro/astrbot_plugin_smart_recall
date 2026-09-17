# astrbot_plugin_smart_recall (SmartRecall)

仅管理员可通过引用消息撤回指定消息的 AstrBot 插件

## 功能

- 仅 **管理员** 可触发撤回，非管理员 @ 机器人发送撤回指令时回复「权限不足」
- 必须 **引用（回复）** 某条消息才能撤回，未引用时回复「请引用要撤回的消息」
- 撤回成功回复「已撤回」，失败回复「撤回失败：<原因>」
- 撤回指令关键词：`撤回` / `撤回这条` / `撤回消息`
- 兼容 aiocqhttp（OneBot v11）/ Telegram / Lark / Discord 等平台（优先 `unsend`，回退 `delete_msg`）

## 使用方式

1. 管理员 @ 机器人并引用要撤回的消息，发送「撤回」（或「撤回这条」「撤回消息」）
2. 机器人撤回被引用的消息并回复「已撤回」

## 注意

- QQ 平台撤回有时间窗口限制（约 2 分钟内），超时无法撤回
- 群聊场景撤回他人消息需要机器人具备群管理员权限

## 安装

在 AstrBot WebUI 插件市场或通过仓库地址安装：

```
https://github.com/Zxin-Pro/astrbot_plugin_smart_recall
```
