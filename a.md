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
- **预期输出**：结构化 JSON 数据，需包含：`user_name`, `user_id`, `booking_time`, `store_name`, `script_name`, `script_details`, `discount_type`, `wechat_no` 等。

---

## 4. 业务数据入库 (Step 3)

### 4.1 业务去重与更新 (表：jubensha_booking)
1. **生成业务唯一标识**：
   `unique_no = md5(f"{booking_time}_{store_name}_{script_name}_{user_id}")`
2. **入库操作 (Upsert)**：
   - **若 unique_no 已存在**：更新该条记录。
   - **若 unique_no 不存在**：插入新记录，并将 `is_api` 字段设为 `1`。

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
  `id` int(11) NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `unique_no` varchar(100) NOT NULL DEFAULT '' COMMENT '唯一值',
  `user_name` varchar(50) NOT NULL DEFAULT '' COMMENT '用户名称',
  `user_id` varchar(50) NOT NULL DEFAULT '' COMMENT '用户编号',
  `booking_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '拼本时间',
  `store_name` varchar(100) NOT NULL DEFAULT '' COMMENT '剧本杀店名',
  `script_name` varchar(200) NOT NULL DEFAULT '' COMMENT '剧本杀名称',
  `script_details` text COMMENT '剧本杀详情',
  `discount_type` varchar(20) NOT NULL DEFAULT '正常' COMMENT '优惠类型：低价、折扣、免单、正常',
  `expire_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '过期时间，默认1天后过期',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `is_api` tinyint(1) NOT NULL DEFAULT '0' COMMENT '接口添加:0=否;1=是',
  `wechat_no` varchar(100) NOT NULL DEFAULT '' COMMENT '微信号',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_user_id` (`user_id`) USING BTREE,
  KEY `idx_booking_time` (`booking_time`) USING BTREE,
  KEY `idx_store_name` (`store_name`) USING BTREE,
  KEY `idx_script_name` (`script_name`) USING BTREE,
  KEY `idx_unique_no` (`unique_no`) USING BTREE,
  KEY `idx_discount_type` (`discount_type`),
  KEY `idx_expire_time` (`expire_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='剧本杀拼本信息表';
```