-- AI MCP Gateway Database Schema v10.0
-- MySQL 8.0+
-- v5.0 更新：网关管理功能升级，新增LLM配置表
-- v6.0 更新：新增RBAC权限系统，支持组织架构管理
-- v7.0 更新：网关-微服务绑定关系，网关权限配置
-- v8.0 更新：业务线权限分离，用户-业务线关联
-- v9.0 更新：移除部门/团队概念，统一为业务线架构
-- v10.0 更新：统一LLM配置表，合并API Key，支持OpenAI/Anthropic兼容

CREATE DATABASE IF NOT EXISTS `ai_mcp_gateway_v2` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `ai_mcp_gateway_v2`;

-- ============================================
-- MCP Gateway 配置表
-- ============================================
DROP TABLE IF EXISTS `mcp_protocol_mapping`;
DROP TABLE IF EXISTS `mcp_protocol_http`;
DROP TABLE IF EXISTS `mcp_gateway_tool`;
DROP TABLE IF EXISTS `mcp_gateway_microservice`;
DROP TABLE IF EXISTS `mcp_gateway_llm`;
DROP TABLE IF EXISTS `mcp_microservice`;
DROP TABLE IF EXISTS `mcp_llm_config`;
DROP TABLE IF EXISTS `mcp_gateway_auth`;
DROP TABLE IF EXISTS `mcp_gateway`;

-- ============================================
-- MCP 微服务表
-- ============================================
CREATE TABLE `mcp_microservice` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL COMMENT '微服务名称',
  `http_base_url` varchar(512) NOT NULL COMMENT 'HTTP基础URL',
  `description` varchar(512) DEFAULT NULL COMMENT '服务描述',
  `business_line_id` bigint DEFAULT NULL COMMENT '所属业务线ID',
  `health_status` varchar(16) DEFAULT 'unknown' COMMENT '健康状态: healthy/unhealthy/unknown',
  `last_check_time` datetime DEFAULT NULL COMMENT '最后检查时间',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_business_line` (`business_line_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP微服务配置';

CREATE TABLE `mcp_gateway` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关唯一标识',
  `gateway_name` varchar(128) NOT NULL COMMENT '网关名称',
  `gateway_desc` varchar(512) DEFAULT NULL COMMENT '网关描述',
  `version` varchar(16) DEFAULT '1.0.0' COMMENT '版本号',
  `business_line_id` bigint DEFAULT NULL COMMENT '所属业务线ID',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gateway_id` (`gateway_id`),
  KEY `idx_status` (`status`),
  KEY `idx_business_line` (`business_line_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP网关配置';

-- ============================================
-- MCP Gateway 认证表
-- ============================================
CREATE TABLE `mcp_gateway_auth` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `key_id` varchar(32) NOT NULL COMMENT 'API Key唯一标识，用于索引查询',
  `api_key_hash` varchar(128) NOT NULL COMMENT 'bcrypt加盐哈希后的API Key',
  `key_preview` varchar(32) DEFAULT NULL COMMENT 'Key前缀预览（脱敏显示）',
  `rate_limit` int DEFAULT 600 COMMENT '调用次数限制(次/5小时)',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `remark` varchar(256) DEFAULT NULL COMMENT '备注',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_key_id` (`key_id`),
  KEY `idx_gateway_id` (`gateway_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MCP网关认证';

