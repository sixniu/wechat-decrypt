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
- `jubensha_booking.poster_sender`：主动请求预约海报接口，下载 `data.url` 图片并发送到指定微信聊天对象
- `jubensha_booking.poster_scheduler`：在 `web_new` 启动后每天按配置时间定时发送预约海报
- `wechat_client`：封装 wxautox4 的发送文件、发送文本、艾特全体等微信自动化能力

预约海报发送示例：

```python
from wxautox4 import WeChat
from services import send_file
from services.jubensha_booking import generate_booking_poster

wx = WeChat()
poster_path = generate_booking_poster()
send_file(wx=wx, filepath=poster_path, who="群聊名称", exact=False)
```

预约海报多群发送示例：

```python
from wxautox4 import WeChat
from services.jubensha_booking import send_booking_poster_to_chats

wx = WeChat()
send_booking_poster_to_chats(
    who_list=["境由心造", "拼好本"],
    wx=wx,
    exact=True,
)
```

微信自动化发送示例：

```python
from wxautox4 import WeChat
from services import at_all, send_file, send_text

wx = WeChat()
send_file(wx=wx, filepath="C:/文件.txt", who="张三", exact=False)
send_text(wx=wx, msg="你好", who="张三", clear=True, at="李四", exact=False)
at_all(wx=wx, msg="通知内容", who="工作群", exact=False)
```

预约海报定时发送：
- 配置集中放在 `services/config.json`
- `services.jubensha_booking.monitored_chatroom_ids`：需要监听的微信群 ID 列表
- `services.jubensha_booking.trigger_keywords`：触发剧本杀拼本处理的关键词列表
- `services.jubensha_booking.allowed_time_range`：每日允许处理剧本杀消息的业务时间范围
- `services.jubensha_booking.poster_sender`：预约海报定时发送配置
- `enabled`：是否启用定时发送
- `target_chats`：发送目标群聊名称列表，按顺序逐个发送
- `target_chat`：发送目标群聊名称
- `exact`：搜索群聊时是否精确匹配
- `times`：每天发送时间，24 小时制 `HH:MM`
- `_comment` / `_xxx_comment`：说明字段，用来代替 JSON 不支持的 `// 注释`

配置热加载：
- `web_new` 启动后会自动监控 `services/config.json`
- 保存配置文件后，通常 5 秒内会自动重载
- 配置格式错误时会继续使用旧配置，并在日志里输出失败原因
- 改动 `monitored_chatroom_ids`、`trigger_keywords`、MySQL、海报定时发送配置后，不需要重启 `main.py`
