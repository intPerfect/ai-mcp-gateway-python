-- AI MCP Gateway Database Schema v3.0
-- MySQL 8.0+
-- 优化版本：移除冗余字段，支持多参数位置

CREATE DATABASE IF NOT EXISTS `ai_mcp_gateway_v2` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `ai_mcp_gateway_v2`;

-- ============================================
-- MCP Gateway 配置表
-- ============================================
DROP TABLE IF EXISTS `mcp_protocol_mapping`;
DROP TABLE IF EXISTS `mcp_protocol_http`;
DROP TABLE IF EXISTS `mcp_gateway_tool`;
DROP TABLE IF EXISTS `mcp_gateway_auth`;
DROP TABLE IF EXISTS `mcp_gateway`;

CREATE TABLE `mcp_gateway` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关唯一标识',
  `gateway_name` varchar(128) NOT NULL COMMENT '网关名称',
  `gateway_desc` varchar(512) DEFAULT NULL COMMENT '网关描述',
  `version` varchar(16) DEFAULT '1.0.0' COMMENT '版本号',
  `auth` tinyint(1) DEFAULT 0 COMMENT '是否启用认证: 0-否 1-是',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gateway_id` (`gateway_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP网关配置';

-- ============================================
-- MCP Gateway 认证表
-- ============================================
CREATE TABLE `mcp_gateway_auth` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `api_key` varchar(128) NOT NULL COMMENT 'API密钥',
  `rate_limit` int DEFAULT 1000 COMMENT '速率限制(次/小时)',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_api_key` (`api_key`),
  KEY `idx_gateway_id` (`gateway_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP网关认证';

-- ============================================
-- MCP Gateway 工具表
-- ============================================
CREATE TABLE `mcp_gateway_tool` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `tool_id` bigint NOT NULL COMMENT '工具ID',
  `tool_name` varchar(128) NOT NULL COMMENT '工具名称(英文)',
  `tool_type` varchar(32) NOT NULL DEFAULT 'function' COMMENT '工具类型: function/resource',
  `tool_description` varchar(512) NOT NULL COMMENT '工具描述(中文)',
  `tool_version` varchar(16) NOT NULL DEFAULT '1.0.0' COMMENT '版本号',
  `protocol_id` bigint NOT NULL COMMENT '协议配置ID',
  `protocol_type` varchar(16) NOT NULL DEFAULT 'http' COMMENT '协议类型: http',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_name` (`gateway_id`, `tool_name`),
  UNIQUE KEY `uk_tool_id` (`tool_id`),
  KEY `idx_gateway_id` (`gateway_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP工具配置';

-- ============================================
-- MCP Protocol HTTP 配置表
-- ============================================
CREATE TABLE `mcp_protocol_http` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `protocol_id` bigint NOT NULL COMMENT '协议ID(与mcp_gateway_tool.tool_id一致)',
  `http_url` varchar(512) NOT NULL COMMENT 'HTTP URL模板，支持{param}占位符',
  `http_method` varchar(16) NOT NULL DEFAULT 'POST' COMMENT 'HTTP方法: GET/POST/PUT/DELETE/PATCH',
  `http_headers` text COMMENT 'HTTP请求头(JSON格式)',
  `timeout` int DEFAULT 30000 COMMENT '超时时间(毫秒)',
  `retry_times` tinyint DEFAULT 0 COMMENT '重试次数',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_protocol_id` (`protocol_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HTTP协议配置';

-- ============================================
-- MCP Protocol 参数映射表 (核心优化)
-- ============================================
CREATE TABLE `mcp_protocol_mapping` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `protocol_id` bigint NOT NULL COMMENT '协议ID',
  `param_location` varchar(16) NOT NULL COMMENT '参数位置: path/query/body/form/header/file',
  `field_name` varchar(128) NOT NULL COMMENT '字段名称',
  `field_type` varchar(32) NOT NULL DEFAULT 'string' COMMENT '字段类型: string/integer/number/boolean/array/object',
  `field_desc` varchar(256) NOT NULL COMMENT '字段描述(中文，用于LLM理解)',
  `is_required` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否必填: 0-否 1-是',
  `default_value` varchar(256) DEFAULT NULL COMMENT '默认值',
  `enum_values` varchar(512) DEFAULT NULL COMMENT '枚举值(JSON数组)',
  `example_value` varchar(256) DEFAULT NULL COMMENT '示例值',
  `sort_order` int DEFAULT 0 COMMENT '排序序号',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_protocol_id` (`protocol_id`),
  KEY `idx_param_location` (`param_location`),
  KEY `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP参数映射配置';

-- ============================================
-- 初始数据
-- ============================================
INSERT INTO `mcp_gateway` (`id`, `gateway_id`, `gateway_name`, `gateway_desc`, `version`, `auth`, `status`)
VALUES (1, 'gateway_001', '商品服务网关', 'Product Service MCP Gateway', '1.0.0', 0, 1);

INSERT INTO `mcp_gateway_auth` (`id`, `gateway_id`, `api_key`, `rate_limit`, `expire_time`, `status`)
VALUES (1, 'gateway_001', 'gw-test-api-key-001', 360000, '2099-12-31 23:59:59', 1);