-- ============================================
-- 网关-微服务绑定表
-- ============================================
CREATE TABLE `mcp_gateway_microservice` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `microservice_id` bigint NOT NULL COMMENT '微服务ID',
  `bind_time` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
  `status` tinyint(1) DEFAULT 1 COMMENT '绑定状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gateway_ms` (`gateway_id`, `microservice_id`),
  KEY `idx_gateway_id` (`gateway_id`),
  KEY `idx_microservice_id` (`microservice_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网关-微服务绑定关系';

-- ============================================
-- LLM 配置表 (统一)
-- ============================================
CREATE TABLE `mcp_llm_config` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `config_id` varchar(64) NOT NULL COMMENT '配置唯一标识',
  `config_name` varchar(128) NOT NULL COMMENT '配置名称(自定义)',
  `api_type` varchar(16) NOT NULL COMMENT 'API类型: openai/anthropic',
  `base_url` varchar(512) NOT NULL COMMENT 'API基础URL',
  `model_name` varchar(128) NOT NULL COMMENT '模型名称',
  `api_key` text NOT NULL COMMENT 'API Key(AES加密存储或JWT Token)',
  `description` varchar(512) DEFAULT NULL COMMENT '描述',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_id` (`config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='LLM配置(统一)';

-- ============================================
-- 网关-LLM绑定关系表
-- ============================================
CREATE TABLE `mcp_gateway_llm` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `llm_config_id` varchar(64) NOT NULL COMMENT 'LLM配置ID',
  `bind_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gateway_llm` (`gateway_id`, `llm_config_id`),
  KEY `idx_gateway_id` (`gateway_id`),
  KEY `idx_llm_config_id` (`llm_config_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网关-LLM绑定关系';

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
  `microservice_id` bigint DEFAULT NULL COMMENT '关联微服务ID',
  `enabled` tinyint(1) NOT NULL DEFAULT 1 COMMENT '启用状态: 0-禁用 1-启用',
  `call_status` varchar(16) DEFAULT 'sunny' COMMENT '调用状态(天气): sunny(晴朗)/cloudy(阴云)/rainy(下雨)',
  `last_call_time` datetime DEFAULT NULL COMMENT '最后调用时间',
  `last_call_code` varchar(32) DEFAULT NULL COMMENT '最后调用返回码(http状态码或业务code)',
  `call_count` int DEFAULT 0 COMMENT '调用次数',
  `error_count` int DEFAULT 0 COMMENT '错误次数',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_tool_name` (`gateway_id`, `tool_name`),
  UNIQUE KEY `uk_tool_id` (`tool_id`),
  KEY `idx_gateway_id` (`gateway_id`),
  KEY `idx_microservice_id` (`microservice_id`)
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
-- MCP Protocol 参数映射表
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
-- RBAC 权限系统表 v9.0
-- ============================================

-- 先删除RBAC相关表（按依赖关系倒序删除）
DROP TABLE IF EXISTS `sys_login_log`;
DROP TABLE IF EXISTS `sys_gateway_permission`;
DROP TABLE IF EXISTS `sys_user_business_line`;
DROP TABLE IF EXISTS `sys_role_permission`;
DROP TABLE IF EXISTS `sys_user_role`;
DROP TABLE IF EXISTS `sys_permission`;
DROP TABLE IF EXISTS `sys_resource`;
DROP TABLE IF EXISTS `sys_role`;
DROP TABLE IF EXISTS `sys_user`;
DROP TABLE IF EXISTS `sys_business_line`;

-- ============================================
-- 业务线表
-- ============================================
CREATE TABLE `sys_business_line` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `line_code` varchar(64) NOT NULL COMMENT '业务线编码(如: OA, PRODUCT)',
  `line_name` varchar(128) NOT NULL COMMENT '业务线名称(如: OA办公, 商品服务)',
  `description` varchar(512) DEFAULT NULL COMMENT '描述',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_line_code` (`line_code`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='业务线表';

-- ============================================
-- 用户表
-- ============================================
CREATE TABLE `sys_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(64) NOT NULL COMMENT '用户名',
  `password_hash` varchar(128) NOT NULL COMMENT 'bcrypt密码哈希',
  `real_name` varchar(64) DEFAULT NULL COMMENT '真实姓名',
  `email` varchar(128) DEFAULT NULL COMMENT '邮箱',
  `phone` varchar(32) DEFAULT NULL COMMENT '手机号',
  `avatar` varchar(256) DEFAULT NULL COMMENT '头像URL',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `last_login_time` datetime DEFAULT NULL COMMENT '最后登录时间',
  `last_login_ip` varchar(64) DEFAULT NULL COMMENT '最后登录IP',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================
-- 角色表
-- ============================================
CREATE TABLE `sys_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_code` varchar(64) NOT NULL COMMENT '角色编码(如: SUPER_ADMIN)',
  `role_name` varchar(128) NOT NULL COMMENT '角色名称',
  `description` varchar(512) DEFAULT NULL COMMENT '角色描述',
  `business_line_id` bigint DEFAULT NULL COMMENT '所属业务线ID，NULL表示全局角色',
  `is_system` tinyint(1) NOT NULL DEFAULT 0 COMMENT '是否系统内置角色: 0-否 1-是',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_code` (`role_code`),
  KEY `idx_status` (`status`),
  KEY `idx_business_line` (`business_line_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色表';

-- 用户角色关联表
CREATE TABLE `sys_user_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_role` (`user_id`, `role_id`),
  KEY `idx_role_id` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户角色关联表';

-- 用户-业务线关联表
CREATE TABLE `sys_user_business_line` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `business_line_id` bigint NOT NULL COMMENT '业务线ID',
  `is_admin` tinyint(1) DEFAULT 0 COMMENT '是否该业务线管理员: 0-否 1-是',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_bl` (`user_id`, `business_line_id`),
  KEY `idx_business_line_id` (`business_line_id`),
  KEY `idx_is_admin` (`is_admin`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户-业务线关联表';

-- ============================================
-- 权限表
-- ============================================

-- 资源表
CREATE TABLE `sys_resource` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `resource_code` varchar(128) NOT NULL COMMENT '资源编码(如: gateway, microservice)',
  `resource_name` varchar(128) NOT NULL COMMENT '资源名称',
  `resource_type` varchar(32) DEFAULT 'menu' COMMENT '资源类型: menu/button/api',
  `parent_id` bigint DEFAULT 0 COMMENT '父资源ID',
  `api_path` varchar(256) DEFAULT NULL COMMENT 'API路径',
  `icon` varchar(64) DEFAULT NULL COMMENT '图标',
  `sort_order` int DEFAULT 0 COMMENT '排序',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_resource_code` (`resource_code`),
  KEY `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资源表';

-- 权限表(资源+操作组合)
CREATE TABLE `sys_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `permission_code` varchar(128) NOT NULL COMMENT '权限编码(如: gateway:create)',
  `permission_name` varchar(128) NOT NULL COMMENT '权限名称',
  `resource_id` bigint NOT NULL COMMENT '资源ID',
  `action` varchar(32) NOT NULL COMMENT '操作: create/read/update/delete',
  `description` varchar(512) DEFAULT NULL COMMENT '描述',
  `status` tinyint(1) NOT NULL DEFAULT 1 COMMENT '状态: 0-禁用 1-启用',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_permission_code` (`permission_code`),
  KEY `idx_resource_id` (`resource_id`),
  KEY `idx_action` (`action`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='权限表';

-- 角色权限关联表
CREATE TABLE `sys_role_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `permission_id` bigint NOT NULL COMMENT '权限ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_perm` (`role_id`, `permission_id`),
  KEY `idx_permission_id` (`permission_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色权限关联表';

-- 网关权限配置表
CREATE TABLE `sys_gateway_permission` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role_id` bigint NOT NULL COMMENT '角色ID',
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `can_create` tinyint(1) DEFAULT 0 COMMENT '创建权限',
  `can_read` tinyint(1) DEFAULT 0 COMMENT '查看权限',
  `can_update` tinyint(1) DEFAULT 0 COMMENT '编辑权限',
  `can_delete` tinyint(1) DEFAULT 0 COMMENT '删除权限',
  `can_chat` tinyint(1) DEFAULT 0 COMMENT '对话权限',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_role_gateway` (`role_id`, `gateway_id`),
  KEY `idx_gateway_id` (`gateway_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网关权限配置';

-- ============================================
-- 登录日志表
-- ============================================
CREATE TABLE `sys_login_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint DEFAULT NULL COMMENT '用户ID',
  `username` varchar(64) DEFAULT NULL COMMENT '用户名',
  `login_ip` varchar(64) DEFAULT NULL COMMENT '登录IP',
  `login_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '登录时间',
  `login_status` tinyint(1) DEFAULT 1 COMMENT '登录状态: 1-成功 0-失败',
  `fail_reason` varchar(256) DEFAULT NULL COMMENT '失败原因',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_login_time` (`login_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表';

-- ============================================
-- 模型调用使用记录表
-- ============================================
CREATE TABLE `mcp_usage_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gateway_id` varchar(64) NOT NULL COMMENT '网关ID',
  `key_id` varchar(32) NOT NULL COMMENT 'API Key标识',
  `session_id` varchar(64) DEFAULT NULL COMMENT '会话ID',
  `call_type` varchar(16) NOT NULL COMMENT '调用类型: llm/tool',
  `call_detail` varchar(256) DEFAULT NULL COMMENT '调用详情(模型名或工具名)',
  `call_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '调用时间',
  `success` tinyint(1) DEFAULT 1 COMMENT '是否成功',
  PRIMARY KEY (`id`),
  KEY `idx_gateway_key_time` (`gateway_id`, `key_id`, `call_time`),
  KEY `idx_call_time` (`call_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型调用使用记录';