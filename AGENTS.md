# AGENTS.md

十三你好

本文件适用于 `wechat-decrypt/` 目录及其子目录。默认使用中文与用户沟通，所有面向用户的说明、日志摘要、计划、错误解释、权限说明和验证结果都应使用中文；命令、代码、字段名、库名可以保留英文，但要用中文解释其含义。

## 项目概览

这是微信 4.x 本地数据库解密和实时监听项目，核心能力包括：

- 从运行中的微信进程提取数据库密钥。
- 解密 SQLCipher 4 加密数据库。
- 通过 `monitor_web.py` / `monitor_web_new.py` 提供 Web UI 和 SSE 实时消息流。
- 通过 `services/` 处理业务消息服务。
- 通过 `mcp_server.py` 提供 MCP 查询能力。

当前重点业务服务在 `services/jubensha_booking/`：

- `service.py`：剧本杀拼本消息处理服务。
- `poster_sender.py`：请求预约海报接口、下载图片、发送到微信聊天对象。
- `poster_scheduler.py`：预约海报定时发送。
- `mysql_client.py`：MySQL 写入逻辑。
- `constants.py`：仅放代码层稳定映射，例如 `DISCOUNT_LABELS`。

## 常用命令

在 `wechat-decrypt/` 目录下执行：

```powershell
python -m unittest discover -s tests
```

运行全部测试。

```powershell
python -m unittest tests.test_services_jubensha_booking
```

运行剧本杀消息服务相关测试。

```powershell
python -m unittest tests.test_monitor_contact_aliases
```

运行 `monitor_web_new.py` 相关测试，其中包含配置热加载和海报定时器接入测试。

```powershell
python -m json.tool services/config.json > $null
python -m json.tool services/config.example.json > $null
```

验证服务配置文件仍然是合法 JSON。

```powershell
python .\main.py web_new
```

启动全文版实时监听 Web UI。该命令会初始化微信实例、启动消息监听、启动服务层、启动预约海报定时任务和配置热加载。

## 配置约定

服务层配置集中在：

- `services/config.json`：当前实际配置。
- `services/config.example.json`：示例配置。
- `services/config_loader.py`：默认配置和配置加载逻辑。

JSON 不支持 `//` 注释。需要说明字段含义时，使用 `_comment` 或 `_xxx_comment` 字段。

这些运行参数应放在 `services/config.json`，不要放常量：

- MySQL 连接信息。
- `services.jubensha_booking.monitored_chatroom_ids`。
- `services.jubensha_booking.trigger_keywords`。
- `services.jubensha_booking.poster_sender.enabled`。
- `services.jubensha_booking.poster_sender.target_chat`。
- `services.jubensha_booking.poster_sender.exact`。
- `services.jubensha_booking.poster_sender.times`。

`monitored_chatroom_ids` 使用对象列表，保留群名可读性：

```json
{
    "id": "18614995060@chatroom",
    "name": "境由心造"
}
```

代码读取时使用 `id`，`name` 仅作为给人看的备注。

## 热加载约定

`monitor_web_new.py` 启动后会监控 `services/config.json` 的修改时间，通常 5 秒内自动热加载配置。

热加载行为：

- 配置合法：关闭旧 `ServiceManager`，后续消息使用新服务配置；旧海报定时器会停止并按新配置重启。
- 配置非法：继续使用旧配置，不应让主程序崩溃，并输出中文错误日志。

改动以下配置后不需要重启 `main.py web_new`：

- `monitored_chatroom_ids`
- `trigger_keywords`
- MySQL 配置
- 海报定时发送配置

## 代码约定

- 优先保持现有 Python 标准库风格，不额外引入依赖，除非确实必要。
- 手动编辑文件用补丁方式，不要顺手重排无关代码。
- 业务服务尽量放在 `services/` 内，剧本杀相关功能放在 `services/jubensha_booking/`。
- `services/` 目录设计目标是尽量独立，新增功能优先复用 `services/config.json` 和现有服务注册方式。
- 配置解析失败时要保留旧运行状态，不能让监听主流程退出。
- 微信客户端 `WeChat()` 只应在启动入口初始化一次，并向业务函数传递已有实例；不要在服务函数里偷偷初始化微信客户端。
- 发送文件使用 `wx.SendFiles(filepath=..., who=..., exact=...)`。

## 注释约定

这是强制要求：无论新增还是修改文件、类、函数、方法，都必须提供完整中文注释或文档字符串。

文件级注释必须说明：

- 这个文件负责什么。
- 属于哪个业务模块。
- 和其它模块的大致关系。

函数或方法注释必须说明：

- 这个函数或方法是干什么的。
- 需要哪些参数。
- 每个参数的含义。
- 返回值是什么；如果没有返回值，也要说明主要副作用。
- 可能抛出的关键异常或失败行为。

类注释必须说明：

- 这个类表示什么角色。
- 由谁创建或调用。
- 管理哪些状态。

行内调用其它重要方法时，也必须增加简短中文注释，说明为什么调用它、调用后会产生什么影响。尤其是这些场景：

- 调用会发送微信消息或文件的方法。
- 调用会读写数据库的方法。
- 调用会启动、停止线程或定时器的方法。
- 调用会读取、热加载、覆盖配置的方法。
- 调用会解密数据库、扫描密钥、访问本地敏感文件的方法。

注释要解释业务意图，不要写空泛重复的话。例如不要写“调用函数”，而要写“重新启动海报定时器，让新的发送时间立即生效”。

## 测试要求

修改功能代码时，优先补或更新测试：

- 新增配置字段：更新 `tests/test_services_config_loader.py`。
- 修改剧本杀消息过滤、关键词、入库行为：更新 `tests/test_services_jubensha_booking.py`。
- 修改 `monitor_web_new.py` 启动、热加载、定时器接入：更新 `tests/test_monitor_contact_aliases.py` 或新增对应测试。
- 修改海报生成、下载、发送：更新 `tests/test_services_booking_poster_sender.py`。
- 修改海报调度：更新 `tests/test_services_booking_poster_scheduler.py`。

完成后至少运行相关测试；较大改动运行：

```powershell
python -m unittest discover -s tests
```

## 文件与安全注意事项

以下文件或目录可能包含本地数据、密钥、数据库、日志或生成产物，除非用户明确要求，不要主动修改、清理或提交说明之外的变更：

- `all_keys.json`
- `config.json`
- `decrypted/`
- `decoded_images/`
- `wxauto_logs/`
- `__pycache__/`
- `*.db`
- `*.db-wal`
- `*.db-shm`

不要输出真实敏感信息，例如数据库密码、微信数据路径中的隐私信息、聊天内容、密钥内容。需要说明时使用概括或打码。

## 权限与运行注意

读取微信进程内存、扫描密钥、启动微信自动化、访问受保护路径等操作可能需要管理员权限或微信已登录。申请权限时必须用中文说明：

1. 要执行什么操作。
2. 为什么需要该权限。
3. 可能影响什么。

不要擅自运行会发送微信消息的命令；发送消息、发送文件、启动真实定时发送前，应确认用户意图明确。

## 交流风格

默认简洁、直接、中文说明。遇到配置、定时、微信自动化、数据库写入这类容易造成实际影响的操作，要明确说明当前会做什么、不会做什么，以及验证方式。
