-- AI MCP Gateway Database Schema
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS `ai_mcp_gateway_v2` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE `ai_mcp_gateway_v2`;

-- MCP Gateway Configuration Table
DROP TABLE IF EXISTS `mcp_gateway`;
CREATE TABLE `mcp_gateway` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Primary Key ID',
  `gateway_id` varchar(64) NOT NULL COMMENT 'Gateway unique identifier',
  `gateway_name` varchar(128) NOT NULL COMMENT 'Gateway name',
  `gateway_desc` varchar(512) DEFAULT NULL COMMENT 'Gateway description',
  `version` varchar(16) DEFAULT NULL COMMENT 'Gateway version',
  `auth` tinyint(1) DEFAULT '0' COMMENT 'Auth status: 0-disabled, 1-enabled',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'Status: 0-disabled, 1-enabled',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_gateway_id` (`gateway_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP Gateway Configuration';

-- MCP Gateway Auth Table
DROP TABLE IF EXISTS `mcp_gateway_auth`;
CREATE TABLE `mcp_gateway_auth` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Primary Key ID',
  `gateway_id` varchar(64) NOT NULL COMMENT 'Gateway ID',
  `api_key` varchar(128) DEFAULT NULL COMMENT 'API key',
  `rate_limit` int DEFAULT '1000' COMMENT 'Rate limit (per hour)',
  `expire_time` datetime DEFAULT NULL COMMENT 'Expiration time',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'Status: 0-disabled, 1-enabled',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_api_key` (`api_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='Gateway Auth Configuration';

-- MCP Gateway Tool Table
DROP TABLE IF EXISTS `mcp_gateway_tool`;
CREATE TABLE `mcp_gateway_tool` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'Auto increment ID',
  `gateway_id` varchar(64) NOT NULL COMMENT 'Gateway ID',
  `tool_id` bigint NOT NULL COMMENT 'Tool ID',
  `tool_name` varchar(128) NOT NULL COMMENT 'MCP tool name',
  `tool_type` varchar(32) NOT NULL DEFAULT 'function' COMMENT 'Tool type: function/resource',
  `tool_description` varchar(512) NOT NULL COMMENT 'Tool description',
  `tool_version` varchar(16) NOT NULL COMMENT 'Tool version',
  `protocol_id` bigint NOT NULL COMMENT 'Protocol ID',
  `protocol_type` varchar(4) NOT NULL DEFAULT 'http' COMMENT 'Protocol type: http, dubbo, rabbitmq',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tool_name` (`gateway_id`,`tool_name`),
  UNIQUE KEY `uq_tool_id` (`tool_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP Gateway Tool';

-- MCP Protocol HTTP Table
DROP TABLE IF EXISTS `mcp_protocol_http`;
CREATE TABLE `mcp_protocol_http` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Primary Key ID',
  `protocol_id` bigint NOT NULL COMMENT 'Protocol ID',
  `http_url` varchar(512) NOT NULL COMMENT 'HTTP URL',
  `http_method` varchar(16) NOT NULL DEFAULT 'POST' COMMENT 'HTTP method: GET/POST/PUT/DELETE',
  `http_headers` text COMMENT 'HTTP headers (JSON format)',
  `timeout` int DEFAULT '30000' COMMENT 'Timeout in milliseconds',
  `retry_times` tinyint DEFAULT '0' COMMENT 'Retry times',
  `status` tinyint(1) NOT NULL DEFAULT '1' COMMENT 'Status: 0-disabled, 1-enabled',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP Protocol HTTP Configuration';

-- MCP Protocol Mapping Table
DROP TABLE IF EXISTS `mcp_protocol_mapping`;
CREATE TABLE `mcp_protocol_mapping` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'Primary Key ID',
  `protocol_id` bigint NOT NULL COMMENT 'Protocol ID',
  `mapping_type` varchar(32) NOT NULL COMMENT 'Mapping type: request/response',
  `parent_path` varchar(256) DEFAULT NULL COMMENT 'Parent path',
  `field_name` varchar(128) NOT NULL COMMENT 'Field name',
  `mcp_path` varchar(256) NOT NULL COMMENT 'MCP full path',
  `mcp_type` varchar(32) NOT NULL COMMENT 'MCP data type: string/number/boolean/object/array',
  `mcp_desc` varchar(512) DEFAULT NULL COMMENT 'MCP field description',
  `is_required` tinyint(1) NOT NULL DEFAULT '0' COMMENT 'Is required: 0-no, 1-yes',
  `sort_order` int DEFAULT '0' COMMENT 'Sort order',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Create time',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Update time',
  PRIMARY KEY (`id`),
  KEY `idx_mapping_type` (`mapping_type`),
  KEY `idx_parent_path` (`parent_path`),
  KEY `idx_mcp_path` (`mcp_path`),
  KEY `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='MCP Protocol Mapping Configuration';

-- Insert sample data
INSERT INTO `mcp_gateway` (`id`, `gateway_id`, `gateway_name`, `gateway_desc`, `version`, `auth`, `status`)
VALUES (1, 'gateway_001', 'Employee Info Gateway', 'MCP Gateway for querying employee information', '1.0.0', 0, 1);

INSERT INTO `mcp_gateway_auth` (`id`, `gateway_id`, `api_key`, `rate_limit`, `expire_time`, `status`)
VALUES 
    (1, 'gateway_001', 'gw-test-api-key-001', 360000, '2099-12-31 23:59:59', 1);


