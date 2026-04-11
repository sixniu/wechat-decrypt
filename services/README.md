# Services

这个目录是独立的消息服务层。

设计目标：
- 尽量少依赖当前项目其他文件
- 后续新增功能继续放在这个目录下
- 复制到其他项目时，优先整体复制 `services/` 目录

当前约定：
- 业务配置放在 `services/config.json`
- 示例配置见 `services/config.example.json`
- 当前项目只需要在消息产生后调用 `dispatch_message_to_services(message)`

当前内置服务：
- `jubensha_booking`：群聊文本消息命中关键词后，调用 AI 提取并写入 MySQL
