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
