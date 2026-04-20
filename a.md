# 需求文档：剧本杀消息结构化提取与自动化入库

## 1. 任务目标
监控聊天消息流，识别特定关键词。命中关键词后，调用 AI 接口提取剧本杀拼本结构化信息，并进行双重去重处理后存入 MySQL 数据库。

---

## 2. 触发规则与过滤 (Step 1)

### 2.1 关键词过滤
仅当消息内容 `content` 包含以下任一字符/词汇时，触发后续逻辑：
> `🥤`, `补贴`, `🈳`, `🆘`, `🉑️`, `🚗`, `免单`, `上车`, `极限`, `❗`

### 2.2 原始消息去重 (表：jubensha_all_content)
1. **生成唯一标识**：`unique_no = md5(sender_wx_id + content)`。
2. **逻辑判断**：
   - 查询数据库中是否存在该 `unique_no`。
   - **已存在**：说明该消息已处理，直接跳过，**严禁**再次请求 AI 接口。
   - **不存在**：执行 `INSERT` 存入原始消息，并进入 **Step 3**。

---

## 3. AI 逻辑处理 (Step 2)

- **调用模块**：使用 `zhipu_chat_demo` 下的 `extract_jubensha` 函数。
- **输入参数**：原始消息文本 `content`。
- **预期输出**：结构化 JSON 数据，只要求 AI 提取 `booking_time`, `store_name`, `script_name`, `script_details`, `discount_type`。
- `user_name`、`user_id`、`wechat_no` 不由 AI 提取，统一从监听到的微信消息和联系人数据库信息补充。

---

## 4. 业务数据入库 (Step 3)

### 4.1 业务去重与更新 (表：jubensha_booking)
1. **生成业务唯一标识**：
   `unique_no = md5(f"{booking_time}_{store_name}_{script_name}_{user_id}")`
2. **入库操作 (Upsert)**：
   - **若 unique_no 已存在**：更新该条记录。
   - **若 unique_no 不存在**：插入新记录，并按当前表默认口径写入 `is_api=0`、`booking_type=group`、`is_completed=0`。
   - 入库时维护 Laravel 风格时间字段：新增记录写入 `created_at` 与 `updated_at`，更新记录刷新 `updated_at`。
   - 业务去重只匹配 `deleted_at IS NULL` 的未软删记录。

---

## 5. 数据库 DDL (SQL)

### 5.1 原始消息内容表
```sql
CREATE TABLE `jubensha_all_content` (
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `unique_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '唯一值',
  `sender_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '发送者名称',
  `sender_wx_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '发送者的微信id',
  `content` text COLLATE utf8mb4_unicode_ci,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_unique_no` (`unique_no`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='剧本杀所有内容';
```

### 5.2 剧本杀拼本信息表
```sql
CREATE TABLE `jubensha_booking` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `unique_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '唯一值',
  `user_id` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '用户 openid',
  `user_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '用户名称',
  `booking_time` datetime DEFAULT NULL COMMENT '开本时间',
  `store_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '店名或区域',
  `script_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '剧本名称',
  `script_details` text COLLATE utf8mb4_unicode_ci COMMENT '详情说明',
  `discount_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '正常' COMMENT '优惠类型：正常、低价、折扣、免单',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `created_at` timestamp NULL DEFAULT NULL COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT NULL COMMENT '更新时间',
  `deleted_at` timestamp NULL DEFAULT NULL COMMENT '删除时间',
  `is_api` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否可靠/官方来源',
  `wechat_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '' COMMENT '微信号',
  `booking_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'group' COMMENT '信息类型：group组局，seek_group求组',
  `is_completed` tinyint(4) NOT NULL DEFAULT '0' COMMENT '是否完成：0未完成，1已完成',
  `province_id` int(11) DEFAULT NULL COMMENT '省份ID',
  `province_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '省份名称',
  `city_id` int(11) DEFAULT NULL COMMENT '城市ID',
  `city_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '城市名称',
  `district_id` int(11) DEFAULT NULL COMMENT '区县ID',
  `district_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '区县名称',
  PRIMARY KEY (`id`),
  KEY `jubensha_booking_user_id_index` (`user_id`),
  KEY `jubensha_booking_booking_time_index` (`booking_time`),
  KEY `jubensha_booking_expire_time_index` (`expire_time`),
  KEY `jubensha_booking_booking_type_index` (`booking_type`),
  KEY `jubensha_booking_is_api_index` (`is_api`),
  KEY `jubensha_booking_unique_no_index` (`unique_no`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```
